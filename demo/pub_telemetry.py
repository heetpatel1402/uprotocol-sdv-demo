#!/usr/bin/env python3
import json
import os
import socket
import time
import uuid

# Defaults are safe for CI; you can override locally:
COUNT = int(os.getenv("DEMO_COUNT", "1"))      # how many events to send
DELAY = float(os.getenv("DEMO_DELAY", "0"))    # seconds between events
TARGET_HOST = os.getenv("DEMO_TARGET_HOST", "127.0.0.1")
TARGET_PORT = int(os.getenv("DEMO_TARGET_PORT", "50052"))

def build_event():
    return {
        "type": "EVENT",
        "id": str(uuid.uuid4()),
        "source": "up://car-01/vehicle.telemetry/publisher?v=1",
        "target": "up://car-01/vehicle.telemetry/speed?v=1",
        "content_type": "application/json",
        "payload": {
            "kmh": 72,
            "timestamp_ms": int(time.time() * 1000),
        },
        "qos": 0,
        "ttl_ms": 2000,
    }

def main():
    addr = (TARGET_HOST, TARGET_PORT)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        for _ in range(COUNT):
            evt = build_event()
            sock.sendto(json.dumps(evt).encode("utf-8"), addr)
            if DELAY > 0:
                time.sleep(DELAY)
    finally:
        sock.close()

if __name__ == "__main__":
    main()
