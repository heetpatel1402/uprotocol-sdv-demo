# demo/Dashboard.py
from __future__ import annotations

import json
import socket
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional, Deque, Dict, Any

import pandas as pd
import streamlit as st
try:
    from demo.driver_behavior import compute_driver_behavior
except ImportError:
    from driver_behavior import compute_driver_behavior

try:
    from demo.history_utils import load_recent_alerts
except ImportError:
    from history_utils import load_recent_alerts

SUMMARY_PORT = 50054
BIND_ADDR = "127.0.0.1"
REFRESH_SEC = 0.25
HISTORY_LEN = 300
DEFAULT_SPEED_LIMIT = 100  # UI threshold only


@dataclass
class Summary:
    ts_ms: int
    speed_kmh: Optional[int]
    locked: Optional[bool]
    effective_limit: Optional[float] = None
    zone: Optional[str] = None


def _safe_int(v) -> Optional[int]:
    try:
        return int(v)
    except Exception:
        return None


class UdpSummaryReceiver:
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

            if not isinstance(msg, dict):
                continue
            if msg.get("type") != "VEHICLE_STATUS_SUMMARY":
                continue

            spd = _safe_int(msg.get("speed_kmh"))
            ts = _safe_int(msg.get("last_update")) or int(time.time() * 1000)
            locked = msg.get("locked", None)
            eff = msg.get("effective_limit")
            zone = None
            cfg = msg.get("config")
            if isinstance(cfg, dict):
                zone = cfg.get("current_zone")

            self._buf.append(
                Summary(
                    ts_ms=ts,
                    speed_kmh=spd,
                    locked=locked,
                    effective_limit=eff,
                    zone=zone,
                )
            )

    def snapshot(self, n: int) -> Deque[Summary]:
        if n >= len(self._buf):
            return deque(self._buf, maxlen=self.capacity)
        out = deque(maxlen=n)
        for item in list(self._buf)[-n:]:
            out.append(item)
        return out


# ----------------------------- Streamlit UI ----------------------------- #

st.set_page_config(
    page_title="uProtocol Vehicle Dashboard",
    page_icon="🚗",
    layout="wide",
)

st.title("🚗 Vehicle Status Dashboard (uProtocol)")
st.caption(f"Listening for summaries on UDP **{BIND_ADDR}:{SUMMARY_PORT}** …")

st.sidebar.header("Controls")
ui_speed_limit = st.sidebar.number_input(
    "UI speed threshold (km/h)", min_value=10, max_value=240,
    value=DEFAULT_SPEED_LIMIT, step=5
)
history_len = st.sidebar.slider("Chart/Table history length", 50, 2000, HISTORY_LEN, step=50)
autoclear = st.sidebar.checkbox("Auto-clear history on idle (10s)", value=False)

if "receiver" not in st.session_state:
    st.session_state.receiver = UdpSummaryReceiver(BIND_ADDR, SUMMARY_PORT, capacity=5000)
    st.session_state.receiver.start()

receiver: UdpSummaryReceiver = st.session_state.receiver

# 5 KPI boxes now (add Driver Behaviour)
kpi_cols = st.columns(5)
speed_box = kpi_cols[0].metric
time_box = kpi_cols[1].metric
lock_box = kpi_cols[2].metric
limit_box = kpi_cols[3].metric
behavior_box = kpi_cols[4].metric


alert_placeholder = st.empty()
chart_placeholder = st.empty()
count_placeholder = st.empty()
table_placeholder = st.empty()
alerts_table_placeholder = st.empty()

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(
        columns=["ts_ms", "speed_kmh", "locked", "effective_limit", "zone"]
    )

last_update_wall = time.time()


