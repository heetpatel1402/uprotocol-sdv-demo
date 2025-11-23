# demo/history_utils.py
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any

ALERT_LOG = Path("logs/alerts.jsonl")


def append_alert(alert: Dict[str, Any]) -> None:
    ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with ALERT_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(alert) + "\n")


def load_recent_alerts(limit: int = 50) -> List[Dict[str, Any]]:
    if not ALERT_LOG.exists():
        return []
    lines = ALERT_LOG.read_text(encoding="utf-8").splitlines()
    lines = lines[-limit:]
    out: List[Dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out
