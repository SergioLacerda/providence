"""Handshake validation engine."""

from __future__ import annotations

import configparser
import json
from pathlib import Path

from ._handshake_validation_result import ValidationResult
from ._handshake_validation_result import result as _result


class GovernanceValidator:
    """Execute layered governance validation for handshake decisions."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def layer_1_discovery(self) -> tuple[str, list[ValidationResult]]:
        """Validate that the workspace exposes the minimum SDD footprint."""
        sdd_dir = self.project_root / ".providence"
        sdd_exists = sdd_dir.exists()
        profile_exists = (sdd_dir / "profile").exists()
        governance_exists = (
            self.project_root / ".providence" / "compiled" / "governance-core.json"
        ).exists()
        results = [
            _result(
                ".providence/ directory",
                sdd_exists,
                f"Found at {sdd_dir}"
                if sdd_exists
                else "Not initialized — run 'providence init'",
                "DISCOVERY",
            ),
            _result(
                ".providence/profile",
                profile_exists,
                "Found" if profile_exists else "Missing — run 'providence init'",
                "DISCOVERY",
            ),
            _result(
                "governance-core.json",
                governance_exists,
                "Found"
                if governance_exists
                else "Not compiled (optional at this stage)",
                "DISCOVERY",
            ),
        ]
        return ("CONNECTED" if sdd_exists else "NOT_CONNECTED"), results

    def layer_2_link_validation(self) -> tuple[str, list[ValidationResult]]:
        """Validate profile and framework links required by the workspace."""
        profile_path = self.project_root / ".providence" / "profile"
        profile_readable = profile_valid = False
        if profile_path.exists():
            try:
                parser = configparser.ConfigParser()
                parser.read(profile_path)
                profile_type = parser.get("sdd", "type", fallback="").strip().lower()
                profile_readable, profile_valid = (
                    True,
                    profile_type in ("master", "client"),
                )
            except Exception:
                profile_readable = False
        results = [
            _result(
                ".providence/profile readable",
                profile_readable,
                "Parses correctly" if profile_readable else "Invalid or missing",
                "LINK_VALIDATION",
            ),
            _result(
                ".providence/profile type valid",
                profile_valid,
                "type=master|client"
                if profile_valid
                else "type field missing or invalid",
                "LINK_VALIDATION",
            ),
            _result(
                "packages framework",
                (self.project_root / "packages").exists(),
                "Framework accessible"
                if (self.project_root / "packages").exists()
                else "Not found",
                "LINK_VALIDATION",
            ),
        ]
        if profile_readable and profile_valid:
            return "LINK_OK", results
        return ("BROKEN_LINK" if profile_path.exists() else "NO_CONFIG"), results

    def layer_3_runtime_validation(self) -> tuple[str, list[ValidationResult]]:
        """Validate runtime cache and initialization state."""
        runtime_dir = self.project_root / ".providence" / "runtime"
        runtime_exists = runtime_dir.exists()
        state_exists = (
            (runtime_dir / "governance-state.json").exists()
            if runtime_exists
            else False
        )
        phase_0_done = (runtime_dir / ".phase-0-complete").exists()
        results = [
            _result(
                ".providence/runtime/",
                runtime_exists,
                "Initialized" if runtime_exists else "Not initialized",
                "RUNTIME_VALIDATION",
            ),
            _result(
                "state cache",
                state_exists,
                "Cache initialized" if state_exists else "Cache not created",
                "RUNTIME_VALIDATION",
            ),
            _result(
                "PHASE 0 setup",
                phase_0_done,
                "Completed" if phase_0_done else "Not run yet",
                "RUNTIME_VALIDATION",
            ),
        ]
        if phase_0_done and state_exists:
            return "READY", results
        return ("PARTIAL" if runtime_exists else "NOT_INITIALIZED"), results

    def layer_4_governance_health(self) -> tuple[str, list[ValidationResult]]:
        """Validate compiled governance artifacts and their readability."""
        governance_path = (
            self.project_root / ".providence" / "compiled" / "governance-core.json"
        )
        governance_valid, governance_items = False, 0
        if governance_path.exists():
            try:
                governance_items = len(
                    json.loads(governance_path.read_text(encoding="utf-8")).get(
                        "items", []
                    )
                )
                governance_valid = True
            except Exception:
                governance_valid = False
        compiled_exists = (self.project_root / ".providence" / "compiled").exists()
        results = [
            _result(
                "governance integrity",
                governance_valid,
                f"Valid ({governance_items} items)"
                if governance_valid
                else "Not compiled",
                "GOVERNANCE_HEALTH",
            ),
            _result(
                "compiled artifacts",
                compiled_exists,
                "Present"
                if compiled_exists
                else "No compiled artifacts found — run 'providence governance compile'",
                "GOVERNANCE_HEALTH",
            ),
        ]
        if governance_valid and compiled_exists:
            return "HEALTHY", results
        return (
            "DEGRADED" if governance_valid or compiled_exists else "UNKNOWN"
        ), results

    @staticmethod
    def compute_final_state(l1: str, l2: str, l3: str, l4: str) -> str:
        """Collapse layer states into the final handshake status."""
        if l1 == "NOT_CONNECTED":
            return "NOT_CONNECTED"
        if l2 == "BROKEN_LINK":
            return "MISCONFIGURED"
        if l3 == "NOT_INITIALIZED":
            return "NOT_INITIALIZED"
        if "PARTIAL" in [l1, l2, l3, l4]:
            return "PARTIAL"
        return "HEALTHY"

    @staticmethod
    def compute_confidence(all_results: list[ValidationResult]) -> float:
        """Compute confidence as the percentage of passing validation checks."""
        return (
            0.0
            if not all_results
            else (sum(1 for result in all_results if result.passed) / len(all_results))
            * 100
        )
