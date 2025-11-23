# # # # demo/status_summary.py
# # demo/status_summary.py
# from __future__ import annotations

# import os
# import json
# import time
# import socket
# import threading
# from pathlib import Path

# try:
#     from demo.common import udp_bind, udp_recv_json, udp_send_json, epoch_ms
# except ImportError:
#     from common import udp_bind, udp_recv_json, udp_send_json, epoch_ms

# try:
#     from demo.config_store import get_config_snapshot, get_effective_speed_limit
# except ImportError:
#     from config_store import get_config_snapshot, get_effective_speed_limit

# # TELEMETRY INPUT (from pub_telemetry)
# SPEED_HOST = "127.0.0.1"
# SPEED_PORT = 50056   # <- IMPORTANT: matches second dest in pub_telemetry

# # STATUS OUTPUT (to dashboard)
# OUT_HOST = "127.0.0.1"
# OUT_PORT = 50054

# # AUDIT LOG INPUT (door lock RPC)
# AUDIT_PATH = Path("logs/audit.jsonl")

# INTERVAL_S = 1.0

# state = {
#     "speed_kmh": None,
#     "locked": None,
#     "last_update": None,
# }


# def speed_listener():
#     sock = udp_bind(SPEED_HOST, SPEED_PORT, None)
#     print(f"[summary] listening to telemetry on udp://{SPEED_HOST}:{SPEED_PORT}", flush=True)

#     while True:
#         try:
#             evt = udp_recv_json(sock)
#             if evt.get("type") != "EVENT":
#                 continue
#             payload = evt.get("payload", {}) or {}
#             kmh = payload.get("kmh")
#             if kmh is not None:
#                 state["speed_kmh"] = float(kmh)
#                 state["last_update"] = payload.get("timestamp_ms") or epoch_ms()
#         except Exception as e:
#             print("[summary] telemetry error:", e, flush=True)


# def audit_listener():
#     AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
#     last_size = 0

#     while True:
#         try:
#             if AUDIT_PATH.exists():
#                 size = AUDIT_PATH.stat().st_size
#                 if size > last_size:
#                     with AUDIT_PATH.open("r", encoding="utf-8") as f:
#                         f.seek(last_size)
#                         for line in f:
#                             try:
#                                 log = json.loads(line)
#                                 req = (log.get("request") or {}).get("method", "")
#                                 if req == "lock":
#                                     resp = log.get("response", {}) or {}
#                                     state["locked"] = bool(resp.get("success"))
#                             except Exception:
#                                 pass
#                     last_size = size
#         except Exception:
#             pass
#         time.sleep(0.5)


# def publisher():
#     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     target = (OUT_HOST, OUT_PORT)
#     print(f"[summary] publishing to udp://{OUT_HOST}:{OUT_PORT}", flush=True)

#     while True:
#         cfg = get_config_snapshot()
#         eff_limit = get_effective_speed_limit(default_threshold=80)

#         msg = {
#             "type": "VEHICLE_STATUS_SUMMARY",
#             "speed_kmh": state["speed_kmh"],
#             "locked": state["locked"],
#             "last_update": state["last_update"] or epoch_ms(),
#             "config": cfg,
#             "effective_limit": eff_limit,
#             "zone": cfg.get("current_zone"),
#         }

#         udp_send_json(sock, target, msg)
#         print("[summary] emitted:", msg, flush=True)
#         time.sleep(INTERVAL_S)


# if __name__ == "__main__":
#     threading.Thread(target=speed_listener, daemon=True).start()
#     threading.Thread(target=audit_listener, daemon=True).start()
#     publisher()

# # import os
# # import json
# # import time
# # import socket
# # import threading
# # from pathlib import Path

# # try:
# #     # when run as: python -m demo.status_summary (from project root)
# #     from demo.common import udp_bind, udp_recv_json, udp_send_json, epoch_ms
# # except ImportError:
# #     # when run as: python status_summary.py (from inside demo/)
# #     from common import udp_bind, udp_recv_json, udp_send_json, epoch_ms

# # try:
# #     from demo.config_store import get_config_snapshot, get_effective_speed_limit
# # except ImportError:
# #     from config_store import get_config_snapshot, get_effective_speed_limit


# # # TELEMETRY INPUT (from pub_telemetry)
# # SPEED_HOST = "127.0.0.1"
# # SPEED_PORT = 50052   # MUST match pub_telemetry SUB_PORT

# # # STATUS OUTPUT (to dashboard)
# # OUT_HOST = "127.0.0.1"
# # OUT_PORT = 50054     # dashboard input

# # # AUDIT LOG INPUT (door lock RPC)
# # AUDIT_PATH = Path("logs/audit.jsonl")

# # # How often to emit summary
# # INTERVAL_S = 1.0

# # # --------- Shared State ----------
# # state = {
# #     "speed_kmh": None,
# #     "locked": None,
# #     "last_update": None,
# #     "zone": None,
# # }


# # # ====================================================
# # # 1. Listen to speed telemetry
# # # ====================================================
# # def speed_listener():
# #     sock = udp_bind(SPEED_HOST, SPEED_PORT, None)
# #     print(f"[summary] listening to telemetry on udp://{SPEED_HOST}:{SPEED_PORT}")

# #     while True:
# #         try:
# #             evt = udp_recv_json(sock)

# #             if evt.get("type") != "EVENT":
# #                 continue

# #             payload = evt.get("payload", {})
# #             kmh = payload.get("kmh")

# #             if kmh is not None:
# #                 state["speed_kmh"] = float(kmh)
# #                 state["last_update"] = payload.get("timestamp_ms")
# #         except Exception as e:
# #             print("[summary] telemetry error:", e)


