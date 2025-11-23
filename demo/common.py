# demo/common.py
from __future__ import annotations

import json
import socket
import struct
import time


# ---- UDP helpers (Pub/Sub) ----

def udp_bind(host: str, port: int, timeout_s: float | None = None) -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        # SO_REUSEPORT where available (Linux/macOS); ignored on Windows
        s.setsockopt(socket.SOL_SOCKET, getattr(socket, "SO_REUSEPORT", 15), 1)
    except Exception:
        pass
    s.bind((host, port))
    if timeout_s is not None:
        s.settimeout(timeout_s)
    return s


def udp_send_json(sock: socket.socket, addr: tuple[str, int], obj: dict) -> None:
    data = json.dumps(obj).encode("utf-8")
    sock.sendto(data, addr)


def udp_recv_json(sock: socket.socket) -> dict:
    data, _ = sock.recvfrom(65535)
    return json.loads(data.decode("utf-8"))


# ---- TCP helpers (RPC) ----

def tcp_listen(host: str, port: int) -> socket.socket:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, port))
    s.listen(8)
    return s


def tcp_connect(host: str, port: int, timeout_s: float = 5.0) -> socket.socket:
    return socket.create_connection((host, port), timeout=timeout_s)


def send_json(conn: socket.socket, obj: dict) -> None:
    raw = json.dumps(obj).encode("utf-8")
    hdr = struct.pack("!I", len(raw))
    conn.sendall(hdr + raw)


def recv_json(conn: socket.socket) -> dict:
    def recvn(n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = conn.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("connection closed")
            buf += chunk
        return buf

    (n,) = struct.unpack("!I", recvn(4))
    raw = recvn(n)
    return json.loads(raw.decode("utf-8"))


def epoch_ms() -> int:
    return int(time.time() * 1000)
# # demo/common.py
# from __future__ import annotations
# import json, socket, struct, time

# # ---- UDP helpers (Pub/Sub) ----
# def udp_bind(host: str, port: int, timeout_s: float|None=None) -> socket.socket:
#     s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#     try:  # SO_REUSEPORT where available
#         s.setsockopt(socket.SOL_SOCKET, getattr(socket, "SO_REUSEPORT", 15), 1)
#     except Exception:
#         pass
#     s.bind((host, port))
#     if timeout_s is not None:
#         s.settimeout(timeout_s)
#     return s

# def udp_send_json(sock: socket.socket, addr: tuple[str,int], obj: dict) -> None:
#     data = json.dumps(obj).encode("utf-8")
#     sock.sendto(data, addr)

# def udp_recv_json(sock: socket.socket) -> dict:
#     data, _ = sock.recvfrom(65535)
#     return json.loads(data.decode("utf-8"))

# # ---- TCP helpers (RPC) ----
# def tcp_listen(host: str, port: int) -> socket.socket:
#     s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#     s.bind((host, port))
#     s.listen(8)
#     return s

# def tcp_connect(host: str, port: int, timeout_s: float=5.0) -> socket.socket:
#     s = socket.create_connection((host,port), timeout=timeout_s)
#     return s

# def send_json(conn: socket.socket, obj: dict) -> None:
#     raw = json.dumps(obj).encode("utf-8")
#     hdr = struct.pack("!I", len(raw))
#     conn.sendall(hdr + raw)

# def recv_json(conn: socket.socket) -> dict:
#     def recvn(n: int) -> bytes:
#         buf = b""
#         while len(buf) < n:
#             chunk = conn.recv(n-len(buf))
#             if not chunk:
#                 raise ConnectionError("connection closed")
#             buf += chunk
#         return buf
#     (n,) = struct.unpack("!I", recvn(4))
#     raw = recvn(n)
#     return json.loads(raw.decode("utf-8"))

# def epoch_ms() -> int:
#     return int(time.time() * 1000)
