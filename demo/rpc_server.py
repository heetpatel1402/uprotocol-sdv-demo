# demo/rpc_server.py
from __future__ import annotations

import json
import os
import socket
import struct
import time
import uuid
from pathlib import Path
from typing import Dict, Any

try:
    from demo.config_store import (
        set_rpc_speed_limit,
        get_config_snapshot,
        get_effective_speed_limit,
    )
except ImportError:
    from config_store import (
        set_rpc_speed_limit,
        get_config_snapshot,
        get_effective_speed_limit,
    )

HOST = os.getenv("RPC_HOST", "127.0.0.1")
PORT = int(os.getenv("RPC_PORT", "6000"))
AUDIT = Path("logs/audit.jsonl")


def epoch_ms() -> int:
    return int(time.time() * 1000)


def send_json(conn: socket.socket, obj: Dict[str, Any]) -> None:
    raw = json.dumps(obj).encode("utf-8")
    hdr = struct.pack("!I", len(raw))
    conn.sendall(hdr + raw)


def recv_json(conn: socket.socket) -> Dict[str, Any]:
    def recvn(n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = conn.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("connection closed")
            buf += chunk
        return buf

    (length,) = struct.unpack("!I", recvn(4))
    raw = recvn(length)
    return json.loads(raw.decode("utf-8"))


def audit_write(entry: Dict[str, Any]) -> None:
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    entry["ts_ms"] = epoch_ms()
    with AUDIT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def handle_lock(req: Dict[str, Any]) -> Dict[str, Any]:
    time.sleep(0.05)
    return {"status": {"code": "OK", "message": "Doors locked"}, "success": True}


def handle_set_speed_limit(req: Dict[str, Any]) -> Dict[str, Any]:
    payload = req.get("payload") or {}
    limit = payload.get("limit_kmh")
    if limit is None:
        return {"status": {"code": "ERR", "message": "missing 'limit_kmh'"}}
    try:
        limit = int(limit)
    except ValueError:
        return {"status": {"code": "ERR", "message": "invalid 'limit_kmh'"}}

    set_rpc_speed_limit(limit)
    eff = get_effective_speed_limit(default_threshold=80)
    return {
        "status": {"code": "OK", "message": f"RPC speed limit set to {limit} km/h"},
        "success": True,
        "effective_limit": eff,
    }


def handle_get_config(req: Dict[str, Any]) -> Dict[str, Any]:
    cfg = get_config_snapshot()
    eff = get_effective_speed_limit(default_threshold=80)
    cfg["effective_limit"] = eff
    return {"status": {"code": "OK", "message": "Config snapshot"}, "config": cfg}


def main() -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(8)
    print(f"[rpc] listening tcp://{HOST}:{PORT}", flush=True)

    try:
        while True:
            conn, addr = srv.accept()
            with conn:
                req = recv_json(conn)

                corr = req.get("correlation_id") or str(uuid.uuid4())
                method = (req.get("method") or "").lower()

                if method == "lock":
                    res = handle_lock(req)
                elif method == "set_speed_limit":
                    res = handle_set_speed_limit(req)
                elif method == "get_config":
                    res = handle_get_config(req)
                else:
                    res = {
                        "status": {
                            "code": "ERR",
                            "message": f"Unknown method '{method}'",
                        }
                    }

                res["correlation_id"] = corr
                send_json(conn, res)

                audit_write(
                    {
                        "correlation_id": corr,
                        "remote": str(addr),
                        "request": {"method": method, "payload": req.get("payload")},
                        "response": res,
                    }
                )
    finally:
        srv.close()


if __name__ == "__main__":
    main()
# from __future__ import annotations

# import json
# import os
# import socket
# import struct
# import time
# import uuid
# from pathlib import Path
# from typing import Dict, Any

# try:
#     from demo.config_store import set_rpc_speed_limit, get_config_snapshot, get_effective_speed_limit
# except ImportError:
#     from config_store import set_rpc_speed_limit, get_config_snapshot, get_effective_speed_limit

# HOST = os.getenv("RPC_HOST", "127.0.0.1")
# PORT = int(os.getenv("RPC_PORT", "6000"))
# AUDIT = Path("logs/audit.jsonl")


# def epoch_ms() -> int:
#     return int(time.time() * 1000)


# def send_json(conn: socket.socket, obj: Dict[str, Any]) -> None:
#     raw = json.dumps(obj).encode("utf-8")
#     hdr = struct.pack("!I", len(raw))  # 4-byte length prefix
#     conn.sendall(hdr + raw)


# def recv_json(conn: socket.socket) -> Dict[str, Any]:
#     def recvn(n: int) -> bytes:
#         buf = b""
#         while len(buf) < n:
#             chunk = conn.recv(n - len(buf))
#             if not chunk:
#                 raise ConnectionError("connection closed")
#             buf += chunk
#         return buf

#     (length,) = struct.unpack("!I", recvn(4))
#     raw = recvn(length)
#     return json.loads(raw.decode("utf-8"))


# def audit_write(entry: Dict[str, Any]) -> None:
#     AUDIT.parent.mkdir(parents=True, exist_ok=True)
#     entry["ts_ms"] = epoch_ms()
#     with AUDIT.open("a", encoding="utf-8") as f:
#         f.write(json.dumps(entry) + "\n")


# def handle_lock(req: Dict[str, Any]) -> Dict[str, Any]:
#     time.sleep(0.05)
#     return {"status": {"code": "OK", "message": "Doors locked"}, "success": True}


# def handle_set_speed_limit(req: Dict[str, Any]) -> Dict[str, Any]:
#     payload = req.get("payload") or {}
#     limit = payload.get("limit_kmh")
#     if limit is None:
#         return {"status": {"code": "ERR", "message": "missing 'limit_kmh'"}}
#     try:
#         limit = int(limit)
#     except ValueError:
#         return {"status": {"code": "ERR", "message": "invalid 'limit_kmh'"}}

#     set_rpc_speed_limit(limit)
#     eff = get_effective_speed_limit(default_threshold=80)
#     return {
#         "status": {"code": "OK", "message": f"RPC speed limit set to {limit} km/h"},
#         "success": True,
#         "effective_limit": eff,
#     }


# def handle_get_config(req: Dict[str, Any]) -> Dict[str, Any]:
#     cfg = get_config_snapshot()
#     eff = get_effective_speed_limit(default_threshold=80)
#     cfg["effective_limit"] = eff
#     return {"status": {"code": "OK", "message": "Config snapshot"}, "config": cfg}


# def main() -> None:
#     srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#     srv.bind((HOST, PORT))
#     srv.listen(8)
#     print(f"[rpc] listening tcp://{HOST}:{PORT}", flush=True)

#     try:
#         while True:
#             conn, addr = srv.accept()
#             with conn:
#                 req = recv_json(conn)

#                 corr = req.get("correlation_id") or str(uuid.uuid4())
#                 method = (req.get("method") or "").lower()

#                 if method == "lock":
#                     res = handle_lock(req)
#                 elif method == "set_speed_limit":
#                     res = handle_set_speed_limit(req)
#                 elif method == "get_config":
#                     res = handle_get_config(req)
#                 else:
#                     res = {"status": {"code": "ERR", "message": f"Unknown method '{method}'"}}

#                 res["correlation_id"] = corr
#                 send_json(conn, res)

#                 audit_write({
#                     "correlation_id": corr,
#                     "remote": str(addr),
#                     "request": {"method": method, "payload": req.get("payload")},
#                     "response": res,
#                 })
#     finally:
#         srv.close()


# if __name__ == "__main__":
#     main()
