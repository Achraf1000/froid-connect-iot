from datetime import datetime, timedelta, timezone

import mongomock
import pytest
from app.config import Settings
from app.firebase import FirebasePublisher
from app.main import create_app
from app.models import Telemetry
from app.storage import Store
from fastapi.testclient import TestClient


@pytest.fixture
def settings():
    return Settings(
        _env_file=None, device_api_key="test-device-key-123456",
        dashboard_password="test-password-123456", session_secret="test-session-secret-" * 3,
        firebase_mode="emulator", mongo_database="cold_chain_test",
    )


@pytest.fixture
def sample():
    base = datetime.now(timezone.utc) - timedelta(minutes=30)
    def build(sequence=0, temperature=5.0, **overrides):
        data = {
            "vehicle_id": "VEH-001", "transport_id": "TRIP-DEMO-001",
            "boot_id": "test-boot", "sequence": sequence,
            "uptime_ms": sequence * 5000,
            "measured_at": (base + timedelta(seconds=sequence * 5)).isoformat().replace("+00:00", "Z"),
            "temperature_c": temperature, "latitude": 36.8065, "longitude": 10.1815,
            "sensor_status": "ok" if temperature is not None else "error",
            "local_alarm": False, "source": "simulator",
        }
        data.update(overrides)
        return data
    return build


@pytest.fixture
def store(settings):
    result = Store(settings, mongomock.MongoClient())
    result.initialize()
    return result


@pytest.fixture
def client(settings, store):
    app = create_app(settings, store, FirebasePublisher(settings), start_worker=False)
    with TestClient(app) as result:
        yield result


@pytest.fixture
def reader(client, settings):
    assert client.post("/api/v1/auth/login", json={"password": settings.dashboard_password}).status_code == 200
    return client


def event(data):
    return {**Telemetry(**data).model_dump(mode="json"), "received_at": data["measured_at"] or "2026-01-01T00:00:00Z"}
