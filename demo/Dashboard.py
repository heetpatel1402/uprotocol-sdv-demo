# demo/dashboard.py
# Vehicle Status Dashboard (uProtocol) — Streamlit
# Listens for VEHICLE_STATUS_SUMMARY messages on UDP and visualizes them.

import json
import socket
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional, Deque, Dict, Any

import pandas as pd
import streamlit as st

# ----------------------------- Config ---------------------------------
SUMMARY_PORT = 50054   # must match status_summary.py emitter
    # must match status_summary.py emitter
BIND_ADDR    = "127.0.0.1"  # listen on localhost
REFRESH_SEC  = 0.25         # UI refresh cadence
HISTORY_LEN  = 300          # how many points to keep for chart/table default
DEFAULT_SPEED_LIMIT = 100   # km/h (you can change in the sidebar)

# ----------------------------- Receiver --------------------------------

@dataclass
class Summary:
    ts_ms: int
    speed_kmh: Optional[int]
    locked: Optional[bool]

def _safe_int(v) -> Optional[int]:
    try:
        return int(v)
    except Exception:
        return None

class UdpSummaryReceiver:
    """Background UDP listener that collects summaries into a deque."""
    def __init__(self, host: str, port: int, capacity: int = 1000):
        self.host = host
        self.port = port
        self.capacity = capacity
        self._buf: Deque[Summary] = deque(maxlen=capacity)
        self._sock: Optional[socket.socket] = None
        self._thr: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def start(self):
        if self._thr and self._thr.is_alive():
            return
        self._stop.clear()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind((self.host, self.port))
        self._sock.settimeout(0.25)
        self._thr = threading.Thread(target=self._run, name="udp-summary-recv", daemon=True)
        self._thr.start()

    def stop(self):
        self._stop.set()
        if self._thr:
            self._thr.join(timeout=1.0)
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass

    def _run(self):
        while not self._stop.is_set():
            try:
                data, _ = self._sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                msg = json.loads(data.decode("utf-8"))
            except Exception:
                continue

            # Expect schema: { "type": "VEHICLE_STATUS_SUMMARY",
            #                  "speed_kmh": <int|None>, "locked": <bool|None>,
            #                  "last_update": <ms> }
            if not isinstance(msg, dict):
                continue
            if msg.get("type") != "VEHICLE_STATUS_SUMMARY":
                continue

            spd = _safe_int(msg.get("speed_kmh"))
            ts  = _safe_int(msg.get("last_update")) or int(time.time() * 1000)
            locked = msg.get("locked", None)
            self._buf.append(Summary(ts_ms=ts, speed_kmh=spd, locked=locked))

    def snapshot(self, n: int) -> Deque[Summary]:
        """Return up to n most recent summaries (rightmost newest)."""
        if n >= len(self._buf):
            return deque(self._buf, maxlen=self.capacity)
        # copy last n
        out = deque(maxlen=n)
        for item in list(self._buf)[-n:]:
            out.append(item)
        return out

# ----------------------------- Streamlit UI -----------------------------

st.set_page_config(
    page_title="uProtocol Vehicle Dashboard",
    page_icon="🚗",
    layout="wide",
)

st.title("🚗 Vehicle Status Dashboard (uProtocol)")
st.caption(f"Listening for summaries on UDP **{BIND_ADDR}:{SUMMARY_PORT}** …")

# Sidebar controls
st.sidebar.header("Controls")
speed_limit = st.sidebar.number_input("Speed limit (km/h)", min_value=10, max_value=240,
                                      value=DEFAULT_SPEED_LIMIT, step=5)
history_len = st.sidebar.slider("Chart/Table history length", 50, 2000, HISTORY_LEN, step=50)
autoclear = st.sidebar.checkbox("Auto-clear history on idle (10s)", value=False)

# Receiver (one instance per session)
if "receiver" not in st.session_state:
    st.session_state.receiver = UdpSummaryReceiver(BIND_ADDR, SUMMARY_PORT, capacity=5000)
    st.session_state.receiver.start()

receiver: UdpSummaryReceiver = st.session_state.receiver

# Placeholders
kpi_cols = st.columns(3)
speed_box = kpi_cols[0].metric
time_box  = kpi_cols[1].metric
lock_box  = kpi_cols[2].metric

alert_placeholder = st.empty()
chart_placeholder = st.empty()
count_placeholder = st.empty()
table_placeholder = st.empty()

# Data cache for chart/table
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["ts_ms", "speed_kmh", "locked"])

last_update_wall = time.time()

def render_loop():
    global last_update_wall
    # Pull snapshot and build DataFrame view
    items = receiver.snapshot(history_len)
    if len(items) == 0:
        alert_placeholder.info("Waiting for summaries …")
        return

    alert_placeholder.empty()

    # Build/extend DF
    df = pd.DataFrame([{"ts_ms": s.ts_ms, "speed_kmh": s.speed_kmh, "locked": s.locked} for s in items])

    # Update KPIs with latest row
    latest: Dict[str, Any] = df.iloc[-1].to_dict()
    spd = latest.get("speed_kmh")
    ts  = latest.get("ts_ms")
    locked = latest.get("locked")

    speed_text = "—" if pd.isna(spd) or spd is None else int(spd)
    time_text  = "—" if pd.isna(ts) or ts is None else int(ts)
    lock_text  = "Unknown" if pd.isna(locked) else ("Yes" if locked else "No")

    speed_box("Current speed (km/h)", speed_text)
    time_box("Last update (ms)", time_text)
    lock_box("Doors locked", lock_text)

    # Overspeed banner
    if isinstance(spd, (int, float)) and spd is not None and spd > speed_limit:
        st.markdown(
            f"<div style='padding:10px;border-radius:8px;background:#ffe5e5;border:1px solid #ffb3b3;'>"
            f"⚠️ <b>Overspeed alert:</b> {int(spd)} km/h exceeds limit {int(speed_limit)} km/h</div>",
            unsafe_allow_html=True
        )

    # Line chart
    df_plot = df[["ts_ms", "speed_kmh"]].rename(columns={"ts_ms": "timestamp", "speed_kmh": "Speed (km/h)"})
    df_plot = df_plot.set_index("timestamp")
    chart_placeholder.line_chart(df_plot)

    # Count this refresh
    count_placeholder.caption(f"Messages in view: **{len(df)}**  •  Newest ts: **{time_text}**")

    # Raw table
    table_placeholder.dataframe(df.sort_values("ts_ms", ascending=False), use_container_width=True)

    last_update_wall = time.time()

# Main refresh loop (Streamlit reruns the script; use while/stop? We do timer-based)
# Streamlit best practice: single iteration body with st.experimental_rerun via auto refresh.
# We simulate a "live" page by sleeping a little at the end.
render_loop()

# Optional auto-clear if idle
if autoclear and (time.time() - last_update_wall) > 10:
    st.session_state.df = pd.DataFrame(columns=["ts_ms", "speed_kmh", "locked"])
time.sleep(REFRESH_SEC)
# Streamlit ≥ 1.30 uses st.rerun(); older builds used st.experimental_rerun()
try:
    st.rerun()
except AttributeError:
    st.experimental_rerun()
