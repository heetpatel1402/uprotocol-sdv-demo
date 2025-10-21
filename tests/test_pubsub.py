"""
Pub/Sub smoke test.

Starts the subscriber, runs the publisher once, and ensures the publisher
exited cleanly. We keep it lightweight so it runs reliably in CI.
"""

import os
import signal
import subprocess
import sys
import time


def _start_subscriber():
    # Start demo/sub_telemetry.py in its own process group so we can cleanly kill it.
    # stdout/stderr to DEVNULL to avoid pipe blocking.
    return subprocess.Popen(
        [sys.executable, "demo/sub_telemetry.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,  # new process group
    )


def _kill_process_group(proc: subprocess.Popen):
    try:
        # Send SIGTERM to the whole group (works on Linux CI)
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
        # Give the subscriber time to bind its UDP socket.
        time.sleep(1.0)

        # Run publisher with a strict timeout so CI can’t hang.
        pub = subprocess.run(
            [sys.executable, "demo/pub_telemetry.py"],
            capture_output=True,
            text=True,
            timeout=100,
        )

        # Publisher should exit cleanly.
        assert pub.returncode == 0, f"publisher failed: {pub.stderr}"
    finally:
        _kill_process_group(sub)
