# tests/test_rpc.py
import subprocess
import sys
import time
from pathlib import Path

DEMO = Path(__file__).resolve().parents[1] / "demo"

def run(cmd, **kw):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, **kw)

def test_rpc_smoke():
    # Start server
    svc = subprocess.Popen(
        [sys.executable, str(DEMO / "rpc_server.py")],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    try:
        time.sleep(0.7)  # allow bind

        # Run client with timeout
        out_cli = run([sys.executable, str(DEMO / "rpc_client.py")], timeout=10).stdout

        # Stop server and collect logs
        svc.terminate()
        try:
            out_svc = svc.communicate(timeout=3)[0]
        except subprocess.TimeoutExpired:
            svc.kill()
            out_svc = svc.communicate()[0]

        # Basic assertions: client received a RESPONSE with status OK
        assert '"type": "RESPONSE"' in out_cli
        assert '"code": "OK"' in out_cli
        # The server should have received a REQUEST
        assert '"type": "REQUEST"' in out_svc
    finally:
        if svc.poll() is None:
            svc.kill()
