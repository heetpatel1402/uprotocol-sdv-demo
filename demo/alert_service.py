# demo/alert_service.py
from __future__ import annotations

import os
import socket
from typing import Optional

try:
    # run as module: python -m demo.alert_service
    from demo.common import udp_bind, udp_recv_json, udp_send_json, epoch_ms
except ImportError:
    # run as script: python demo/alert_service.py
    from common import udp_bind, udp_recv_json, udp_send_json, epoch_ms

try:
    from demo.config_store import get_effective_speed_limit, get_config_snapshot
except ImportError:
    from config_store import get_effective_speed_limit, get_config_snapshot

try:
    from demo.history_utils import append_alert
except ImportError:
    try:
        from history_utils import append_alert
    except ImportError:
        append_alert = None  # type: ignore

IN_HOST = os.getenv("ALERT_IN_HOST", "127.0.0.1")
IN_PORT = int(os.getenv("ALERT_IN_PORT", "50052"))   # telemetry for alerts
OUT_HOST = os.getenv("ALERT_OUT_HOST", "127.0.0.1")
OUT_PORT = int(os.getenv("ALERT_OUT_PORT", "50053"))  # alerts out

DEBOUNCE_MS = int(os.getenv("ALERT_DEBOUNCE_MS", "2000"))
DEFAULT_THRESHOLD = float(os.getenv("SPEED_THRESHOLD", "80"))


def main():
    sub = udp_bind(IN_HOST, IN_PORT, None)
    pub = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    last_alert_ms: Optional[int] = 0

    print(f"[alert] listening udp://{IN_HOST}:{IN_PORT}, emitting to {OUT_HOST}:{OUT_PORT}", flush=True)

    try:
        while True:
            evt = udp_recv_json(sub)
            payload = evt.get("payload", {}) or {}
            kmh = float(payload.get("kmh", 0.0))
            now = epoch_ms()

            # FR-9 effective limit (RPC + geofence + default)
            effective_limit = get_effective_speed_limit(DEFAULT_THRESHOLD)
            # Get current zone for weighting behaviour (FR-8)
            cfg = get_config_snapshot()
            zone = cfg.get("current_zone")

            if kmh > effective_limit and (now - (last_alert_ms or 0)) >= DEBOUNCE_MS:
                last_alert_ms = now
                alert = {
                    "type": "SPEED_ALERT",
                    "kmh": kmh,
                    "limit": effective_limit,
                    "timestamp_ms": now,
                    "source": "up://car-01/vehicle.telemetry/speed?v=1",
                    "zone": zone,
                }
                udp_send_json(pub, (OUT_HOST, OUT_PORT), alert)
                print("[alert] emitted:", alert, flush=True)

                if append_alert:
                    append_alert(alert)

    except Exception as e:
        print("[alert] error:", repr(e), flush=True)
    finally:
        sub.close()
        pub.close()


if __name__ == "__main__":
    main()
# # demo/alert_service.py
# from __future__ import annotations

# import os
# import socket
# from typing import Optional

# try:
#     # run as module: python -m demo.alert_service
#     from demo.common import udp_bind, udp_recv_json, udp_send_json, epoch_ms
# except ImportError:
#     # run as script: python demo/alert_service.py
#     from common import udp_bind, udp_recv_json, udp_send_json, epoch_ms

# try:
#     from demo.config_store import get_effective_speed_limit
# except ImportError:
#     from config_store import get_effective_speed_limit

# try:
#     from demo.history_utils import append_alert
# except ImportError:
#     try:
#         from history_utils import append_alert
#     except ImportError:
#         append_alert = None  # type: ignore

# IN_HOST = os.getenv("ALERT_IN_HOST", "127.0.0.1")
# IN_PORT = int(os.getenv("ALERT_IN_PORT", "50052"))   # telemetry for alerts
# OUT_HOST = os.getenv("ALERT_OUT_HOST", "127.0.0.1")
# OUT_PORT = int(os.getenv("ALERT_OUT_PORT", "50053"))  # alerts out

# DEBOUNCE_MS = int(os.getenv("ALERT_DEBOUNCE_MS", "2000"))
# DEFAULT_THRESHOLD = float(os.getenv("SPEED_THRESHOLD", "80"))


