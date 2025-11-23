# demo/sub_telemetry.py
import socket, json

PORT = 50051  # where we listen

def main():
    print(f"[sub] listening on udp://127.0.0.1:{PORT}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("127.0.0.1", PORT))

    while True:
        data, addr = sock.recvfrom(65535)
        try:
            msg = json.loads(data.decode("utf-8"))
        except Exception:
            print("[sub] received non-JSON bytes")
            continue

        print("\n[sub] EVENT received from", addr)
        print(json.dumps(msg, indent=2))

if __name__ == "__main__":
    main()
    
