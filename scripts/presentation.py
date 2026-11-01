"""Live, explicitly synthetic presentation through the real telemetry API."""
import argparse
import json
import math
import os
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / ".runtime"
CONTROL = RUNTIME / "presentation-command.json"
STATUS = RUNTIME / "presentation.json"
COMMANDS = ("auto", "normal", "hot", "low", "pause", "resume", "stop")


def write_json(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value), encoding="utf-8")
    # Windows readers may briefly hold the destination without delete sharing.
    for attempt in range(30):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 29:
                raise
            time.sleep(0.05)


def automatic_temperature(elapsed):
    """150-second cycle: normal 20s, high 45s, then normal 85s."""
    phase = elapsed % 150
    return 12.0 if 20 <= phase < 65 else round(5 + 0.3 * math.sin(elapsed / 12), 2)


def run(duration):
    config = dotenv_values(ROOT / ".env")
    transport = "PRESENTATION-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    boot = "presentation-" + uuid.uuid4().hex[:16]
    started = time.monotonic()
    start_utc = datetime.now(timezone.utc)
    # Preload a clearly synthetic history for a useful chart on first opening.
    history_count = 60
    headers = {"X-Device-Key": config["DEVICE_API_KEY"]}
    status = {"pid": os.getpid(), "transport_id": transport,
              "url": f"http://127.0.0.1:8000/?transport={transport}", "running": True}
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=10) as client:
        client.post("/api/v1/auth/login", json={"password": config["DASHBOARD_PASSWORD"]}).raise_for_status()
        client.post("/api/v1/transports", json={
            "id": transport, "name": "Présentation guidée · " + datetime.now().strftime("%H:%M"),
        }).raise_for_status()

        def send(sequence, elapsed, temperature, at, local_alarm):
            progress = min(max(elapsed, 0) / 600, 1)
            payload = {
                "schema_version": 1, "config_version": 1, "vehicle_id": "VEH-001",
                "transport_id": transport, "boot_id": boot, "sequence": sequence,
                "uptime_ms": int((history_count * 5 + elapsed) * 1000),
                "measured_at": at.isoformat(), "temperature_c": temperature,
                "latitude": round(36.8065 + progress * 0.0715, 6),
                "longitude": round(10.1815 + progress * 0.1215, 6),
                "sensor_status": "ok", "local_alarm": local_alarm,
                "source": "simulator", "dropped_count": 0,
            }
            response = client.post("/api/v1/telemetry", json=payload, headers=headers)
            response.raise_for_status()
            return response.status_code

        for i in range(history_count):
            elapsed = (i - history_count) * 5
            temperature = 12.0 if 15 <= i < 25 else round(5 + 0.3 * math.sin(i / 5), 2)
            send(i, elapsed, temperature, start_utc + timedelta(seconds=elapsed), 21 <= i < 25)
        write_json(CONTROL, {"id": uuid.uuid4().hex, "command": "auto"})
        write_json(STATUS, status)
        print("DEMONSTRATION LOCALE - mesures synthetiques, API/MongoDB/Firebase reels", flush=True)
        print(status["url"], flush=True)
        mode, paused, previous_command = "auto", False, None
        pending_since, previous_sample = None, None
        sequence, next_sample = history_count, time.monotonic()
        auto_started = next_sample
        try:
            while time.monotonic() - started < duration:
                now = time.monotonic()
                try:
                    command = json.loads(CONTROL.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    command = {}
                if command.get("id") != previous_command:
                    previous_command = command.get("id")
                    action = command.get("command")
                    if action == "stop":
                        break
                    if action in ("auto", "normal", "hot", "low"):
                        mode, paused = action, False
                        if action == "auto":
                            auto_started = now
                    elif action in ("pause", "resume"):
                        paused = action == "pause"
                    print(f"Commande: {action} | mode={mode} | pause={paused}", flush=True)
                if not paused and now >= next_sample:
                    elapsed = now - started
                    temperature = automatic_temperature(now - auto_started) if mode == "auto" else {
                        "normal": 5.0, "hot": 12.0, "low": 0.0,
                    }[mode]
                    if previous_sample is not None and now - previous_sample > 10:
                        pending_since = None
                    if temperature < 2 or temperature > 8:
                        if pending_since is None:
                            pending_since = now
                    else:
                        pending_since = None
                    alarm = pending_since is not None and now - pending_since >= 30
                    try:
                        code = send(sequence, elapsed, temperature, datetime.now(timezone.utc), alarm)
                        print(f"seq={sequence} temp={temperature:.2f} alarm={alarm} HTTP={code}", flush=True)
                        sequence += 1
                        previous_sample = now
                    except httpx.HTTPError as exc:
                        # Do not print request headers or credentials.
                        print(f"Envoi indisponible ({type(exc).__name__}), reprise dans 5 s.", flush=True)
                    next_sample = now + 5
                    status.update(mode=mode, temperature=temperature, alarm=alarm)
                status.update(paused=paused, remaining_seconds=max(0, int(duration - (now - started))))
                write_json(STATUS, status)
                time.sleep(0.25)
        finally:
            status["running"] = False
            write_json(STATUS, status)
            print("Demonstration arretee. Historique conserve.", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--command", choices=COMMANDS)
    parser.add_argument("--duration", type=int, default=14400)
    args = parser.parse_args()
    RUNTIME.mkdir(exist_ok=True)
    if args.command:
        write_json(CONTROL, {"id": uuid.uuid4().hex, "command": args.command})
        print("Commande envoyee :", args.command)
    else:
        run(args.duration)


if __name__ == "__main__":
    main()
