# --- add near the imports in demo/pub_telemetry.py ---
import os
import time
import json
import socket
import uuid

# existing imports stay…

COUNT = int(os.getenv("DEMO_COUNT", "5"))    # how many events to send
DELAY = float(os.getenv("DEMO_DELAY", "0.3"))  # seconds between events

def publish_once(sock, target_addr):
    # build your message exactly how you already do
    evt = {
        "type": "EVENT",
        "id": str(uuid.uuid4()),
        "source": "up://car-01/vehicle.telemetry/publisher?v=1",
        "target": "up://car-01/vehicle.telemetry/speed?v=1",
        "content_type": "application/json",
        "payload": {"kmh": 72, "timestamp_ms": int(time.time() * 1000)},
        "qos": 0,
        "ttl_ms": 2000,
    }
    data = json.dumps(evt).encode("utf-8")
    sock.sendto(data, target_addr)

def main():
    # your existing socket setup; example:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    target_addr = ("127.0.0.1", 50052)

    for _ in range(COUNT):
        publish_once(sock, target_addr)
        if DELAY > 0:
            time.sleep(DELAY)

    # exit cleanly
    sock.close()

if __name__ == "__main__":
    main()
