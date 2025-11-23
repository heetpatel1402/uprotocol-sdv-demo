from __future__ import annotations

import os
import socket
from typing import Optional

# --- Imports that work both in CI (package) and locally -----------------
try:
    # When imported as demo.alert_service (CI, python -m demo.alert_service)
    from demo.common import udp_bind, udp_recv_json, udp_send_json, epoch_ms
except ImportError:
    # When run as a plain script from project root (rare)
    from common import udp_bind, udp_recv_json, udp_send_json, epoch_ms

try:
    from demo.config_store import get_effective_speed_limit
except ImportError:
    from config_store import get_effective_speed_limit

# Optional history logging of alerts
try:
    from demo.history_utils import append_alert
except ImportError:
    try:
        from history_utils import append_alert
    except ImportError:
        append_alert = None  # type: ignore

# -----------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------
IN_HOST = os.getenv("ALERT_IN_HOST", "127.0.0.1")
IN_PORT = int(os.getenv("ALERT_IN_PORT", "50052"))     # telemetry in
OUT_HOST = os.getenv("ALERT_OUT_HOST", "127.0.0.1")
OUT_PORT = int(os.getenv("ALERT_OUT_PORT", "50053"))   # alerts out

DEBOUNCE_MS = int(os.getenv("ALERT_DEBOUNCE_MS", "2000"))
DEFAULT_THRESHOLD = float(os.getenv("SPEED_THRESHOLD", "80"))

# NEW: bounded mode for tests (FR-1 / FR-2)
# 0  => run forever (normal)
# >0 => socket timeout in seconds, process at most one message then exit
ALERT_TIMEOUT = float(os.getenv("ALERT_TIMEOUT", "0"))


def _process_one(sub: socket.socket,
                 pub: socket.socket,
                 last_alert_ms: Optional[int]) -> Optional[int]:
    """Receive one telemetry event and emit SPEED_ALERT if needed.

    Returns updated last_alert_ms.
    """
    evt = udp_recv_json(sub)
    kmh = float(evt.get("payload", {}).get("kmh", 0.0))
    now = epoch_ms()

    # FR-9: pick final limit from config_store (RPC + geofence)
    effective_limit = get_effective_speed_limit(DEFAULT_THRESHOLD)

    if kmh > effective_limit and (now - (last_alert_ms or 0)) >= DEBOUNCE_MS:
        last_alert_ms = now
        alert = {
            "type": "SPEED_ALERT",
            "kmh": kmh,
            "limit": effective_limit,
            "timestamp_ms": now,
            "source": "up://car-01/vehicle.telemetry/speed?v=1",
        }
        udp_send_json(pub, (OUT_HOST, OUT_PORT), alert)
        print("[alert] emitted:", alert, flush=True)

        if append_alert:
            append_alert(alert)

    return last_alert_ms


def main() -> None:
    bounded = ALERT_TIMEOUT > 0

    # In bounded mode we attach a timeout; otherwise block forever
    sub = udp_bind(IN_HOST, IN_PORT, ALERT_TIMEOUT if bounded else None)
    pub = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    last_alert_ms: Optional[int] = 0

    print(
        f"[alert] listening udp://{IN_HOST}:{IN_PORT}, "
        f"emitting to {OUT_HOST}:{OUT_PORT}",
        flush=True,
    )

    try:
        if not bounded:
            # Normal infinite service
            while True:
                last_alert_ms = _process_one(sub, pub, last_alert_ms)
        else:
            # Test mode: process at most one event, then exit cleanly
            try:
                last_alert_ms = _process_one(sub, pub, last_alert_ms)
            except socket.timeout:
                # No telemetry within ALERT_TIMEOUT seconds – just exit
                print("[alert] bounded mode timeout, exiting", flush=True)
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
#     from demo.config_store import get_effective_speed_limit, get_config_snapshot
# except ImportError:
#     from config_store import get_effective_speed_limit, get_config_snapshot

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

#             # FR-9 effective limit (RPC + geofence + default)
#             effective_limit = get_effective_speed_limit(DEFAULT_THRESHOLD)
#             # Get current zone for weighting behaviour (FR-8)
#             cfg = get_config_snapshot()
#             zone = cfg.get("current_zone")

