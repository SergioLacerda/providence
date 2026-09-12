from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from providence_runtime._skill_executor import SkillExecutor
from providence_runtime._skill_registry import SkillRegistry
from providence_runtime.skills import _REGISTRY


def _make_executor(tmp_path: Path) -> SkillExecutor:
    return SkillExecutor(SkillRegistry(_REGISTRY, tmp_path))


def test_run_skill_returns_missing_skill(tmp_path: Path) -> None:
    result = _make_executor(tmp_path).run_skill("does-not-exist")
    assert result.exit_code == 1
    assert result.policy_result == "missing_skill"
    assert result.governance_footer


def test_run_skill_warn_mode_plans_successfully(tmp_path: Path) -> None:
    with patch(
        "providence_runtime.policy.PolicyEngine._check_handshake_guard",
        return_value=None,
    ):
        result = _make_executor(tmp_path).run_skill(
            "sdd-review-architecture", enforcement_mode="warn"
        )
    assert result.exit_code == 0
    assert result.policy_result == "planned"


def test_run_skill_strict_mode_blocks_high_risk(tmp_path: Path) -> None:
    with patch(
        "providence_runtime.policy.PolicyEngine._check_handshake_guard",
        return_value=None,
    ):
        result = _make_executor(tmp_path).run_skill(
            "sdd-review-architecture", enforcement_mode="strict"
        )
    assert result.exit_code == 1
    assert result.policy_result == "blocked"


def test_run_skill_handshake_unauthorized(tmp_path: Path) -> None:
    blocked = SimpleNamespace(
        allowed=False, reason="handshake missing skill declaration"
    )
    with patch(
        "providence_runtime.policy.PolicyEngine.evaluate_skill_policy",
        return_value=blocked,
    ):
        result = _make_executor(tmp_path).run_skill(
            "sdd-diagnose", enforcement_mode="strict", project_root=tmp_path
        )
    assert result.exit_code == 1
    assert result.policy_result == "unauthorized"


def test_run_skill_deprecated_emits_warning(tmp_path: Path) -> None:
    from providence_runtime._skill_contracts import SkillDefinition
    from providence_runtime.skills import _REGISTRY as registry

    original = registry["sdd-diagnose"]
    registry["sdd-diagnose"] = SkillDefinition(
        name=original.name,
        version=original.version,
        category=original.category,
        description=original.description,
        when_to_use=list(original.when_to_use),
        outcomes=list(original.outcomes),
        allowed_tools=list(original.allowed_tools),
        cli_fallback=list(original.cli_fallback),
        required_permissions=list(original.required_permissions),
        deprecated_after=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
    )
    try:
        with (
            patch(
                "providence_runtime.policy.PolicyEngine._check_handshake_guard",
                return_value=None,
            ),
            pytest.warns(DeprecationWarning, match="is deprecated"),
        ):
            result = _make_executor(tmp_path).run_skill(
                "sdd-diagnose", project_root=tmp_path
            )
        assert result.exit_code == 0
    finally:
        registry["sdd-diagnose"] = original
