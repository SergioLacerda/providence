"""Read operator-facing state from persisted wizard artifacts."""

from __future__ import annotations

import json
from pathlib import Path

_ENFORCEMENT_LABELS = {
    "silent_mode": "Sem Alertas",
    "warn_mode": "Alertas",
    "strict_mode": "Bloquear",
}


def read_enforcement_label(config_path: Path) -> str:
    """Return the human-readable enforcement label from wizard config."""
    try:
        if not config_path.exists():
            return "Alertas"
        with open(config_path, encoding="utf-8") as handle:
            config = json.load(handle)
    except Exception:  # nosec B110 noqa: BLE001
        return "Alertas"
    return _ENFORCEMENT_LABELS.get(
        config.get("enforcement_mode", "warn_mode"), "Alertas"
    )
