# demo/alert_service.py
import os, time
from common import udp_bind, udp_recv_json, udp_send_json, epoch_ms
import socket

IN_HOST = os.getenv("ALERT_IN_HOST", "127.0.0.1")
IN_PORT = int(os.getenv("ALERT_IN_PORT", "50052"))    # same as telemetry port
OUT_HOST = os.getenv("ALERT_OUT_HOST", "127.0.0.1")
OUT_PORT = int(os.getenv("ALERT_OUT_PORT", "50053"))  # alert topic port

THRESH = float(os.getenv("SPEED_THRESHOLD", "80"))
DEBOUNCE_MS = int(os.getenv("ALERT_DEBOUNCE_MS", "2000"))
BOUND_TIMEOUT = float(os.getenv("ALERT_TIMEOUT", "0"))  # 0 => run forever

def main():
    sub = udp_bind(IN_HOST, IN_PORT, None if BOUND_TIMEOUT == 0 else BOUND_TIMEOUT)
    pub = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    last_alert_ms = 0
    try:
        if BOUND_TIMEOUT == 0:
            print(f"[alert] listening udp://{IN_HOST}:{IN_PORT}, emitting to {OUT_HOST}:{OUT_PORT}", flush=True)
            while True:
                evt = udp_recv_json(sub)
                kmh = float(evt.get("payload", {}).get("kmh", 0))
                now = epoch_ms()
                if kmh > THRESH and (now - last_alert_ms) >= DEBOUNCE_MS:
                    last_alert_ms = now
                    alert = {
                        "type": "SPEED_ALERT",
                        "kmh": kmh,
                        "threshold": THRESH,
                        "timestamp_ms": now,
                        "source": "up://car-01/vehicle.telemetry/speed?v=1"
                    }
                    udp_send_json(pub, (OUT_HOST, OUT_PORT), alert)
                    print("[alert] emitted:", alert, flush=True)
        else:
            # bounded: process one message and exit
            evt = udp_recv_json(sub)
            kmh = float(evt.get("payload", {}).get("kmh", 0))
            now = epoch_ms()
            if kmh > THRESH:
                alert = {
                    "type": "SPEED_ALERT",
                    "kmh": kmh,
                    "threshold": THRESH,
                    "timestamp_ms": now,
                    "source": "up://car-01/vehicle.telemetry/speed?v=1"
                }
                udp_send_json(pub, (OUT_HOST, OUT_PORT), alert)
                print("[alert] emitted (bounded):", alert, flush=True)
    except Exception as e:
        print("[alert] end:", repr(e), flush=True)
    finally:
        sub.close(); pub.close()

if __name__ == "__main__":
    main()