# # # ====================================================
# # # 2. Tail audit.jsonl for door lock state
# # # ====================================================
# # def audit_listener():
# #     AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
# #     last_size = 0

# #     while True:
# #         try:
# #             if AUDIT_PATH.exists():
# #                 size = AUDIT_PATH.stat().st_size
# #                 if size > last_size:
# #                     with AUDIT_PATH.open("r", encoding="utf-8") as f:
# #                         f.seek(last_size)
# #                         for line in f:
# #                             try:
# #                                 log = json.loads(line)
# #                                 req = log.get("request", {})
# #                                 if "lock" in req:
# #                                     resp = log.get("response", {})
# #                                     state["locked"] = bool(resp.get("success"))
# #                             except:
# #                                 pass
# #                     last_size = size
# #         except:
# #             pass

# #         time.sleep(0.5)


# # # ====================================================
# # # 3. Publish VEHICLE_STATUS_SUMMARY
# # # ====================================================
# # def publisher():
# #     sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# #     target = (OUT_HOST, OUT_PORT)
# #     print(f"[summary] publishing to udp://{OUT_HOST}:{OUT_PORT}")

# #     while True:
# #         cfg = get_config_snapshot()
# #         eff_limit = get_effective_speed_limit(default_threshold=80)

# #         msg = {
# #             "type": "VEHICLE_STATUS_SUMMARY",
# #             "speed_kmh": state["speed_kmh"],
# #             "locked": state["locked"],
# #             "last_update": state["last_update"],
# #             "config": cfg,
# #             "effective_limit": eff_limit,
# #             "zone": cfg.get("current_zone"),
# #         }

# #         udp_send_json(sock, target, msg)
# #         print("[summary] emitted:", msg)
# #         time.sleep(INTERVAL_S)


# # # ====================================================
# # # MAIN
# # # ====================================================
# # if __name__ == "__main__":
# #     threading.Thread(target=speed_listener, daemon=True).start()
# #     threading.Thread(target=audit_listener, daemon=True).start()
# #     publisher()
from __future__ import annotations

import json
import socket
import threading
import time
from pathlib import Path

# UDP + time helpers
try:
    from demo.common import udp_bind, udp_recv_json, udp_send_json, epoch_ms
except ImportError:
    from common import udp_bind, udp_recv_json, udp_send_json, epoch_ms

# Config snapshot + effective limit (FR-7/8/9)
try:
    from demo.config_store import get_config_snapshot, get_effective_speed_limit
except ImportError:
    from config_store import get_config_snapshot, get_effective_speed_limit

# TELEMETRY INPUT (from pub_telemetry)
SPEED_HOST = "127.0.0.1"
SPEED_PORT = 50052  # MUST match pub_telemetry SUB_PORT

# STATUS OUTPUT (to dashboard)
OUT_HOST = "127.0.0.1"
OUT_PORT = 50054  # dashboard input

# AUDIT LOG INPUT (door lock RPC)
AUDIT_PATH = Path("logs/audit.jsonl")

# How often to emit summary
INTERVAL_S = 1.0

# --------- Shared State ----------
state = {
    "speed_kmh": None,
    "locked": None,
    "last_update": None,
}


# ====================================================
# 1. Listen to speed telemetry
# ====================================================
def speed_listener() -> None:
    sock = udp_bind(SPEED_HOST, SPEED_PORT, None)
    print(f"[summary] listening telemetry on udp://{SPEED_HOST}:{SPEED_PORT}", flush=True)

    try:
        while True:
            evt = udp_recv_json(sock)

            if evt.get("type") != "EVENT":
                continue

            payload = evt.get("payload", {}) or {}
            kmh = payload.get("kmh")

            if kmh is not None:
                try:
                    state["speed_kmh"] = float(kmh)
                except (TypeError, ValueError):
                    continue
                state["last_update"] = payload.get("timestamp_ms", epoch_ms())
    finally:
        sock.close()


# ====================================================
# 2. Tail audit.jsonl for door lock state
# ====================================================
def audit_listener() -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    last_size = 0

    while True:
        try:
            if AUDIT_PATH.exists():
                size = AUDIT_PATH.stat().st_size
                if size > last_size:
                    with AUDIT_PATH.open("r", encoding="utf-8") as f:
                        f.seek(last_size)
                        for line in f:
                            try:
                                log = json.loads(line)
                            except Exception:
                                continue

                            req = log.get("request", {}) or {}
                            if req.get("method") == "lock":
                                resp = log.get("response", {}) or {}
                                state["locked"] = bool(resp.get("success"))
                    last_size = size
        except Exception:
            # keep watcher alive even on parse errors
            pass

        time.sleep(0.5)


# ====================================================
# 3. Publish VEHICLE_STATUS_SUMMARY
# ====================================================
def publisher() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    target = (OUT_HOST, OUT_PORT)
    print(f"[summary] publishing to udp://{OUT_HOST}:{OUT_PORT}", flush=True)

    try:
        while True:
            cfg = get_config_snapshot()
            eff_limit = get_effective_speed_limit(default_threshold=80.0)

            msg = {
                "type": "VEHICLE_STATUS_SUMMARY",
                "speed_kmh": state["speed_kmh"],
                "locked": state["locked"],
                "last_update": state["last_update"],
                "config": cfg,
                "effective_limit": eff_limit,
                # also expose zone at top level (used by dashboard)
                "zone": cfg.get("current_zone"),
            }

            udp_send_json(sock, target, msg)
            print("[summary] emitted:", msg, flush=True)
            time.sleep(INTERVAL_S)
    finally:
        sock.close()


# ====================================================
# MAIN
# ====================================================
if __name__ == "__main__":
    threading.Thread(target=speed_listener, daemon=True).start()
    threading.Thread(target=audit_listener, daemon=True).start()
    publisher()
