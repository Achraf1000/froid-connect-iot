import hashlib
import json
import threading
from datetime import datetime, timezone

from pymongo import ASCENDING, MongoClient
from pymongo.errors import DuplicateKeyError

from .config import RULES
from .engine import replay


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def public(document):
    if document is None:
        return None
    return {k: v for k, v in document.items() if k != "_id"}


class ConflictError(Exception):
    pass


class Store:
    def __init__(self, settings, client=None):
        self.client = client or MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=1500)
        self.db = self.client[settings.mongo_database]
        self.lock = threading.RLock()

    def initialize(self):
        self.db.measurements.create_index(
            [("vehicle_id", ASCENDING), ("boot_id", ASCENDING), ("sequence", ASCENDING)],
            unique=True,
        )
        self.db.measurements.create_index([("transport_id", ASCENDING), ("measured_at", ASCENDING)])
        self.db.measurements.create_index("projected")
        self.db.transports.create_index("id", unique=True)
        self.db.states.create_index("transport_id", unique=True)
        self.db.alerts.create_index("id", unique=True)
        if not self.db.transports.find_one({"id": "TRIP-DEMO-001"}):
            self.create_transport({
                "id": "TRIP-DEMO-001", "name": "Démonstration · Tunis → La Marsa",
                "origin": "Tunis", "destination": "La Marsa",
            })

    def create_transport(self, data):
        transport = {
            **data, "vehicle_id": "VEH-001", "status": "active",
            "created_at": utc_now(), "ended_at": None, "rules": RULES.copy(),
        }
        self.db.transports.insert_one(transport.copy())
        return transport

    def ingest(self, measurement):
        data = measurement.model_dump(mode="json")
        if measurement.measured_at:
            data["measured_at"] = measurement.measured_at.isoformat(
                timespec="milliseconds"
            ).replace("+00:00", "Z")
        identity = {k: data[k] for k in ("vehicle_id", "boot_id", "sequence")}
        fingerprint = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
        existing = self.db.measurements.find_one(identity)
        if existing:
            if existing["fingerprint"] != fingerprint:
                raise ConflictError("Identifiant réutilisé avec un contenu différent.")
            return False
        transport = self.db.transports.find_one({"id": data["transport_id"]})
        if not transport:
            raise KeyError("Transport inconnu.")
        if transport["status"] != "active":
            raise ConflictError("Transport terminé.")
        document = {
            **data, "received_at": utc_now(), "fingerprint": fingerprint, "projected": False,
        }
        try:
            self.db.measurements.insert_one(document)
        except DuplicateKeyError:
            existing = self.db.measurements.find_one(identity)
            if existing["fingerprint"] != fingerprint:
                raise ConflictError("Identifiant réutilisé avec un contenu différent.")
            return False
        return True

    def reconcile(self):
        # One application worker. Snapshot IDs prevent a concurrent insert being marked done.
        with self.lock:
            dirty = self.db.measurements.distinct("transport_id", {"projected": False})
            for transport_id in dirty:
                transport = self.db.transports.find_one({"id": transport_id})
                docs = list(self.db.measurements.find({"transport_id": transport_id}))
                state, alerts = replay(docs, transport["rules"])
                version = hashlib.sha256(
                    json.dumps({"state": state, "alerts": alerts}, sort_keys=True).encode()
                ).hexdigest()
                state.update(version=version, firebase_synced=False)
                self.db.states.replace_one({"transport_id": transport_id}, state, upsert=True)
                # All alert rows are derived from the durable measurements and can be rebuilt.
                keep = [a["id"] for a in alerts]
                for alert in alerts:
                    self.db.alerts.replace_one({"id": alert["id"]}, alert, upsert=True)
                self.db.alerts.delete_many({"transport_id": transport_id, "id": {"$nin": keep}})
                self.db.measurements.update_many(
                    {"_id": {"$in": [m["_id"] for m in docs]}}, {"$set": {"projected": True}}
                )

    def state(self, transport_id=None):
        query = {"transport_id": transport_id} if transport_id else {}
        return public(self.db.states.find_one(query, sort=[("received_at", -1)]))

    def measurements(self, transport_id, limit=500, offset=0, start=None, end=None):
        query = {"transport_id": transport_id}
        if start or end:
            query["measured_at"] = {}
            if start:
                query["measured_at"]["$gte"] = start
            if end:
                query["measured_at"]["$lte"] = end
        total = self.db.measurements.count_documents(query)
        docs = self.db.measurements.find(query).sort(
            [("measured_at", -1), ("sequence", -1)]
        ).skip(offset).limit(limit)
        items = [{k: v for k, v in public(d).items() if k not in ("fingerprint", "projected")} for d in docs]
        return {"items": items, "total": total, "limit": limit, "offset": offset}