# def main():
#     sub = udp_bind(IN_HOST, IN_PORT, None)
#     pub = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     last_alert_ms: Optional[int] = 0

#     print(f"[alert] listening udp://{IN_HOST}:{IN_PORT}, emitting to {OUT_HOST}:{OUT_PORT}", flush=True)

#     try:
#         while True:
#             evt = udp_recv_json(sub)
#             payload = evt.get("payload", {}) or {}
#             kmh = float(payload.get("kmh", 0.0))
#             now = epoch_ms()

#             effective_limit = get_effective_speed_limit(DEFAULT_THRESHOLD)

#             if kmh > effective_limit and (now - (last_alert_ms or 0)) >= DEBOUNCE_MS:
#                 last_alert_ms = now
#                 alert = {
#                     "type": "SPEED_ALERT",
#                     "kmh": kmh,
#                     "limit": effective_limit,
#                     "timestamp_ms": now,
#                     "source": "up://car-01/vehicle.telemetry/speed?v=1",
#                 }
#                 udp_send_json(pub, (OUT_HOST, OUT_PORT), alert)
#                 print("[alert] emitted:", alert, flush=True)

#                 if append_alert:
#                     append_alert(alert)

#     except Exception as e:
#         print("[alert] error:", repr(e), flush=True)
#     finally:
#         sub.close()
#         pub.close()


# if __name__ == "__main__":
#     main()


# # import os
# # import socket
# # from typing import Optional



# # import os
# # import socket
# # from typing import Optional

# # # this is safe in both run styles
# # try:
# #     # if run as module: python -m demo.alert_service
# #     from demo.common import udp_bind, udp_recv_json, udp_send_json, epoch_ms
# # except ImportError:
# #     # if run as script: python demo/alert_service.py
# #     from common import udp_bind, udp_recv_json, udp_send_json, epoch_ms

# # try:
# #     from demo.config_store import get_effective_speed_limit
# # except ImportError:
# #     from config_store import get_effective_speed_limit

# # # optional: persist alerts
# # try:
# #     from demo.history_utils import append_alert
# # except ImportError:
# #     try:
# #         from history_utils import append_alert
# #     except ImportError:
# #         append_alert = None  # type: ignore


# # IN_HOST = os.getenv("ALERT_IN_HOST", "127.0.0.1")
# # IN_PORT = int(os.getenv("ALERT_IN_PORT", "50052"))    # telemetry in
# # OUT_HOST = os.getenv("ALERT_OUT_HOST", "127.0.0.1")
# # OUT_PORT = int(os.getenv("ALERT_OUT_PORT", "50053"))  # alerts out

# # DEBOUNCE_MS = int(os.getenv("ALERT_DEBOUNCE_MS", "2000"))
# # DEFAULT_THRESHOLD = float(os.getenv("SPEED_THRESHOLD", "80"))


# # def main():
# #     sub = udp_bind(IN_HOST, IN_PORT, None)
# #     pub = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# #     last_alert_ms: Optional[int] = 0

# #     print(f"[alert] listening udp://{IN_HOST}:{IN_PORT}, emitting to {OUT_HOST}:{OUT_PORT}", flush=True)

# #     try:
# #         while True:
# #             evt = udp_recv_json(sub)
# #             kmh = float(evt.get("payload", {}).get("kmh", 0.0))
# #             now = epoch_ms()

# #             effective_limit = get_effective_speed_limit(DEFAULT_THRESHOLD)

# #             if kmh > effective_limit and (now - (last_alert_ms or 0)) >= DEBOUNCE_MS:
# #                 last_alert_ms = now
# #                 alert = {
# #                     "type": "SPEED_ALERT",
# #                     "kmh": kmh,
# #                     "limit": effective_limit,
# #                     "timestamp_ms": now,
# #                     "source": "up://car-01/vehicle.telemetry/speed?v=1",
# #                 }
# #                 udp_send_json(pub, (OUT_HOST, OUT_PORT), alert)
# #                 print("[alert] emitted:", alert, flush=True)

# #                 if append_alert:
# #                     append_alert(alert)

# #     except Exception as e:
# #         print("[alert] error:", repr(e), flush=True)
# #     finally:
# #         sub.close()
# #         pub.close()


# # if __name__ == "__main__":
# #     main()
