    # demo/rpc_client.py
import socket, json, uuid, time

SERVER_PORT = 50052   # service port
CLIENT_PORT = 50053   # our local port to receive the response

def uuri(authority, ue_id, resource, v=1):
    return f"up://{authority}/{ue_id}{resource}?v={v}"

def build_request(lock: bool):
    return {
        "type": "REQUEST",
        "id": str(uuid.uuid4()),
        "source": uuri("car-01", "mobile.app", "/client"),
        "target": uuri("car-01", "body.control", "/doors/lock"),
        "content_type": "application/json",
        "payload": {"lock": lock},
        "qos": 1,
        "ttl_ms": 3000,
        "timestamp_ms": int(time.time() * 1000),
    }

def main():
    # single socket: bind so the server can reply back to this port
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", CLIENT_PORT))

    req = build_request(lock=True)
    print("[cli] REQUEST ->")
    print(json.dumps(req, indent=2))

    sock.sendto(json.dumps(req).encode("utf-8"), ("127.0.0.1", SERVER_PORT))
    sock.settimeout(5.0)

    data, addr = sock.recvfrom(65535)
    resp = json.loads(data.decode("utf-8"))
    print("\n[cli] RESPONSE from", addr)
    print(json.dumps(resp, indent=2))
    print(f"[cli] matched correlation_id? {resp.get('correlation_id') == req['id']}")

if __name__ == "__main__":
    main()
    
