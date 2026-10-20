import pytest
from app.models import Telemetry
from pymongo.errors import ServerSelectionTimeoutError


def send(client, settings, data):
    return client.post("/api/v1/telemetry", json=data, headers={"X-Device-Key": settings.device_api_key})


def test_health_is_public_but_data_is_private(client):
    assert client.get("/health").status_code == 200
    assert client.get("/api/v1/transports").status_code == 401
    assert client.get("/ready").status_code == 401


def test_device_key_required(client, sample):
    assert client.post("/api/v1/telemetry", json=sample()).status_code == 401


def test_dashboard_password_does_not_authorize_device(reader, sample):
    assert reader.post("/api/v1/telemetry", json=sample()).status_code == 401


def test_measurement_acknowledged_after_storage(reader, settings, sample, store):
    response = send(reader, settings, sample())
    assert response.status_code == 201
    assert store.db.measurements.count_documents({}) == 1
    store.reconcile()
    data = reader.get("/api/v1/vehicles/VEH-001/state").json()
    assert data["state"]["temperature_c"] == 5
    assert data["freshness"] == "stale"


def test_duplicates_and_content_conflict(client, settings, sample, store):
    assert send(client, settings, sample()).status_code == 201
    assert send(client, settings, sample()).json()["duplicate"] is True
    assert send(client, settings, sample(temperature=12.0)).status_code == 409
    assert store.db.measurements.count_documents({}) == 1


@pytest.mark.parametrize("change", [
    {"temperature_c": "hot"}, {"temperature_c": "5"}, {"temperature_c": True},
    {"latitude": 95.0}, {"longitude": 200.0}, {"sequence": -1}, {"sequence": True},
    {"measured_at": "not-a-date"}, {"measured_at": "2026-01-01T12:00:00"},
    {"measured_at": "2099-01-01T00:00:00Z"},
    {"sensor_status": "error", "temperature_c": 5.0},
    {"sensor_status": "ok", "temperature_c": None},
    {"extra_field": "forbidden"}, {"transport_id": "../escape"},
])
def test_validation(client, settings, sample, store, change):
    assert send(client, settings, sample(**change)).status_code == 422
    assert store.db.measurements.count_documents({}) == 0


def test_missing_field(client, settings, sample):
    data = sample()
    del data["temperature_c"]
    assert send(client, settings, data).status_code == 422


def test_nan_rejected(client, settings, sample):
    import json
    data = sample(temperature=float("nan"))
    response = client.post("/api/v1/telemetry", content=json.dumps(data), headers={
        "X-Device-Key": settings.device_api_key, "Content-Type": "application/json",
    })
    assert response.status_code == 422


def test_unknown_transport(client, settings, sample):
    assert send(client, settings, sample(transport_id="UNKNOWN")).status_code == 404


def test_transport_lifecycle(reader, settings, sample):
    created = reader.post("/api/v1/transports", json={"id": "NEW", "name": "Livraison"})
    assert created.status_code == 201
    assert reader.post("/api/v1/transports", json={"id": "NEW", "name": "Livraison"}).status_code == 409
    assert reader.patch("/api/v1/transports/NEW", json={"status": "completed"}).status_code == 200
    assert send(reader, settings, sample(transport_id="NEW")).status_code == 409


def test_mongo_failure_never_acknowledges(client, settings, sample, store, monkeypatch):
    def fail(*args, **kwargs):
        raise ServerSelectionTimeoutError("offline")
    monkeypatch.setattr(store, "ingest", fail)
    assert send(client, settings, sample()).status_code == 503


def test_restart_replay_and_late_data(reader, sample, store):
    for i in [0, 1, 2, 3, 4, 6]:
        store.ingest(Telemetry(**sample(i, 12.0)))
    store.reconcile()
    assert store.db.alerts.count_documents({}) == 0
    store.ingest(Telemetry(**sample(5, 12.0)))
    store.reconcile()
    store.reconcile()
    assert store.state()["sequence"] == 6
    assert store.db.alerts.count_documents({}) == 1
    assert store.db.measurements.count_documents({"projected": False}) == 0


def test_pagination_csv_and_unknown_clock(reader, sample, store):
    for i in range(4):
        store.ingest(Telemetry(**sample(i, measured_at=None)))
    store.reconcile()
    assert reader.get("/api/v1/vehicles/VEH-001/state").json()["freshness"] == "unknown"
    data = reader.get("/api/v1/transports/TRIP-DEMO-001/measurements?limit=2&offset=2").json()
    assert data["total"] == 4
    assert len(data["items"]) == 2
    response = reader.get("/api/v1/transports/TRIP-DEMO-001/export.csv")
    assert response.status_code == 200
    assert "temperature_c" in response.text


def test_logout_revokes_browser_cookie(reader):
    assert reader.get("/api/v1/auth/session").status_code == 200
    reader.post("/api/v1/auth/logout")
    assert reader.get("/api/v1/auth/session").status_code == 401


def test_cross_origin_mutation_rejected(reader):
    assert reader.post("/api/v1/transports", json={"id": "BAD", "name": "test"},
                       headers={"Origin": "https://untrusted.example"}).status_code == 403
