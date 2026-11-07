"""Load surveillance detection settings from config/config.yaml.

The Spark pipeline and other components can import these helpers to avoid
hardcoding thresholds. Environment variables (when present) override YAML for
easy runtime tuning.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - optional dep in minimal envs
    yaml = None

DEFAULTS: dict[str, Any] = {
    "window_duration_seconds": 10,
    "window_slide_seconds": 5,
    "watermark_seconds": 2,
    "rules": {
        "spoofing": {
            "enabled": True,
            "min_order_to_trade_ratio": 5.0,
            "min_cancellation_rate": 0.80,
            "max_execution_horizon_ms": 2000.0,
            "severity": "HIGH",
            "alert_type": "SPOOFING",
        },
        "layering": {"enabled": False, "depth_threshold": 5},
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_detection_config(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    if path is None:
        path = Path(__file__).resolve().with_name("config.yaml")
    cfg = dict(DEFAULTS)
    p = Path(path)
    if yaml and p.exists():
        with p.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        det = data.get("detection") or {}
        if isinstance(det, dict):
            cfg = _deep_merge(cfg, det)

    # Env overrides for quick tuning (no file edit/rebuild)
    sp = cfg.setdefault("rules", {}).setdefault("spoofing", {})
    def _f(name: str, cast):
        v = os.getenv(name)
        if v is not None and v != "":
            try:
                sp_key = {
                    "DETECTION_OTR_MIN": "min_order_to_trade_ratio",
                    "DETECTION_CANCEL_RATE_MIN": "min_cancellation_rate",
                    "DETECTION_EXEC_HORIZON_MAX_MS": "max_execution_horizon_ms",
                }.get(name)
                if sp_key:
                    sp[sp_key] = cast(v)
            except Exception:
                pass
    _f("DETECTION_OTR_MIN", float)
    _f("DETECTION_CANCEL_RATE_MIN", float)
    _f("DETECTION_EXEC_HORIZON_MAX_MS", float)
    return cfg


def spoofing_rule(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    return (load_detection_config(path).get("rules") or {}).get("spoofing") or DEFAULTS["rules"]["spoofing"]
