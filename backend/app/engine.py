"""Pure event replay. Durations use device monotonic time, never HTTP arrival time."""
from .config import RULES


def replay(measurements: list[dict], rules: dict | None = None) -> tuple[dict | None, list[dict]]:
    rules = rules or RULES
    if not measurements:
        return None, []
    # Order boot sessions by their earliest observed event, then by monotonic sequence.
    sessions = {}
    for m in measurements:
        key = m["boot_id"]
        event = m["measured_at"] or m["received_at"]
        sessions[key] = min(sessions.get(key, event), event)
    ordered = sorted(measurements, key=lambda m: (sessions[m["boot_id"]], m["boot_id"], m["sequence"]))
    previous = None
    pending = None
    active = None
    alerts = []
    state = None
    gaps = 0
    for m in ordered:
        valid = m["sensor_status"] == "ok"
        continuous = (
            previous is not None
            and m["boot_id"] == previous["boot_id"]
            and m["sequence"] == previous["sequence"] + 1
            and 0 < m["uptime_ms"] - previous["uptime_ms"] <= rules["max_gap_ms"]
            and previous["sensor_status"] == "ok"
            and valid
        )
        if previous is not None and not continuous:
            gaps += 1
            pending = None
            if active:
                active["status"] = "interrupted"
                active["ended_at"] = None
                active["last_observed_at"] = previous["measured_at"] or previous["received_at"]
                active = None
        status = "sensor_error" if not valid else "normal"
        elapsed = 0
        temp = m["temperature_c"]
        outside = valid and (temp < rules["min_c"] or temp > rules["max_c"])
        if outside:
            if pending is None:
                pending = m
            elapsed = m["uptime_ms"] - pending["uptime_ms"]
            status = "alert" if elapsed >= rules["delay_ms"] else "pending"
            if status == "alert":
                if active is None:
                    active = {
                        "id": f'{m["transport_id"]}:{pending["boot_id"]}:{pending["sequence"]}',
                        "transport_id": m["transport_id"],
                        "vehicle_id": m["vehicle_id"],
                        "started_at": pending["measured_at"] or pending["received_at"],
                        "triggered_at": m["measured_at"] or m["received_at"],
                        "ended_at": None,
                        "status": "active",
                        "direction": "high" if temp > rules["max_c"] else "low",
                        "min_c": temp,
                        "max_c": temp,
                        "duration_seconds": elapsed / 1000,
                    }
                    alerts.append(active)
                active["min_c"] = min(active["min_c"], temp)
                active["max_c"] = max(active["max_c"], temp)
                active["duration_seconds"] = elapsed / 1000
        elif valid:
            if active:
                active["status"] = "resolved"
                active["ended_at"] = m["measured_at"] or m["received_at"]
                active["duration_seconds"] = (m["uptime_ms"] - pending["uptime_ms"]) / 1000
            pending = None
            active = None
        else:
            pending = None
        state = {
            **{k: m[k] for k in (
                "vehicle_id", "transport_id", "boot_id", "sequence", "measured_at",
                "received_at", "temperature_c", "latitude", "longitude", "sensor_status",
                "local_alarm", "source", "dropped_count",
            )},
            "thermal_status": status,
            "excursion_seconds": elapsed / 1000,
            "gap_count": gaps,
            "measurement_count": len(ordered),
            "alert_count": len(alerts),
            "clock_synced": m["measured_at"] is not None,
            "rules": rules,
        }
        previous = m
    return state, alerts
