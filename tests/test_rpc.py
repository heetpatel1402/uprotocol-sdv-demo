"""
RPC smoke test.

Starts the RPC server, runs the client once, and asserts the client exits
cleanly and prints something (a response).
"""

import os
import signal
import subprocess
import sys
import time


def _start_server():
    return subprocess.Popen(
        [sys.executable, "demo/rpc_server.py"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _kill_process_group(proc: subprocess.Popen):
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except Exception:
        pass
    try:
        proc.kill()
    except Exception:
        pass


def test_rpc_roundtrip():
    server = _start_server()
    try:
        time.sleep(1.0)  # let the server bind

        client = subprocess.run(
            [sys.executable, "demo/rpc_client.py"],
            capture_output=True,
            text=True,
            timeout=100,
        )

        # Client should exit cleanly and print some JSON/response text.
        assert client.returncode == 0, f"client failed: {client.stderr}"
        assert client.stdout.strip(), "client printed no output"
    finally:
        _kill_process_group(server)
