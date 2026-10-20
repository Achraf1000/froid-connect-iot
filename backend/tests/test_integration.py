import os
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from app.config import Settings
from app.firebase import FirebasePublisher
from app.models import Telemetry
from app.storage import Store

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(os.getenv("RUN_INTEGRATION") != "1", reason="RUN_INTEGRATION=1 pour les services locaux"),
]


def test_real_mongo_firebase_and_access_rules():
    suffix = uuid.uuid4().hex[:12]
    settings = Settings(mongo_database=f"cold_chain_integration_{suffix}")
    store = Store(settings)
    publisher = FirebasePublisher(settings)
    transport_id = f"INTEGRATION-{suffix}"
    try:
        store.initialize()
        store.create_transport({"id": transport_id, "name": "Essai isolé", "origin": "Tunis", "destination": "La Marsa"})
        base = datetime.now(timezone.utc) - timedelta(minutes=2)
        for i in range(9):
            data = Telemetry(
                vehicle_id="VEH-001", transport_id=transport_id, boot_id="integration",
                sequence=i, uptime_ms=i * 5000, measured_at=base + timedelta(seconds=i*5),
                temperature_c=12.0 if i < 8 else 5.0, latitude=36.8, longitude=10.18,
                sensor_status="ok", local_alarm=6 <= i < 8,
            )
            assert store.ingest(data) is True
            assert store.ingest(data) is False
        store.reconcile()
        original_url = settings.firebase_database_url
        settings.firebase_database_url = "http://127.0.0.1:1?ns=demo-cold-chain-default-rtdb"
        publisher.publish_pending(store)
        assert store.db.measurements.count_documents({}) == 9
        assert store.state(transport_id)["firebase_synced"] is False
        settings.firebase_database_url = original_url
        publisher.publish_pending(store)
        assert store.state(transport_id)["firebase_synced"] is True
        assert store.db.alerts.find_one({"transport_id": transport_id})["status"] == "resolved"

        namespace = "demo-cold-chain-default-rtdb"
        url = f"http://127.0.0.1:9000/transports/{transport_id}/state.json"
        params = {"ns": namespace}
        assert httpx.get(url, params=params).status_code == 401
        session = publisher.reader_session()
        auth = httpx.post(
            "http://127.0.0.1:9099/identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken",
            params={"key": "demo-key"}, json={"token": session["token"], "returnSecureToken": True},
        )
        auth.raise_for_status()
        params["auth"] = auth.json()["idToken"]
        result = httpx.get(url, params=params)
        result.raise_for_status()
        assert result.json()["temperature_c"] == 5.0
        assert httpx.put(url, params=params, json={"temperature_c": 99}).status_code == 401
    finally:
        # Only this test's newly created namespace and transport are removed.
        assert settings.mongo_database == f"cold_chain_integration_{suffix}"
        store.client.drop_database(settings.mongo_database)
        httpx.delete(
            f"http://127.0.0.1:9000/transports/{transport_id}.json",
            params={"ns": "demo-cold-chain-default-rtdb"}, headers={"Authorization": "Bearer owner"},
        )
        publisher.close()
        store.client.close()
