# demo/rpc_server.py
import os, json, time, uuid, socket, struct
from pathlib import Path

HOST = os.getenv("RPC_HOST", "127.0.0.1")
PORT = int(os.getenv("RPC_PORT", "6000"))
AUDIT = Path("logs/audit.jsonl")

def epoch_ms() -> int:
    return int(time.time() * 1000)

def send_json(conn: socket.socket, obj: dict) -> None:
    raw = json.dumps(obj).encode("utf-8")
    hdr = struct.pack("!I", len(raw))        # 4-byte length prefix (big-endian)
    conn.sendall(hdr + raw)

def recv_json(conn: socket.socket) -> dict:
    # read 4-byte length, then that many bytes
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

def audit_write(entry: dict):
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    entry["ts_ms"] = epoch_ms()
    with AUDIT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

def handle_lock(req: dict) -> dict:
    # pretend to actuate a body control module
    time.sleep(0.05)  # small delay to simulate work
    return {"status": {"code": "OK", "message": "Doors locked"}, "success": True}

def main():
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
                method = req.get("method", "")

                if method == "lock":
                    res = handle_lock(req)
                else:
                    res = {"status": {"code": "ERR", "message": f"Unknown method '{method}'"}}

                # echo correlation_id back
                res["correlation_id"] = corr
                send_json(conn, res)

                # audit
                audit_write({
                    "correlation_id": corr,
                    "request": {"method": method},
                    "response": res
                })
    finally:
        srv.close()

if __name__ == "__main__":
    main()
