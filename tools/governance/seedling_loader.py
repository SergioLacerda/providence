#!/usr/bin/env python3
"""
Providence Seedlings Framework - Auto-activation of Governance

A seedling is a lightweight trigger that automatically activates governance
when a project is loaded, without requiring manual commands.

Usage:
    from tools.governance.seedling_loader import SeedlingLoader

    loader = SeedlingLoader(project_root)
    seeds = loader.load_all()
    for seed in seeds:
        if seed.get("auto_activate"):
            loader.execute_seed(seed)

Seedlings location: .providence/seedlings/*.seed.json
Each seedling defines:
- auto_activate: bool
- required_context: list of required files/dirs
- on_load: trigger action ("activate_governance", etc)
- triggers: list of trigger conditions
"""

import json
import logging
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _resolve_seedlings_dir(project_root: Path) -> Path:
    """Resolve canonical seedlings directory under .providence."""
    return Path(project_root) / ".providence" / "seedlings"


class SeedlingLoader:
    """Load and execute Providence seedlings (auto-activation triggers)"""

    def __init__(self, project_root: Path):
        """Initialize seedling loader

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
        self.seedlings_dir = _resolve_seedlings_dir(self.project_root)

    def load_all(self) -> list[dict[str, Any]]:
        """Load all seedling files from seedlings directory

        Returns:
            List of parsed seedling dictionaries
        """
        if not self.seedlings_dir.exists():
            warnings.warn(
                f"Seedlings directory not found: {self.seedlings_dir} — "
                f"governance activation defaults may apply",
                RuntimeWarning,
                stacklevel=2,
            )
            return []

        seedlings = []
        try:
            for seed_file in self.seedlings_dir.glob("*.seed.json"):
                try:
                    with open(seed_file, encoding="utf-8", errors="strict") as f:
                        seed = json.load(f)
                        # Validate basic structure
                        if self._validate_seedling(seed):
                            seedlings.append(seed)
                except (OSError, json.JSONDecodeError):
                    # Skip malformed seedlings silently
                    continue
        except Exception:
            logger.debug("Failed while loading seedlings", exc_info=True)

        return seedlings

    def load_by_trigger(self, trigger: str) -> list[dict[str, Any]]:
        """Load seedlings that match a specific trigger condition

        Args:
            trigger: Trigger name (e.g., "on_project_load")

        Returns:
            List of matching seedlings
        """
        all_seedlings = self.load_all()
        return [s for s in all_seedlings if trigger in s.get("triggers", [])]

    def _validate_seedling(self, seed: dict[str, Any]) -> bool:
        """Validate seedling structure

        Required fields:
        - auto_activate: bool
        - required_context: list
        - on_load: str
        - triggers: list
        """
        required = {"auto_activate", "required_context", "on_load", "triggers"}
        return required.issubset(seed.keys())

    def _check_required_context(self, seed: dict[str, Any]) -> bool:
        """Check if all required context files/dirs exist

        Args:
            seed: Seedling dictionary

        Returns:
            True if all required context exists
        """
        required = seed.get("required_context", [])
        for context_path in required:
            full_path = self.project_root / context_path
            if not full_path.exists():
                return False
        return True

    def execute_seed(self, seed: dict[str, Any]) -> bool:
        """Execute a seedling's on_load action

        Currently supports:
        - "activate_governance": Initializes governance activation

        Args:
            seed: Seedling dictionary

        Returns:
            True if execution successful
        """
        action = seed.get("on_load")
        # Overlay must run even in degraded mode (for example missing .providence registries).
        if action != "prepare_personal_overlay" and not self._check_required_context(
            seed
        ):
            return False

        if action == "activate_governance":
            return self._activate_governance()
        if action == "prepare_personal_overlay":
            return self._prepare_personal_overlay()

        # Unknown action
        return False

    def _prepare_personal_overlay(self) -> bool:
        """Build dynamic personal+governed capability overlay state."""
        try:
            from tools.governance.personal_overlay import resolve_personal_overlay

            runtime_dir = self.project_root / ".providence" / "runtime"
            runtime_dir.mkdir(parents=True, exist_ok=True)

            overlay = resolve_personal_overlay(project_root=self.project_root)
            overlay_path = runtime_dir / "personal-overlay-state.json"
            with open(overlay_path, "w", encoding="utf-8", errors="strict") as f:
                json.dump(overlay, f, indent=2, ensure_ascii=False)

            drifts = overlay.get("drift_events", [])
            if isinstance(drifts, list) and drifts:
                compliance_log = runtime_dir / "compliance-events.jsonl"
                with open(compliance_log, "a", encoding="utf-8", errors="strict") as f:
                    for drift in drifts:
                        event = {
                            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                            "event": "personal_overlay_drift",
                            "severity": "warn",
                            "details": drift,
                        }
                        f.write(json.dumps(event, ensure_ascii=False) + "\n")
            return True
        except Exception:
            return False

    def _activate_governance(self) -> bool:
        """Activate governance protocol

        Returns:
            True if activation successful
        """
        try:
            # Import here to avoid circular dependencies
            from tools.governance.agent_handshake import AgentHandshakeProtocol

            ahp = AgentHandshakeProtocol(project_root=self.project_root)
            _ = ahp.validate(output_mode="silent")

            # Mark as activated by storing state
            runtime_dir = self.project_root / ".providence" / "runtime"
            runtime_dir.mkdir(parents=True, exist_ok=True)

            return True
        except Exception:
            return False

    def auto_activate(self) -> list[dict[str, Any]]:
        """Auto-activate all applicable seedlings (on_project_load trigger)

        This is the main entry point called automatically when IDE starts.

        Returns:
            List of successfully executed seedlings
        """
        activated = []
        seedlings = self.load_by_trigger("on_project_load")

        for seed in seedlings:
            if seed.get("auto_activate") and self.execute_seed(seed):
                activated.append(seed)

        return activated


def auto_activate_governance(project_root: Path | None = None) -> bool:
    """Convenience function to auto-activate governance on project load

    Args:
        project_root: Project root (auto-detected if None)

    Returns:
        True if activation successful
    """
    if project_root is None:
        project_root = Path.cwd()

    loader = SeedlingLoader(project_root)
    activated = loader.auto_activate()
    return len(activated) > 0
