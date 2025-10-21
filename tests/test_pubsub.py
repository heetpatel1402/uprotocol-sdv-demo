"""
Pub/Sub smoke test that is deterministic in CI.
- Starts the subscriber
- Runs the publisher once (one-shot) and verifies it exits cleanly
"""

import os
import signal
import subprocess
import sys
import time


def _start_subscriber():
    # run in its own process group so we can kill reliably on CI
    return subprocess.Popen(
        [sys.executable, "demo/sub_telemetry.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _kill_pg(proc: subprocess.Popen):
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except Exception:
        pass
    try:
        proc.kill()
    except Exception:
        pass


def test_pubsub_runs():
    sub = _start_subscriber()
    try:
        # Give subscriber time to bind the UDP socket
        time.sleep(2.0)

        env = os.environ.copy()
        env["DEMO_COUNT"] = "1"
        env["DEMO_DELAY"] = "0"

        # Run the publisher in one-shot mode
        pub = subprocess.run(
            [sys.executable, "demo/pub_telemetry.py"],
            env=env,
            capture_output=True,
            text=True,
            timeout=20,     # should be more than enough now
        )

        assert pub.returncode == 0, f"Publisher failed:\nSTDERR:\n{pub.stderr}\nSTDOUT:\n{pub.stdout}"
    finally:
        _kill_pg(sub)
