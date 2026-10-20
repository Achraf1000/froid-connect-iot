import pytest
from app.engine import replay
from conftest import event


@pytest.mark.parametrize("temperature", [2.0, 5.0, 8.0])
def test_normal_including_boundaries(sample, temperature):
    state, alerts = replay([event(sample(i, temperature)) for i in range(20)])
    assert state["thermal_status"] == "normal"
    assert alerts == []


@pytest.mark.parametrize("temperature", [0.0, 12.0])
def test_alarm_at_30_seconds_and_not_before(sample, temperature):
    data = [event(sample(i, temperature)) for i in range(6)]
    state, alerts = replay(data)
    assert state["thermal_status"] == "pending"
    assert not alerts
    data.append(event(sample(6, temperature)))
    state, alerts = replay(data)
    assert state["thermal_status"] == "alert"
    assert len(alerts) == 1
    assert alerts[0]["duration_seconds"] == 30


def test_millisecond_boundary(sample):
    data = [event(sample(i, 12.0)) for i in range(6)]
    before, events = replay(data + [event(sample(6, 12.0, uptime_ms=29999))])
    assert before["thermal_status"] == "pending"
    assert not events
    at, events = replay(data + [event(sample(6, 12.0, uptime_ms=30000))])
    assert at["thermal_status"] == "alert"
    assert len(events) == 1


def test_short_excursions_do_not_accumulate(sample):
    temps = [12.0] * 5 + [5.0] + [12.0] * 5 + [5.0]
    state, alerts = replay([event(sample(i, t)) for i, t in enumerate(temps)])
    assert state["thermal_status"] == "normal"
    assert not alerts


def test_single_event_then_resolution(sample):
    data = [event(sample(i, 12.0)) for i in range(15)] + [event(sample(15, 5.0))]
    state, alerts = replay(data)
    assert state["thermal_status"] == "normal"
    assert len(alerts) == 1
    assert alerts[0]["status"] == "resolved"
    assert alerts[0]["duration_seconds"] == 75


def test_gap_does_not_prove_continuity(sample):
    data = [event(sample(i, 12.0)) for i in [0, 1, 2, 10]]
    state, alerts = replay(data)
    assert state["thermal_status"] == "pending"
    assert state["excursion_seconds"] == 0
    assert not alerts


def test_missing_sequence_breaks_continuity_even_if_time_close(sample):
    data = [event(sample(i, 12.0)) for i in [0, 1, 2, 3, 5, 6, 7]]
    state, alerts = replay(data)
    assert state["excursion_seconds"] == 10
    assert not alerts


def test_late_replay_restores_order(sample):
    data = [event(sample(i, 12.0)) for i in range(7)]
    state, alerts = replay([data[6], *data[:6]])
    assert state["sequence"] == 6
    assert len(alerts) == 1


def test_network_arrival_times_do_not_control_duration(sample):
    data = [event(sample(i, 12.0)) for i in range(7)]
    for item in data:
        item["received_at"] = "2026-01-01T12:00:00Z"
    state, alerts = replay(data)
    assert state["thermal_status"] == "alert"
    assert alerts[0]["duration_seconds"] == 30


def test_sensor_error_interrupts_without_claiming_resolution(sample):
    data = [event(sample(i, 12.0)) for i in range(7)] + [event(sample(7, None))]
    state, alerts = replay(data)
    assert state["thermal_status"] == "sensor_error"
    assert alerts[0]["status"] == "interrupted"
    assert alerts[0]["ended_at"] is None


def test_boot_reset_does_not_continue_previous_excursion(sample):
    data = [event(sample(i, 12.0)) for i in range(5)]
    data.append(event(sample(0, 12.0, boot_id="new-boot", measured_at=sample(5)["measured_at"])))
    state, alerts = replay(data)
    assert state["excursion_seconds"] == 0
    assert not alerts
