# FR-2: Spin up RPC server and run the client; ensure response indicates success.
import subprocess, sys, time, os, signal

def test_rpc_lock_smoke():
    srv = subprocess.Popen([sys.executable, "demo/rpc_server.py"],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        time.sleep(0.8)  # allow bind
        out = subprocess.check_output([sys.executable, "demo/rpc_client.py"],
                                      timeout=10, text=True)
        # Client prints the JSON response; success must be true
        assert '"success": true' in out or "'success': True" in out
    finally:
        # best-effort cleanup cross-platform
        try:
            if os.name == "nt":
                srv.terminate()
            else:
                os.killpg(os.getpgid(srv.pid), signal.SIGTERM)
        except Exception:
            pass