def render_loop():
    global last_update_wall
    items = receiver.snapshot(history_len)
    if len(items) == 0:
        alert_placeholder.info("Waiting for summaries …")
        return

    alert_placeholder.empty()

    df = pd.DataFrame(
        [
            {
                "ts_ms": s.ts_ms,
                "speed_kmh": s.speed_kmh,
                "locked": s.locked,
                "effective_limit": s.effective_limit,
                "zone": s.zone,
            }
            for s in items
        ]
    )

    latest: Dict[str, Any] = df.iloc[-1].to_dict()
    spd = latest.get("speed_kmh")
    ts = latest.get("ts_ms")
    locked = latest.get("locked")
    eff_limit = latest.get("effective_limit")
    zone = latest.get("zone")

    speed_text = "—" if pd.isna(spd) or spd is None else int(spd)
    time_text = "—" if pd.isna(ts) or ts is None else int(ts)
    lock_text = "Unknown" if pd.isna(locked) else ("Yes" if locked else "No")
    limit_text = "—" if eff_limit is None or pd.isna(eff_limit) else int(eff_limit)

    speed_box("Current speed (km/h)", speed_text)
    time_box("Last update (ms)", time_text)
    lock_box("Doors locked", lock_text)
    limit_box("Effective speed limit (km/h)", limit_text)
        # ---- Driver Behaviour KPI (last 5 minutes of alerts) ----
    behavior = compute_driver_behavior()
    behavior_box(
        "Driver behaviour (last 5 min)",
        behavior["label"],
        help=f"Score: {behavior['score']} • Alerts: {behavior['alert_count']} in last {behavior['window_minutes']} min",
    )


    threshold = eff_limit if isinstance(eff_limit, (int, float)) else ui_speed_limit
    if isinstance(spd, (int, float)) and threshold is not None and spd > threshold:
        st.markdown(
            f"<div style='padding:10px;border-radius:8px;background:#ffe5e5;border:1px solid #ffb3b3;'>"
            f"⚠️ <b>Overspeed alert:</b> {int(spd)} km/h exceeds limit {int(threshold)} km/h"
            + (f" (zone: {zone})" if zone else "")
            + "</div>",
            unsafe_allow_html=True,
        )

    df_plot = df[["ts_ms", "speed_kmh"]].rename(
        columns={"ts_ms": "timestamp", "speed_kmh": "Speed (km/h)"}
    )
    df_plot = df_plot.set_index("timestamp")
    chart_placeholder.line_chart(df_plot)

    count_placeholder.caption(
        f"Messages in view: **{len(df)}** • Newest ts: **{time_text}**"
        + (f" • Zone: **{zone}**" if zone else "")
    )

    table_placeholder.dataframe(df.sort_values("ts_ms", ascending=False), use_container_width=True)

    recent_alerts = load_recent_alerts(limit=50)
    if recent_alerts:
        alerts_df = pd.DataFrame(recent_alerts)
        alerts_table_placeholder.expander("Recent SPEED_ALERT events").dataframe(
            alerts_df.sort_values("timestamp_ms", ascending=False),
            use_container_width=True,
        )

    last_update_wall = time.time()


render_loop()

if autoclear and (time.time() - last_update_wall) > 10:
    st.session_state.df = pd.DataFrame(
        columns=["ts_ms", "speed_kmh", "locked", "effective_limit", "zone"]
    )

time.sleep(REFRESH_SEC)
try:
    st.rerun()
except AttributeError:
    st.experimental_rerun()
# from __future__ import annotations

# import json
# import socket
# import threading
# import time
# from collections import deque
# from dataclasses import dataclass
# from typing import Optional, Deque, Dict, Any

# import pandas as pd
# import streamlit as st

# try:
#     from demo.history_utils import load_recent_alerts
# except ImportError:
#     from history_utils import load_recent_alerts  # if placed at project root

# SUMMARY_PORT = 50054
# BIND_ADDR = "127.0.0.1"
# REFRESH_SEC = 0.25
# HISTORY_LEN = 300
# DEFAULT_SPEED_LIMIT = 100  # UI slider only (visual threshold)


# @dataclass
# class Summary:
#     ts_ms: int
#     speed_kmh: Optional[int]
#     locked: Optional[bool]
#     effective_limit: Optional[float] = None
#     zone: Optional[str] = None


# def _safe_int(v) -> Optional[int]:
#     try:
#         return int(v)
#     except Exception:
#         return None


# class UdpSummaryReceiver:
#     """Background UDP listener that collects summaries into a deque."""

#     def __init__(self, host: str, port: int, capacity: int = 1000):
#         self.host = host
#         self.port = port
#         self.capacity = capacity
#         self._buf: Deque[Summary] = deque(maxlen=capacity)
#         self._sock: Optional[socket.socket] = None
#         self._thr: Optional[threading.Thread] = None
#         self._stop = threading.Event()

