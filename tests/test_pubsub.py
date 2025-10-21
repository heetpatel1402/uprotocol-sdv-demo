# tests/test_pubsub.py
import subprocess
import sys
import time
from pathlib import Path

DEMO = Path(__file__).resolve().parents[1] / "demo"

def run(cmd, **kw):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, **kw)

def test_pubsub_smoke():
    # Start subscriber (background)
    sub = subprocess.Popen(
        [sys.executable, str(DEMO / "sub_telemetry.py")],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    try:
        time.sleep(0.7)  # give it time to bind

        # Run publisher with timeout
        out_pub = run([sys.executable, str(DEMO / "pub_telemetry.py")], timeout=10).stdout

        # Give subscriber a moment to print the event, then terminate it
        time.sleep(0.7)
        sub.terminate()
        try:
            out_sub = sub.communicate(timeout=3)[0]
        except subprocess.TimeoutExpired:
            sub.kill()
            out_sub = sub.communicate()[0]

        # Basic assertions: publisher said it sent, subscriber printed an EVENT
        assert "Published EVENT" in out_pub
        assert '"type": "EVENT"' in out_sub
        assert '"payload"' in out_sub
    finally:
        # Safety net
        if sub.poll() is None:
            sub.kill()
