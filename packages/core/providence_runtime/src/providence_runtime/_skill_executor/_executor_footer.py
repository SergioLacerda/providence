"""Footer policy helpers for the skill executor."""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def resolve_footer_policy(project_root: Path | None) -> str:
    root = project_root or Path.cwd()
    state_path = root / ".providence" / "runtime" / "governance-state.json"
    try:
        if state_path.exists():
            payload = json.loads(state_path.read_text(encoding="utf-8"))
            policy = payload.get("response_footer_policy")
            if isinstance(policy, str) and policy.strip():
                return policy.strip().lower()
    except (json.JSONDecodeError, KeyError, AttributeError, OSError) as exc:
        logger.debug("Could not read footer policy from %s: %s", state_path, exc)
    return "always"