#     def start(self):
#         if self._thr and self._thr.is_alive():
#             return
#         self._stop.clear()
#         self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#         self._sock.bind((self.host, self.port))
#         self._sock.settimeout(0.25)
#         self._thr = threading.Thread(target=self._run, name="udp-summary-recv", daemon=True)
#         self._thr.start()

#     def stop(self):
#         self._stop.set()
#         if self._thr:
#             self._thr.join(timeout=1.0)
#         if self._sock:
#             try:
#                 self._sock.close()
#             except Exception:
#                 pass

#     def _run(self):
#         while not self._stop.is_set():
#             try:
#                 data, _ = self._sock.recvfrom(65535)
#             except socket.timeout:
#                 continue
#             except OSError:
#                 break
#             try:
#                 msg = json.loads(data.decode("utf-8"))
#             except Exception:
#                 continue

#             if not isinstance(msg, dict):
#                 continue
#             if msg.get("type") != "VEHICLE_STATUS_SUMMARY":
#                 continue

#             spd = _safe_int(msg.get("speed_kmh"))
#             ts = _safe_int(msg.get("last_update")) or int(time.time() * 1000)
#             locked = msg.get("locked", None)
#             eff = msg.get("effective_limit")
#             zone = None
#             cfg = msg.get("config")
#             if isinstance(cfg, dict):
#                 zone = cfg.get("current_zone")

#             self._buf.append(
#                 Summary(
#                     ts_ms=ts,
#                     speed_kmh=spd,
#                     locked=locked,
#                     effective_limit=eff,
#                     zone=zone,
#                 )
#             )

#     def snapshot(self, n: int) -> Deque[Summary]:
#         if n >= len(self._buf):
#             return deque(self._buf, maxlen=self.capacity)
#         out = deque(maxlen=n)
#         for item in list(self._buf)[-n:]:
#             out.append(item)
#         return out


# # ----------------------------- Streamlit UI ----------------------------- #

# st.set_page_config(
#     page_title="uProtocol Vehicle Dashboard",
#     page_icon="🚗",
#     layout="wide",
# )

# st.title("🚗 Vehicle Status Dashboard (uProtocol)")
# st.caption(f"Listening for summaries on UDP **{BIND_ADDR}:{SUMMARY_PORT}** …")

# st.sidebar.header("Controls")
# ui_speed_limit = st.sidebar.number_input(
#     "UI speed threshold (km/h)", min_value=10, max_value=240,
#     value=DEFAULT_SPEED_LIMIT, step=5
# )
# history_len = st.sidebar.slider("Chart/Table history length", 50, 2000, HISTORY_LEN, step=50)
# autoclear = st.sidebar.checkbox("Auto-clear history on idle (10s)", value=False)

# if "receiver" not in st.session_state:
#     st.session_state.receiver = UdpSummaryReceiver(BIND_ADDR, SUMMARY_PORT, capacity=5000)
#     st.session_state.receiver.start()

# receiver: UdpSummaryReceiver = st.session_state.receiver

# kpi_cols = st.columns(4)
# speed_box = kpi_cols[0].metric
# time_box = kpi_cols[1].metric
# lock_box = kpi_cols[2].metric
# limit_box = kpi_cols[3].metric

# alert_placeholder = st.empty()
# chart_placeholder = st.empty()
# count_placeholder = st.empty()
# table_placeholder = st.empty()
# alerts_table_placeholder = st.empty()

# if "df" not in st.session_state:
#     st.session_state.df = pd.DataFrame(columns=["ts_ms", "speed_kmh", "locked", "effective_limit", "zone"])

# last_update_wall = time.time()


# def render_loop():
#     global last_update_wall
#     items = receiver.snapshot(history_len)
#     if len(items) == 0:
#         alert_placeholder.info("Waiting for summaries …")
#         return

#     alert_placeholder.empty()

#     df = pd.DataFrame(
#         [
#             {
#                 "ts_ms": s.ts_ms,
#                 "speed_kmh": s.speed_kmh,
#                 "locked": s.locked,
#                 "effective_limit": s.effective_limit,
#                 "zone": s.zone,
#             }
#             for s in items
#         ]
#     )

