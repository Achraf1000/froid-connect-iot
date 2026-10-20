import asyncio
import csv
import hmac
import io
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pymongo.errors import DuplicateKeyError, PyMongoError

from .config import RULES, Settings
from .firebase import FirebasePublisher
from .models import Login, Telemetry, TransportCreate, TransportUpdate
from .storage import ConflictError, Store, public, utc_now

log = logging.getLogger("coldchain")


def create_app(settings=None, store=None, publisher=None, start_worker=True):
    settings = settings or Settings()
    store = store or Store(settings)
    publisher = publisher or FirebasePublisher(settings)
    signer = URLSafeTimedSerializer(settings.session_secret, salt="cold-chain-session")

    async def project():
        while True:
            try:
                await asyncio.to_thread(store.reconcile)
                await asyncio.to_thread(publisher.publish_pending, store)
            except PyMongoError:
                log.warning("MongoDB indisponible, reprise du traitement au prochain cycle.")
            await asyncio.sleep(1)

    @asynccontextmanager
    async def lifespan(app):
        store.initialize()
        # Recover committed records which were not projected before a previous shutdown.
        store.reconcile()
        task = asyncio.create_task(project()) if start_worker else None
        yield
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        publisher.close()
        store.client.close()

    app = FastAPI(title="Chaîne du froid · API", version="1.0.0", lifespan=lifespan)
    app.state.store = store
    app.state.publisher = publisher
    app.add_middleware(
        CORSMiddleware, allow_origins=[settings.frontend_origin],
        allow_credentials=True, allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type", "X-Device-Key"],
    )

    @app.exception_handler(PyMongoError)
    async def database_unavailable(request, exc):
        return JSONResponse(status_code=503, content={"detail": "Stockage indisponible. Réessayez."})

    @app.exception_handler(RequestValidationError)
    async def invalid_payload(request, exc):
        # Never echo arbitrary input (including non-JSON floats or credentials).
        return JSONResponse(status_code=422, content={"detail": [
            {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
            for error in exc.errors()
        ]})

    def reader(request: Request):
        token = request.cookies.get("coldchain_session", "")
        try:
            signer.loads(token, max_age=8 * 3600)
        except (BadSignature, SignatureExpired):
            raise HTTPException(401, "Connexion au tableau de bord requise.")
        if request.method not in ("GET", "HEAD"):
            origin = request.headers.get("origin")
            allowed = {settings.frontend_origin, str(request.base_url).rstrip("/")}
            if origin and origin not in allowed:
                raise HTTPException(403, "Origine non autorisée.")
        return True

    def device(x_device_key: str = Header(default="")):
        if not hmac.compare_digest(x_device_key.encode(), settings.device_api_key.encode()):
            raise HTTPException(401, "Clé du véhicule incorrecte.")

    @app.get("/health")
    def health():
        return {"status": "ok", "version": "1.0.0"}

    @app.post("/api/v1/auth/login")
    def login(body: Login, response: Response):
        if not hmac.compare_digest(body.password.encode(), settings.dashboard_password.encode()):
            raise HTTPException(401, "Mot de passe incorrect.")
        response.set_cookie(
            "coldchain_session", signer.dumps({"reader": settings.firebase_reader_uid}),
            httponly=True, secure=settings.cookie_secure, samesite="strict", max_age=8 * 3600,
        )
        return {"authenticated": True}

    @app.post("/api/v1/auth/logout", dependencies=[Depends(reader)])
    def logout(response: Response):
        response.delete_cookie("coldchain_session")
        return {"authenticated": False}

    @app.get("/api/v1/auth/session", dependencies=[Depends(reader)])
    def session():
        return {"authenticated": True}

    @app.get("/ready", dependencies=[Depends(reader)])
    def ready():
        store.client.admin.command("ping")
        pending = store.db.states.count_documents({"firebase_synced": False})
        return {
            "mongodb": "connected",
            "firebase": "pending" if pending else ("connected" if publisher.connected else "idle"),
            "pending_publications": pending, "detail": publisher.last_error,
        }

    @app.get("/api/v1/config", dependencies=[Depends(reader)])
    def configuration():
        return {"vehicle_id": "VEH-001", "rules": RULES, "firebase_mode": settings.firebase_mode}

    @app.get("/api/v1/firebase/session", dependencies=[Depends(reader)])
    def firebase_session():
        try:
            return publisher.reader_session()
        except Exception:
            raise HTTPException(503, "Connexion temps réel indisponible ; suivi par API disponible.")

    @app.post("/api/v1/telemetry", dependencies=[Depends(device)])
    def telemetry(body: Telemetry, response: Response):
        try:
            inserted = store.ingest(body)
        except KeyError:
            raise HTTPException(404, "Transport inconnu.")
        except ConflictError as exc:
            raise HTTPException(409, str(exc))
        response.status_code = 201 if inserted else 200
        return {"accepted": True, "duplicate": not inserted, "sequence": body.sequence}

    @app.get("/api/v1/transports", dependencies=[Depends(reader)])
    def transports():
        return [public(t) for t in store.db.transports.find().sort("created_at", -1)]

    @app.post("/api/v1/transports", status_code=201, dependencies=[Depends(reader)])
    def new_transport(body: TransportCreate):
        try:
            return store.create_transport(body.model_dump())
        except DuplicateKeyError:
            raise HTTPException(409, "Cet identifiant de transport existe déjà.")

    @app.patch("/api/v1/transports/{transport_id}", dependencies=[Depends(reader)])
    def finish_transport(transport_id: str, body: TransportUpdate):
        result = store.db.transports.update_one(
            {"id": transport_id, "status": "active"},
            {"$set": {"status": body.status, "ended_at": utc_now()}},
        )
        if result.matched_count == 0:
            raise HTTPException(409, "Transport absent ou déjà terminé.")
        return {"id": transport_id, "status": body.status}

    @app.get("/api/v1/vehicles/VEH-001/state", dependencies=[Depends(reader)])
    def state(transport_id: str | None = None):
        data = store.state(transport_id)
        if data is None:
            return {"state": None, "freshness": "empty", "server_time": utc_now()}
        measured_at = data["measured_at"]
        age = (
            max(0, (datetime.now(timezone.utc) - datetime.fromisoformat(measured_at.replace("Z", "+00:00"))).total_seconds())
            if measured_at else None
        )
        return {
            "state": data, "age_seconds": age,
            "freshness": "unknown" if age is None else ("stale" if age > RULES["stale_seconds"] else "fresh"),
            "server_time": utc_now(),
        }

    @app.get("/api/v1/transports/{transport_id}/measurements", dependencies=[Depends(reader)])
    def measurements(
        transport_id: str, limit: int = Query(500, ge=1, le=2000),
        offset: int = Query(0, ge=0), start: datetime | None = None, end: datetime | None = None,
    ):
        def iso(value):
            if value is None:
                return None
            if value.tzinfo is None:
                raise HTTPException(422, "Fuseau horaire requis.")
            return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        return store.measurements(transport_id, limit, offset, iso(start), iso(end))

    @app.get("/api/v1/transports/{transport_id}/alerts", dependencies=[Depends(reader)])
    def alerts(transport_id: str):
        return [public(a) for a in store.db.alerts.find(
            {"transport_id": transport_id}).sort("started_at", -1)]

    @app.get("/api/v1/transports/{transport_id}/export.csv", dependencies=[Depends(reader)])
    def export(transport_id: str):
        output = io.StringIO()
        fields = ["measured_at", "received_at", "temperature_c", "latitude", "longitude",
                  "sensor_status", "boot_id", "sequence", "source"]
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in store.db.measurements.find({"transport_id": transport_id}).sort("measured_at", 1):
            writer.writerow(row)
        return Response(
            "\ufeff" + output.getvalue(), media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="mesures.csv"'},
        )

    dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="dashboard")
    return app
