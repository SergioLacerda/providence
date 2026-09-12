"""Telemetry emission helpers for the skill executor."""

from __future__ import annotations

from providence_skills import SkillRunResult

from ..telemetry import RuntimeEvent, TelemetrySink


def emit_skill_telemetry(
    sink: TelemetrySink | None,
    result: SkillRunResult,
) -> None:
    if sink is None:
        return
    sink.emit(
        RuntimeEvent(
            event="runtime.skill.run",
            command=f"skills run {result.skill}",
            status="ok" if result.exit_code == 0 else "fail",
            trace_id=result.trace_id or "",
            details={
                "skill": result.skill,
                "profile": result.profile,
                "policy_result": result.policy_result,
                "reason": result.reason,
                "fallback": result.fallback,
                # TEL-12 (`.analysis/refined/20260906-gaps-e-melhorias-review/backlog.md`):
                # `status` above collapses exit_code to ok/fail — the raw
                # numeric code is preserved here so a non-zero failure code
                # is inspectable, not just "fail".
                "exit_code": result.exit_code,
            },
        )
    )