#     latest: Dict[str, Any] = df.iloc[-1].to_dict()
#     spd = latest.get("speed_kmh")
#     ts = latest.get("ts_ms")
#     locked = latest.get("locked")
#     eff_limit = latest.get("effective_limit")
#     zone = latest.get("zone")

#     speed_text = "—" if pd.isna(spd) or spd is None else int(spd)
#     time_text = "—" if pd.isna(ts) or ts is None else int(ts)
#     lock_text = "Unknown" if pd.isna(locked) else ("Yes" if locked else "No")
#     limit_text = "—" if eff_limit is None or pd.isna(eff_limit) else int(eff_limit)

#     speed_box("Current speed (km/h)", speed_text)
#     time_box("Last update (ms)", time_text)
#     lock_box("Doors locked", lock_text)
#     limit_box("Effective speed limit (km/h)", limit_text)

#     # Overspeed banner based on effective limit if known, else UI slider
#     threshold = eff_limit if isinstance(eff_limit, (int, float)) else ui_speed_limit
#     if isinstance(spd, (int, float)) and threshold is not None and spd > threshold:
#         st.markdown(
#             f"<div style='padding:10px;border-radius:8px;background:#ffe5e5;border:1px solid #ffb3b3;'>"
#             f"⚠️ <b>Overspeed alert:</b> {int(spd)} km/h exceeds limit {int(threshold)} km/h"
#             + (f" (zone: {zone})" if zone else "")
#             + "</div>",
#             unsafe_allow_html=True,
#         )

#     df_plot = df[["ts_ms", "speed_kmh"]].rename(columns={"ts_ms": "timestamp", "speed_kmh": "Speed (km/h)"})
#     df_plot = df_plot.set_index("timestamp")
#     chart_placeholder.line_chart(df_plot)

#     count_placeholder.caption(
#         f"Messages in view: **{len(df)}** • Newest ts: **{time_text}**"
#         + (f" • Zone: **{zone}**" if zone else "")
#     )

#     table_placeholder.dataframe(df.sort_values("ts_ms", ascending=False), use_container_width=True)

#     # Recent alerts from file (if any)
#     recent_alerts = load_recent_alerts(limit=50)
#     if recent_alerts:
#         alerts_df = pd.DataFrame(recent_alerts)
#         alerts_table_placeholder.expander("Recent SPEED_ALERT events").dataframe(
#             alerts_df.sort_values("timestamp_ms", ascending=False),
#             use_container_width=True,
#         )

#     last_update_wall = time.time()


# render_loop()

# if autoclear and (time.time() - last_update_wall) > 10:
#     st.session_state.df = pd.DataFrame(columns=["ts_ms", "speed_kmh", "locked", "effective_limit", "zone"])

# time.sleep(REFRESH_SEC)
# try:
#     st.rerun()
# except AttributeError:
#     st.experimental_rerun()
# # # # demo/dashboard.py
# # # Vehicle Status Dashboard (uProtocol) — Streamlit
# # # Listens for VEHICLE_STATUS_SUMMARY messages on UDP and visualizes them.

# # import json
# # import socket
# # import threading
# # import time
# # from collections import deque
# # from dataclasses import dataclass
# # from typing import Optional, Deque, Dict, Any

# # import pandas as pd
# # import streamlit as st

# # from history_utils import load_recent_alerts

# # # ----------------------------- Config ---------------------------------
# # SUMMARY_PORT = 50054        # must match status_summary.py emitter
# # BIND_ADDR = "127.0.0.1"     # listen on localhost
# # REFRESH_SEC = 0.25          # UI refresh cadence
# # HISTORY_LEN = 300           # how many points to keep for chart/table default
# # DEFAULT_SPEED_LIMIT = 100   # sidebar local limit (separate from effective limit)

# # # ----------------------------- Receiver --------------------------------


# # @dataclass
# # class Summary:
# #     ts_ms: int
# #     speed_kmh: Optional[int]
# #     locked: Optional[bool]
# #     effective_limit: Optional[int]
# #     current_zone: Optional[str]


# # def _safe_int(v) -> Optional[int]:
# #     try:
# #         return int(v)
# #     except Exception:
# #         return None


