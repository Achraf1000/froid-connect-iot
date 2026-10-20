import time
from urllib.parse import parse_qs, urlparse

import httpx

from .storage import public


class FirebasePublisher:
    def __init__(self, settings):
        self.settings = settings
        self.last_error = None
        self.connected = False
        self.client = httpx.Client(timeout=3)
        self.app = None
        self.last_refresh = 0.0

    def cloud_app(self):
        import firebase_admin
        from firebase_admin import credentials
        if self.app is None:
            credential = (
                credentials.Certificate(self.settings.google_application_credentials)
                if self.settings.google_application_credentials else credentials.ApplicationDefault()
            )
            self.app = firebase_admin.initialize_app(
                credential, {"databaseURL": self.settings.firebase_database_url},
                name="cold-chain-publisher",
            )
        return self.app

    def reader_session(self):
        settings = self.settings
        if settings.firebase_mode == "emulator":
            import jwt
            now = int(time.time())
            token = jwt.encode({
                "iss": "firebase-admin@demo-cold-chain.iam.gserviceaccount.com",
                "sub": "firebase-admin@demo-cold-chain.iam.gserviceaccount.com",
                "aud": "https://identitytoolkit.googleapis.com/google.identity.identitytoolkit.v1.IdentityToolkit",
                "iat": now, "exp": now + 3600, "uid": settings.firebase_reader_uid,
            }, key="", algorithm="none")
            return {
                "mode": "emulator", "token": token,
                "config": {"apiKey": "demo-key", "projectId": settings.firebase_project_id,
                           "databaseURL": f"https://{settings.firebase_project_id}-default-rtdb.firebaseio.com"},
                "database_host": settings.firebase_database_emulator_host,
                "database_port": settings.firebase_database_emulator_port,
                "auth_url": settings.firebase_auth_emulator_url,
            }
        if settings.firebase_mode == "cloud" and settings.firebase_web_api_key:
            from firebase_admin import auth
            token = auth.create_custom_token(settings.firebase_reader_uid, app=self.cloud_app())
            return {
                "mode": "cloud", "token": token.decode(),
                "config": {"apiKey": settings.firebase_web_api_key,
                           "projectId": settings.firebase_project_id,
                           "authDomain": settings.firebase_auth_domain,
                           "databaseURL": settings.firebase_database_url},
            }
        raise RuntimeError("Connexion Firebase non configurée.")

    def write(self, path, data):
        settings = self.settings
        if settings.firebase_mode == "disabled":
            raise RuntimeError("Firebase désactivé dans la configuration.")
        if settings.firebase_mode == "emulator":
            parsed = urlparse(settings.firebase_database_url)
            if parsed.hostname not in ("127.0.0.1", "localhost", "firebase"):
                raise ValueError("L'émulateur doit utiliser une adresse locale.")
            namespace = parse_qs(parsed.query).get("ns", [settings.firebase_project_id])[0]
            response = self.client.put(
                f"{parsed.scheme}://{parsed.netloc}/{path}.json",
                params={"ns": namespace}, json=data,
                headers={"Authorization": "Bearer owner"},
            )
            response.raise_for_status()
        elif settings.firebase_mode == "cloud":
            from firebase_admin import db
            db.reference(path, app=self.cloud_app()).set(data)
        else:
            raise ValueError("FIREBASE_MODE doit être emulator, cloud ou disabled.")

    def publish_pending(self, store):
        refresh = time.monotonic() - self.last_refresh >= 30
        states = list(store.db.states.find({} if refresh else {"firebase_synced": False}))
        if refresh:
            self.last_refresh = time.monotonic()
        for doc in states:
            try:
                payload = public(doc)
                payload.pop("firebase_synced", None)
                self.write(f'transports/{doc["transport_id"]}/state', payload)
                store.db.states.update_one(
                    {"transport_id": doc["transport_id"], "version": doc["version"]},
                    {"$set": {"firebase_synced": True}},
                )
                self.connected = True
                self.last_error = None
            except Exception:
                self.connected = False
                # Do not include credential paths, URLs with credentials, or tokens in API output.
                self.last_error = "Publication Firebase en attente ; nouvelle tentative automatique."
                break

    def close(self):
        self.client.close()
        if self.app:
            import firebase_admin
            firebase_admin.delete_app(self.app)
