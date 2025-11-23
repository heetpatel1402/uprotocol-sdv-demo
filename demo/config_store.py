# demo/config_store.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Optional

_CFG_PATH = Path("logs/config.json")


def _load_raw() -> Dict[str, Any]:
    if _CFG_PATH.exists():
        try:
            return json.loads(_CFG_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_raw(cfg: Dict[str, Any]) -> None:
    _CFG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CFG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


# ------- Writers (FR-7, FR-8) -------

def set_rpc_speed_limit(limit_kmh: int) -> None:
    cfg = _load_raw()
    cfg["rpc_speed_limit"] = int(limit_kmh)
    _save_raw(cfg)


def set_geo_context(zone_name: Optional[str], limit_kmh: Optional[int]) -> None:
    cfg = _load_raw()
    cfg["current_zone"] = zone_name
    cfg["geo_speed_limit"] = int(limit_kmh) if limit_kmh is not None else None
    _save_raw(cfg)


# ------- Readers (FR-9) -------

def get_effective_speed_limit(default_threshold: float) -> float:
    """
    Priority:
      1) geofence limit if present
      2) rpc limit if present
      3) fallback to default_threshold
    """
    cfg = _load_raw()

    if cfg.get("geo_speed_limit") is not None:
        return float(cfg["geo_speed_limit"])

    if cfg.get("rpc_speed_limit") is not None:
        return float(cfg["rpc_speed_limit"])

    return float(default_threshold)


def get_config_snapshot() -> Dict[str, Any]:
    cfg = _load_raw()
    cfg.setdefault("rpc_speed_limit", None)
    cfg.setdefault("geo_speed_limit", None)
    cfg.setdefault("current_zone", None)
    return cfg
