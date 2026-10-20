"""Inject explicit synthetic telemetry through the same HTTP API as the ESP32."""
import argparse
import math
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=["normal", "short", "long", "low", "demo"], default="demo")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--transport", default="TRIP-DEMO-001")
    parser.add_argument("--realtime", action="store_true")
    parser.add_argument("--count", type=int, default=100)
    args = parser.parse_args()
    config = dotenv_values(ROOT / ".env")
    boot = "sim-" + uuid.uuid4().hex[:16]
    base = datetime.now(timezone.utc)
    if not args.realtime:
        base -= timedelta(seconds=(args.count - 1) * 5)
    with httpx.Client(base_url=args.url, timeout=10) as client:
        response = client.post("/api/v1/auth/login", json={"password": config["DASHBOARD_PASSWORD"]})
        response.raise_for_status()
        transports = client.get("/api/v1/transports").json()
        if args.transport not in {t["id"] for t in transports}:
            client.post("/api/v1/transports", json={"id": args.transport, "name": f"Essai {args.scenario} · Tunis → La Marsa"}).raise_for_status()
        for i in range(args.count):
            temp = 5.0 + math.sin(i / 7) * 0.65
            excursion_start = None
            if args.scenario == "short" and 5 <= i < 9:
                temp, excursion_start = 12.0, 5
            elif args.scenario in ("long", "low") and i >= 5:
                temp, excursion_start = (12.0 if args.scenario == "long" else 0.0), 5
            elif args.scenario == "demo" and 30 <= i < 42:
                temp, excursion_start = 10.0 + math.sin((i - 30) / 3) * 1.5, 30
            at = datetime.now(timezone.utc) if args.realtime else base + timedelta(seconds=i * 5)
            progress = min(i / max(1, args.count - 1), 1)
            payload = {
                "schema_version": 1, "config_version": 1,
                "vehicle_id": "VEH-001", "transport_id": args.transport, "boot_id": boot,
                "sequence": i, "uptime_ms": i * 5000,
                "measured_at": at.isoformat(),
                "temperature_c": round(temp, 2), "latitude": 36.8065 + progress * 0.0715,
                "longitude": 10.1815 + progress * 0.1215,
                "sensor_status": "ok", "local_alarm": excursion_start is not None and (i - excursion_start) * 5 >= 30,
                "source": "simulator", "dropped_count": 0,
            }
            response = client.post("/api/v1/telemetry", json=payload, headers={"X-Device-Key": config["DEVICE_API_KEY"]})
            response.raise_for_status()
            print(f"#{i:03d} | {temp:.2f} C | HTTP {response.status_code}", flush=True)
            if args.realtime:
                time.sleep(5)


if __name__ == "__main__":
    main()
