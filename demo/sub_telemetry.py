#!/usr/bin/env python3
import json
import os
import socket
import sys
import time

HOST = os.getenv("DEMO_BIND_HOST", "127.0.0.1")
PORT = int(os.getenv("DEMO_BIND_PORT", "50052"))
# If DEMO_SUB_TIMEOUT > 0, the script will wait up to that many seconds
# for a single message and then exit (good for CI).
SUB_TIMEOUT = float(os.getenv("DEMO_SUB_TIMEOUT", "0"))  # 0 = run forever

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Make binds more reliable on CI
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, PORT))

    if SUB_TIMEOUT > 0:
        # CI mode: receive one packet or time out, then exit
        sock.settimeout(SUB_TIMEOUT)
        try:
            data, addr = sock.recvfrom(65535)
            msg = json.loads(data.decode("utf-8"))
            # print to make debugging easier in logs
            print("[svc] got:", json.dumps(msg), file=sys.stdout, flush=True)
        except socket.timeout:
            print("[svc] no message within timeout", file=sys.stdout, flush=True)
        finally:
            sock.close()
        return

    # Local/dev mode: print every packet forever
    print(f"[svc] BodyControl listening on udp://{HOST}:{PORT}", flush=True)
    try:
        while True:
            data, addr = sock.recvfrom(65535)
            try:
                msg = json.loads(data.decode("utf-8"))
            except Exception:
                msg = {"raw": data.decode("utf-8", errors="replace")}
            print("[svc] EVENT:", json.dumps(msg, indent=2), flush=True)
    finally:
        sock.close()

if __name__ == "__main__":
    main()
