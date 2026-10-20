from app.firebase import FirebasePublisher
from app.models import Telemetry


def test_failed_publication_is_retried(settings, store, sample, monkeypatch):
    publisher = FirebasePublisher(settings)
    store.ingest(Telemetry(**sample()))
    store.reconcile()
    def fail(*args):
        raise RuntimeError("offline")
    monkeypatch.setattr(publisher, "write", fail)
    publisher.publish_pending(store)
    assert store.state()["firebase_synced"] is False
    assert publisher.last_error is not None
    written = []
    monkeypatch.setattr(publisher, "write", lambda path, data: written.append((path, data)))
    publisher.publish_pending(store)
    assert store.state()["firebase_synced"] is True
    assert len(written) == 1
    assert publisher.last_error is None
    publisher.close()


def test_periodic_republication_recovers_an_empty_emulator(settings, store, sample, monkeypatch):
    publisher = FirebasePublisher(settings)
    store.ingest(Telemetry(**sample()))
    store.reconcile()
    writes = []
    monkeypatch.setattr(publisher, "write", lambda path, data: writes.append(data))
    publisher.publish_pending(store)
    assert store.state()["firebase_synced"] is True
    publisher.publish_pending(store)
    assert len(writes) == 1
    publisher.last_refresh = 0
    publisher.publish_pending(store)
    assert len(writes) == 2
    publisher.close()
