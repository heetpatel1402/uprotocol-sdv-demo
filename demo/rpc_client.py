# # demo/rpc_client.py
import os
import json
import uuid
import socket
import struct

HOST = os.getenv("RPC_HOST", "127.0.0.1")
PORT = int(os.getenv("RPC_PORT", "6000"))


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

    (length,) = struct.unpack("!I", recvn(4))
    raw = recvn(length)
    return json.loads(raw.decode("utf-8"))


def main():
    corr = str(uuid.uuid4())
    req = {"method": "lock", "correlation_id": corr}

    with socket.create_connection((HOST, PORT), timeout=3.0) as conn:
        send_json(conn, req)
        res = recv_json(conn)

    print("[client] RESPONSE:", json.dumps(res), flush=True)


if __name__ == "__main__":
    main()