# # class UdpSummaryReceiver:
# #     """Background UDP listener that collects summaries into a deque."""

# #     def __init__(self, host: str, port: int, capacity: int = 1000):
# #         self.host = host
# #         self.port = port
# #         self.capacity = capacity
# #         self._buf: Deque[Summary] = deque(maxlen=capacity)
# #         self._sock: Optional[socket.socket] = None
# #         self._thr: Optional[threading.Thread] = None
# #         self._stop = threading.Event()

# #     def start(self):
# #         if self._thr and self._thr.is_alive():
# #             return
# #         self._stop.clear()
# #         self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# #         self._sock.bind((self.host, self.port))
# #         self._sock.settimeout(0.25)
# #         self._thr = threading.Thread(
# #             target=self._run, name="udp-summary-recv", daemon=True
# #         )
# #         self._thr.start()

# #     def stop(self):
# #         self._stop.set()
# #         if self._thr:
# #             self._thr.join(timeout=1.0)
# #         if self._sock:
# #             try:
# #                 self._sock.close()
# #             except Exception:
# #                 pass

# #     def _run(self):
# #         while not self._stop.is_set():
# #             try:
# #                 data, _ = self._sock.recvfrom(65535)
# #             except socket.timeout:
# #                 continue
# #             except OSError:
# #                 break
# #             try:
# #                 msg = json.loads(data.decode("utf-8"))
# #             except Exception:
# #                 continue

# #             if not isinstance(msg, dict):
# #                 continue
# #             if msg.get("type") != "VEHICLE_STATUS_SUMMARY":
# #                 continue

# #             spd = _safe_int(msg.get("speed_kmh"))
# #             ts = _safe_int(msg.get("last_update")) or int(time.time() * 1000)
# #             locked = msg.get("locked", None)
# #             eff_lim = _safe_int(msg.get("effective_limit"))
# #             zone = msg.get("current_zone")

# #             self._buf.append(
# #                 Summary(
# #                     ts_ms=ts,
# #                     speed_kmh=spd,
# #                     locked=locked,
# #                     effective_limit=eff_lim,
# #                     current_zone=zone,
# #                 )
# #             )

# #     def snapshot(self, n: int) -> Deque[Summary]:
# #         """Return up to n most recent summaries (rightmost newest)."""
# #         if n >= len(self._buf):
# #             return deque(self._buf, maxlen=self.capacity)
# #         out = deque(maxlen=n)
# #         for item in list(self._buf)[-n:]:
# #             out.append(item)
# #         return out


# # # ----------------------------- Streamlit UI -----------------------------

# # st.set_page_config(
# #     page_title="uProtocol Vehicle Dashboard",
# #     page_icon="🚗",
# #     layout="wide",
# # )

# # st.title("🚗 Vehicle Status Dashboard (uProtocol)")
# # st.caption(f"Listening for summaries on UDP **{BIND_ADDR}:{SUMMARY_PORT}** …")

# # # Sidebar controls
# # st.sidebar.header("Controls")
# # speed_limit = st.sidebar.number_input(
# #     "Local overspeed check (km/h)",
# #     min_value=10,
# #     max_value=240,
# #     value=DEFAULT_SPEED_LIMIT,
# #     step=5,
# # )
# # history_len = st.sidebar.slider(
# #     "Chart/Table history length", 50, 2000, HISTORY_LEN, step=50
# # )
# # autoclear = st.sidebar.checkbox("Auto-clear history on idle (10s)", value=False)

# # # Receiver (one instance per session)
# # if "receiver" not in st.session_state:
# #     st.session_state.receiver = UdpSummaryReceiver(
# #         BIND_ADDR, SUMMARY_PORT, capacity=5000
# #     )
# #     st.session_state.receiver.start()

# # receiver: UdpSummaryReceiver = st.session_state.receiver

# # # Placeholders
# # kpi_cols = st.columns(4)
# # speed_box = kpi_cols[0].metric
# # time_box = kpi_cols[1].metric
# # lock_box = kpi_cols[2].metric
# # limit_box = kpi_cols[3].metric

# # alert_placeholder = st.empty()
# # chart_placeholder = st.empty()
# # count_placeholder = st.empty()
# # table_placeholder = st.empty()

