# demo/rpc_server.py
import socket, json, uuid, time

SERVER_PORT = 50052  # where we accept requests

def uuri(authority, ue_id, resource, v=1):
    return f"up://{authority}/{ue_id}{resource}?v={v}"

def build_response(req, ok: bool, message: str):
    return {
        "type": "RESPONSE",
        "id": str(uuid.uuid4()),
        "correlation_id": req["id"],
        "source": uuri("car-01", "body.control", "/service"),
        "target": req["source"],
        "content_type": "application/json",
        "status": {"code": "OK" if ok else "ERROR", "message": message},
        "payload": {"success": ok, "timestamp_ms": int(time.time() * 1000)},
    }

def main():
    print(f"[svc] BodyControl listening on udp://127.0.0.1:{SERVER_PORT}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", SERVER_PORT))

    while True:
        data, addr = sock.recvfrom(65535)
        req = json.loads(data.decode("utf-8"))
        print("\n[svc] REQUEST from", addr)
        print(json.dumps(req, indent=2))

        # very dumb handler: expects payload {"lock": true|false}
        lock = bool(req.get("payload", {}).get("lock", True))
        resp = build_response(req, ok=True, message=("Doors locked" if lock else "Doors unlocked"))

        # reply to the sender address/port (client binds to a known port)
        sock.sendto(json.dumps(resp).encode("utf-8"), addr)
        print("[svc] RESPONSE sent (corr=", resp["correlation_id"][:8], "…)", sep="")

if __name__ == "__main__":
    main()
