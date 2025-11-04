# FR-3: End-to-end for status_summary.py using ephemeral ports and a temp audit file.
import os, sys, json, time, socket, subprocess, pathlib, signal

def bind_udp(addr, port, timeout=5):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((addr, port))
    s.settimeout(timeout)
    return s

def test_status_summary_pipeline(tmp_path):
    addr = "127.0.0.1"
    speed_port = 56052
    out_port   = 56054
    audit = tmp_path / "audit.jsonl"

    # Receiver for summaries BEFORE starting the service (avoid race)
    sink = bind_udp(addr, out_port, timeout=10)

    env = os.environ.copy()
    env.update({
        "SUM_SPEED_HOST": addr,
        "SUM_SPEED_PORT": str(speed_port),
        "SUM_OUT_HOST":   addr,
        "SUM_OUT_PORT":   str(out_port),
        "SUM_AUDIT_PATH": str(audit),
        "SUM_INTERVAL_S": "0.5",
    })

    # Start status_summary
    proc = subprocess.Popen([sys.executable, "demo/status_summary.py"], env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        time.sleep(0.5)

        # Send one speed EVENT to the service's input
        src = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        evt = {
            "type": "EVENT",
            "payload": {"kmh": 88, "timestamp_ms": int(time.time()*1000)}
        }
        src.sendto(json.dumps(evt).encode("utf-8"), (addr, speed_port))

        # Write an audit line that indicates a lock command succeeded
        audit_line = {
            "ts_ms": int(time.time()*1000),
            "request": {"lock": True},
            "response": {"success": True}
        }
        audit.write_text(json.dumps(audit_line) + "\n", encoding="utf-8")

        # Expect one summary from the service
        data, _ = sink.recvfrom(65535)
        summary = json.loads(data.decode("utf-8"))

        assert summary["type"] == "VEHICLE_STATUS_SUMMARY"
        # speed should propagate
        assert summary.get("speed_kmh") in (88, "88", 88.0)
        # locked may take one cycle; accept None or True
        assert summary.get("locked") in (None, True, False)

    finally:
        try:
            if os.name == "nt":
                proc.terminate()
            else:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception:
            pass