# # # Data cache for chart/table
# # if "df" not in st.session_state:
# #     st.session_state.df = pd.DataFrame(
# #         columns=["ts_ms", "speed_kmh", "locked", "effective_limit", "current_zone"]
# #     )

# # last_update_wall = time.time()


# # def render_loop():
# #     global last_update_wall
# #     items = receiver.snapshot(history_len)
# #     if len(items) == 0:
# #         alert_placeholder.info("Waiting for summaries …")
# #         return

# #     alert_placeholder.empty()

# #     df = pd.DataFrame(
# #         [
# #             {
# #                 "ts_ms": s.ts_ms,
# #                 "speed_kmh": s.speed_kmh,
# #                 "locked": s.locked,
# #                 "effective_limit": s.effective_limit,
# #                 "current_zone": s.current_zone,
# #             }
# #             for s in items
# #         ]
# #     )

# #     latest: Dict[str, Any] = df.iloc[-1].to_dict()
# #     spd = latest.get("speed_kmh")
# #     ts = latest.get("ts_ms")
# #     locked = latest.get("locked")
# #     eff_lim = latest.get("effective_limit")
# #     zone = latest.get("current_zone")

# #     speed_text = "—" if pd.isna(spd) or spd is None else int(spd)
# #     time_text = "—" if pd.isna(ts) or ts is None else int(ts)
# #     lock_text = "Unknown" if pd.isna(locked) else ("Yes" if locked else "No")
# #     limit_text = "—" if pd.isna(eff_lim) or eff_lim is None else int(eff_lim)

# #     speed_box("Current speed (km/h)", speed_text)
# #     time_box("Last update (ms)", time_text)
# #     lock_box("Doors locked", lock_text)
# #     limit_box("Effective speed limit (km/h)", limit_text)

# #     if zone:
# #         st.caption(f"Current geofence zone: **{zone}**")

# #     # Local overspeed banner (using sidebar limit)
# #     if isinstance(spd, (int, float)) and spd is not None and spd > speed_limit:
# #         st.markdown(
# #             f"<div style='padding:10px;border-radius:8px;background:#ffe5e5;"
# #             f"border:1px solid #ffb3b3;'>"
# #             f"⚠️ <b>Overspeed alert (UI):</b> {int(spd)} km/h exceeds "
# #             f"local limit {int(speed_limit)} km/h</div>",
# #             unsafe_allow_html=True,
# #         )

# #     # Line chart over time
# #     df_plot = df[["ts_ms", "speed_kmh"]].rename(
# #         columns={"ts_ms": "timestamp", "speed_kmh": "Speed (km/h)"}
# #     )
# #     df_plot = df_plot.set_index("timestamp")
# #     chart_placeholder.line_chart(df_plot)

# #     # Count + newest ts
# #     count_placeholder.caption(
# #         f"Messages in view: **{len(df)}**  •  Newest ts: **{time_text}**"
# #     )

# #     # Summary table
# #     table_placeholder.dataframe(
# #         df.sort_values("ts_ms", ascending=False), use_container_width=True
# #     )

# #     # Alert history section (FR-9)
# #     st.subheader("Recent Speed Alerts")
# #     alerts = load_recent_alerts(max_rows=200)
# #     if alerts:
# #         df_alerts = pd.DataFrame(alerts)
# #         st.dataframe(df_alerts, use_container_width=True)
# #         st.download_button(
# #             label="Download alerts as CSV",
# #             data=df_alerts.to_csv(index=False).encode("utf-8"),
# #             file_name="alerts.csv",
# #             mime="text/csv",
# #         )
# #     else:
# #         st.info("No alerts logged yet.")

# #     last_update_wall = time.time()


# # # One render per run; Streamlit reruns script often
# # render_loop()

# # # Optional auto-clear if idle
# # if autoclear and (time.time() - last_update_wall) > 10:
# #     st.session_state.df = pd.DataFrame(
# #         columns=["ts_ms", "speed_kmh", "locked", "effective_limit", "current_zone"]
# #     )

# # time.sleep(REFRESH_SEC)
# # try:
# #     st.rerun()
# # except AttributeError:
# #     st.experimental_rerun()
