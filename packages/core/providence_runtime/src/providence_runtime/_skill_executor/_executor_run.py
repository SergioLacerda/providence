"""Main skill-run orchestration for `SkillExecutor`."""

from __future__ import annotations

import time
import warnings
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from providence_skills import SkillRunResult, format_governance_footer

from .._skill_contracts import _is_deprecation_due
from ..learning import SupervisedLearningStore
from ..telemetry import RuntimeEvent
from ._executor_commands import execute_skill_commands
from ._executor_pipeline import run_composed_skill
from ._executor_results import (
    build_execution_result,
    build_missing_skill_result,
    build_policy_blocked_result,
)
from ._handlers import _classify_execution_outcome, _get_skill_handler


def run_skill_flow(
    *,
    registry: Any,
    sink: Any,
    run_skill: Callable[..., SkillRunResult],
    name: str,
    execute: bool,
    profile: str,
    enforcement_mode: str,
    project_root: Path | None,
    context: dict[str, Any] | None,
    footer_policy: str,
) -> SkillRunResult:
    root = project_root or Path.cwd()
    learning = SupervisedLearningStore(root)
    footer_fn = _make_footer_fn(profile, footer_policy)
    skill = registry.get_skill(name)
    if skill is None:
        return build_missing_skill_result(
            skill_name=name,
            profile=profile,
            governance_footer=footer_fn("missing_skill", "error"),
        )
    from ..policy import PolicyEngine

    policy_check = PolicyEngine().evaluate_skill_policy(
        skill_name=name,
        skill=skill,
        enforcement_mode=enforcement_mode,
        project_root=project_root,
    )
    if not policy_check.allowed:
        drift = (
            "handshake_unauthorized"
            if "handshake" in policy_check.reason.lower()
            else "fallback_cli"
        )
        return build_policy_blocked_result(
            skill_name=name,
            profile=profile,
            reason=policy_check.reason,
            drift=drift,
            governance_footer=footer_fn(drift, "blocked"),
            cli_fallback=list(skill.cli_fallback),
        )
    if _is_deprecation_due(skill.deprecated_after):
        warnings.warn(
            f"Skill '{skill.name}' is deprecated (deprecated_after={skill.deprecated_after}).",
            DeprecationWarning,
            stacklevel=2,
        )
    artifacts: dict[str, Any] = {}
    handler = _get_skill_handler(name)
    handler_context = dict(context or {})
    handler_context.setdefault("_project_root", str(root))
    pre_run_result = _try_pre_run(
        run_skill=run_skill,
        handler=handler,
        handler_context=handler_context,
        learning=learning,
        skill=skill,
        profile=profile,
        enforcement_mode=enforcement_mode,
        execute=execute,
        root=root,
        artifacts=artifacts,
        footer_fn=footer_fn,
        sink=sink,
        registry=registry,
    )
    if pre_run_result is not None:
        return pre_run_result
    exit_code, execution_errors, command_results = (
        execute_skill_commands(
            skill=skill,
            root=root,
            handler=handler,
            learning=learning,
            context=handler_context,
        )
        if execute
        else (0, [], [])
    )
    artifacts["command_results"] = command_results
    if exit_code == 124 and handler is not None:
        artifacts.update(
            handler.timeout_hook(
                handler_context,
                learning=learning,
                skill=skill,
                elapsed_seconds=int(skill.budget_policy.get("timeout_seconds", 120)),
            )
        )
    if handler is not None:
        artifacts.update(
            handler.post_run(
                handler_context,
                learning=learning,
                exit_code=exit_code,
                artifacts=artifacts,
            )
        )
    policy_result, reason, drift = _classify_execution_outcome(
        execute=execute, exit_code=exit_code, execution_errors=execution_errors
    )
    return build_execution_result(
        skill_name=name,
        profile=profile,
        policy_result=policy_result,
        reason=reason,
        exit_code=exit_code,
        governance_footer=footer_fn(drift, "ok" if exit_code == 0 else "fail"),
        fallback=list(skill.cli_fallback),
        command_results=command_results,
        artifacts=artifacts,
    )


def _try_pre_run(**kwargs: Any) -> SkillRunResult | None:
    handler = kwargs["handler"]
    if handler is None:
        return None
    start = time.monotonic()
    outcome = handler.pre_run(
        kwargs["handler_context"],
        learning=kwargs["learning"],
        skill=kwargs["skill"],
        profile=kwargs["profile"],
        footer_fn=kwargs["footer_fn"],
    )
    _emit_gate_latency(
        sink=kwargs.get("sink"),
        skill=kwargs["skill"],
        gate_decision=outcome.artifacts.get("gate_decision"),
        duration_ms=int((time.monotonic() - start) * 1000),
    )
    kwargs["artifacts"].update(outcome.artifacts)
    if outcome.early_result is not None:
        return cast(SkillRunResult, outcome.early_result)
    if outcome.compose_config is None:
        return None
    return run_composed_skill(
        run_skill=kwargs["run_skill"],
        parent_skill=kwargs["skill"],
        context=kwargs["handler_context"],
        seed_artifacts=kwargs["artifacts"],
        compose_config=outcome.compose_config,
        execute=kwargs["execute"],
        profile=kwargs["profile"],
        enforcement_mode=kwargs["enforcement_mode"],
        project_root=kwargs["root"],
        registry=kwargs.get("registry"),
        footer_fn=kwargs["footer_fn"],
    )


def _emit_gate_latency(
    *,
    sink: Any,
    skill: Any,
    gate_decision: dict[str, Any] | None,
    duration_ms: int,
) -> None:
    """Emit a ``guardrail.gate.latency`` event for one correction-gate evaluation.

    No-op when there is no sink to emit to, or when this handler's pre_run
    did not evaluate a correction gate (``gate_decision`` absent — most
    handlers are not gate handlers at all). ``details.outcome`` carries the
    gate's actual decision value (``allow``/``deny``/``escalate``) rather than
    a separate vocabulary, so it never drifts from what `_evaluate_correction_gate`
    can return.
    """
    if sink is None or gate_decision is None:
        return
    skill_name = getattr(skill, "name", "") or ""
    sink.emit(
        RuntimeEvent(
            event="guardrail.gate.latency",
            command=f"skills run {skill_name}",
            status="ok",
            trace_id="",
            path_id=skill_name,
            duration_ms=duration_ms,
            details={
                "rule_id": gate_decision.get("rule_id", ""),
                "outcome": gate_decision.get("decision", ""),
            },
        )
    )


def _make_footer_fn(profile: str, footer_policy: str) -> Callable[[str, str], str]:
    def _maybe_footer(drift: str, governance: str) -> str:
        if footer_policy != "always":
            return ""
        return format_governance_footer(
            drift=drift, governance=governance, profile=profile
        )

    return _maybe_footer
