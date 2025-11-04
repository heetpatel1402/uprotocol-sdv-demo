# demo/status_summary.py
import os, time, json, socket, threading
from pathlib import Path
from common import udp_bind, udp_recv_json, udp_send_json, epoch_ms

# inputs
SPEED_HOST = os.getenv("SUM_SPEED_HOST", "127.0.0.1")
SPEED_PORT = int(os.getenv("SUM_SPEED_PORT", "50052"))  # listen to telemetry
AUDIT_FILE = Path(os.getenv("SUM_AUDIT_PATH", "logs/audit.jsonl"))

# output
OUT_HOST = os.getenv("SUM_OUT_HOST", "127.0.0.1")
OUT_PORT = int(os.getenv("SUM_OUT_PORT", "50054"))

INTERVAL_S = float(os.getenv("SUM_INTERVAL_S", "10"))

state = {"speed_kmh": None, "locked": None, "last_lock_ts": None}

def speed_listener():
    sock = udp_bind(SPEED_HOST, SPEED_PORT, None)
    try:
        while True:
            evt = udp_recv_json(sock)
            state["speed_kmh"] = evt.get("payload", {}).get("kmh")
    finally:
        sock.close()

def audit_watcher():
    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    last_size = 0
    while True:
        try:
            if AUDIT_FILE.exists():
                sz = AUDIT_FILE.stat().st_size
                if sz > last_size:
                    with AUDIT_FILE.open("r", encoding="utf-8") as f:
                        f.seek(last_size)
                        for line in f:
                            try:
                                obj = json.loads(line)
                                if "lock" in obj.get("request", {}):
                                    state["locked"] = bool(obj.get("response", {}).get("success", False))
                                    state["last_lock_ts"] = obj.get("ts_ms")
                            except Exception:
                                pass
                    last_size = sz
        except Exception:
            pass
        time.sleep(1)

def publisher():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    addr = (OUT_HOST, OUT_PORT)
    try:
        while True:
            msg = {
                "type": "VEHICLE_STATUS_SUMMARY",
                "speed_kmh": state["speed_kmh"],
                "locked": state["locked"],
                "last_update": epoch_ms(),
            }
            udp_send_json(sock, addr, msg)
            print("[summary] emitted:", msg, flush=True)
            time.sleep(INTERVAL_S)
    finally:
        sock.close()

if __name__ == "__main__":
    threading.Thread(target=speed_listener, daemon=True).start()
    threading.Thread(target=audit_watcher, daemon=True).start()
    publisher()