#             if kmh > effective_limit and (now - (last_alert_ms or 0)) >= DEBOUNCE_MS:
#                 last_alert_ms = now
#                 alert = {
#                     "type": "SPEED_ALERT",
#                     "kmh": kmh,
#                     "limit": effective_limit,
#                     "timestamp_ms": now,
#                     "source": "up://car-01/vehicle.telemetry/speed?v=1",
#                     "zone": zone,
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
# # # demo/alert_service.py
# # from __future__ import annotations

# # import os
# # import socket
# # from typing import Optional

# # try:
# #     # run as module: python -m demo.alert_service
# #     from demo.common import udp_bind, udp_recv_json, udp_send_json, epoch_ms
# # except ImportError:
# #     # run as script: python demo/alert_service.py
# #     from common import udp_bind, udp_recv_json, udp_send_json, epoch_ms

# # try:
# #     from demo.config_store import get_effective_speed_limit
# # except ImportError:
# #     from config_store import get_effective_speed_limit

# # try:
# #     from demo.history_utils import append_alert
# # except ImportError:
# #     try:
# #         from history_utils import append_alert
# #     except ImportError:
# #         append_alert = None  # type: ignore

# # IN_HOST = os.getenv("ALERT_IN_HOST", "127.0.0.1")
# # IN_PORT = int(os.getenv("ALERT_IN_PORT", "50052"))   # telemetry for alerts
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
# #             payload = evt.get("payload", {}) or {}
# #             kmh = float(payload.get("kmh", 0.0))
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


# # # import os
# # # import socket
# # # from typing import Optional



# # # import os
# # # import socket
# # # from typing import Optional

# # # # this is safe in both run styles
# # # try:
# # #     # if run as module: python -m demo.alert_service
# # #     from demo.common import udp_bind, udp_recv_json, udp_send_json, epoch_ms
# # # except ImportError:
# # #     # if run as script: python demo/alert_service.py
# # #     from common import udp_bind, udp_recv_json, udp_send_json, epoch_ms

# # # try:
# # #     from demo.config_store import get_effective_speed_limit
# # # except ImportError:
# # #     from config_store import get_effective_speed_limit

# # # # optional: persist alerts
# # # try:
# # #     from demo.history_utils import append_alert
# # # except ImportError:
# # #     try:
# # #         from history_utils import append_alert
# # #     except ImportError:
# # #         append_alert = None  # type: ignore


# # # IN_HOST = os.getenv("ALERT_IN_HOST", "127.0.0.1")
# # # IN_PORT = int(os.getenv("ALERT_IN_PORT", "50052"))    # telemetry in
# # # OUT_HOST = os.getenv("ALERT_OUT_HOST", "127.0.0.1")
# # # OUT_PORT = int(os.getenv("ALERT_OUT_PORT", "50053"))  # alerts out

# # # DEBOUNCE_MS = int(os.getenv("ALERT_DEBOUNCE_MS", "2000"))
# # # DEFAULT_THRESHOLD = float(os.getenv("SPEED_THRESHOLD", "80"))


# # # def main():
# # #     sub = udp_bind(IN_HOST, IN_PORT, None)
# # #     pub = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# # #     last_alert_ms: Optional[int] = 0

# # #     print(f"[alert] listening udp://{IN_HOST}:{IN_PORT}, emitting to {OUT_HOST}:{OUT_PORT}", flush=True)

# # #     try:
# # #         while True:
# # #             evt = udp_recv_json(sub)
# # #             kmh = float(evt.get("payload", {}).get("kmh", 0.0))
# # #             now = epoch_ms()

# # #             effective_limit = get_effective_speed_limit(DEFAULT_THRESHOLD)

# # #             if kmh > effective_limit and (now - (last_alert_ms or 0)) >= DEBOUNCE_MS:
# # #                 last_alert_ms = now
# # #                 alert = {
# # #                     "type": "SPEED_ALERT",
# # #                     "kmh": kmh,
# # #                     "limit": effective_limit,
# # #                     "timestamp_ms": now,
# # #                     "source": "up://car-01/vehicle.telemetry/speed?v=1",
# # #                 }
# # #                 udp_send_json(pub, (OUT_HOST, OUT_PORT), alert)
# # #                 print("[alert] emitted:", alert, flush=True)

# # #                 if append_alert:
# # #                     append_alert(alert)

# # #     except Exception as e:
# # #         print("[alert] error:", repr(e), flush=True)
# # #     finally:
# # #         sub.close()
# # #         pub.close()


# # # if __name__ == "__main__":
# # #     main()
