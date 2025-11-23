# demo/driver_behavior.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

try:
    from demo.common import epoch_ms
except ImportError:
    from common import epoch_ms

ALERT_LOG = Path("logs/alerts.jsonl")

# 5-minute window (in ms)
WINDOW_MS = 10000


def _load_recent_alerts_window(now_ms: int) -> list[Dict[str, Any]]:
    """Return all alerts within the last WINDOW_MS milliseconds."""
    if not ALERT_LOG.exists():
        return []

    out: list[Dict[str, Any]] = []
    for line in ALERT_LOG.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            alert = json.loads(line)
        except Exception:
            continue

        ts = alert.get("timestamp_ms")
        if ts is None:
            continue
        try:
            ts = int(ts)
        except Exception:
            continue

        if now_ms - ts <= WINDOW_MS:
            out.append(alert)

    return out


def compute_driver_behavior() -> Dict[str, Any]:
    """
    Compute a simple driver behaviour score based on speed alerts
    from the last 5 minutes.

    Scoring:
      - School zone  -> +3 per alert
      - City zone    -> +2 per alert
      - Highway zone -> +1 per alert
      - Other / no zone -> +1 per alert

    Levels:
      0–3   -> Safe
      4–7   -> Moderate
      8+    -> Risky
    """
    now = epoch_ms()
    recent_alerts = _load_recent_alerts_window(now)

    if not recent_alerts:
        return {
            "score": 0,
            "level": "safe",
            "label": "🟢 Safe",
            "alert_count": 0,
            "window_minutes": 5,
        }

    score = 0
    for alert in recent_alerts:
        zone = (alert.get("zone") or "").lower()
        if "school" in zone:
            score += 3
        elif "city" in zone:
            score += 2
        elif "highway" in zone:
            score += 1
        else:
            score += 1

    if score <= 3:
        level = "safe"
        label = "🟢 Safe"
    elif score <= 7:
        level = "moderate"
        label = "🟡 Moderate"
    else:
        level = "risky"
        label = "🔴 Risky"

    return {
        "score": score,
        "level": level,
        "label": label,
        "alert_count": len(recent_alerts),
        "window_minutes": 5,
    }
