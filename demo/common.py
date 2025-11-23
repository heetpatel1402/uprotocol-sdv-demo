from __future__ import annotations

import json
import socket
import struct
import time
from typing import Optional


# ---------------- UDP helpers -----------------


def udp_bind(host: str, port: int, timeout_s: Optional[float] = None) -> socket.socket:
    """Bind a UDP socket on (host, port). Optional timeout."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        # SO_REUSEPORT may not exist on Windows
        s.setsockopt(socket.SOL_SOCKET, getattr(socket, "SO_REUSEPORT", 15), 1)
    except Exception:
        pass
    s.bind((host, port))
    if timeout_s is not None:
        s.settimeout(timeout_s)
    return s


def udp_send_json(sock: socket.socket, addr: tuple[str, int], obj: dict) -> None:
    """Send a JSON-encoded dict over UDP."""
    data = json.dumps(obj).encode("utf-8")
    sock.sendto(data, addr)


def udp_recv_json(sock: socket.socket) -> dict:
    """Receive a JSON object over UDP."""
    data, _ = sock.recvfrom(65535)
    return json.loads(data.decode("utf-8"))


# ---------------- TCP helpers (RPC) -----------------


def tcp_listen(host: str, port: int) -> socket.socket:
    """Start a TCP listening socket."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((host, port))
    s.listen(8)
    return s


def tcp_connect(host: str, port: int, timeout_s: float = 5.0) -> socket.socket:
    """Open a TCP client connection."""
    return socket.create_connection((host, port), timeout=timeout_s)


def send_json(conn: socket.socket, obj: dict) -> None:
    """Send a length-prefixed JSON object over TCP."""
    raw = json.dumps(obj).encode("utf-8")
    hdr = struct.pack("!I", len(raw))
    conn.sendall(hdr + raw)


def recv_json(conn: socket.socket) -> dict:
    """Receive a length-prefixed JSON object over TCP."""

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


# ---------------- Time helper -----------------


def epoch_ms() -> int:
    """Return current time in milliseconds since epoch."""
    return int(time.time() * 1000)
