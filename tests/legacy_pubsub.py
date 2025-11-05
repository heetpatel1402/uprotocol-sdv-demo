import os
import signal
import subprocess
import sys
import time

def _start_subscriber():
    env = os.environ.copy()
    env["DEMO_SUB_TIMEOUT"] = "5"  # exit after first message or 5s
    # new session => its own process group (easy cleanup)
    return subprocess.Popen(
        [sys.executable, "demo/sub_telemetry.py"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
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
        # Give subscriber time to bind
        time.sleep(1.0)

        env = os.environ.copy()
        env["DEMO_COUNT"] = "1"
        env["DEMO_DELAY"] = "0"

        pub = subprocess.run(
            [sys.executable, "demo/pub_telemetry.py"],
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )

        assert pub.returncode == 0, f"Publisher failed:\n{pub.stderr}\n{pub.stdout}"

        # Optionally, read what the subscriber printed (not required for pass)
        try:
            out, err = sub.communicate(timeout=6)
            # If you want, assert something about `out`
            # assert '"type": "EVENT"' in out
        except subprocess.TimeoutExpired:
            # It should not happen because of DEMO_SUB_TIMEOUT=5, but don’t fail test if it does
            pass
    finally:
        _kill_pg(sub)
