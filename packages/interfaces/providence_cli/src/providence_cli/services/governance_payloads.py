"""Canonical JSON envelope helpers for governance command handlers."""

from __future__ import annotations

from typing import Any

from providence_cli.shared.contracts import build_error_result, build_ok_result


def governance_ok(command: str, data: dict[str, Any]) -> dict[str, Any]:
    """Build canonical success envelope for governance commands."""
    return build_ok_result(command, data)


def governance_error(
    command: str, data: dict[str, Any], *, code: str, message: str
) -> dict[str, Any]:
    """Build canonical error envelope for governance commands."""
    return build_error_result(command, data, code=code, message=message)


def build_governance_audit_data(report: Any) -> dict[str, Any]:
    """Build canonical data payload for `governance audit`."""
    return {
        "score": report.score,
        "issues": [
            {
                "severity": issue.severity,
                "category": issue.category,
                "message": issue.message,
                "remediation": issue.remediation,
            }
            for issue in report.issues
        ],
        "metadata": report.metadata,
        "exit_code": 0 if report.ok else 1,
    }


def build_governance_handshake_completed_data(result: Any) -> dict[str, Any]:
    """Build canonical data payload for completed handshake responses."""
    return {
        "status": "completed",
        "agent_id": result.agent_id,
        "timestamp": result.timestamp,
        "skills_authorized": result.skills_to_use,
    }


def build_governance_compile_data(
    *,
    core_items: int,
    client_items: int,
    core_msgpack: str,
    client_msgpack: str,
    core_fingerprint: str,
    exit_code: int,
    consistency_reason: str | None = None,
) -> dict[str, Any]:
    """Build canonical data payload for `governance compile`."""
    data: dict[str, Any] = {
        "summary": {
            "core_items": core_items,
            "client_items": client_items,
            "core_msgpack": core_msgpack,
            "client_msgpack": client_msgpack,
            "core_fingerprint": core_fingerprint,
        },
        "exit_code": exit_code,
    }
    if consistency_reason is not None:
        data["consistency_reason"] = consistency_reason
    return data


def build_governance_load_data(
    *, path: str, summary: dict[str, Any] | None, exit_code: int
) -> dict[str, Any]:
    """Build canonical data payload for `governance load`."""
    data: dict[str, Any] = {"path": path, "exit_code": exit_code}
    if summary is not None:
        data["summary"] = summary
    return data


def build_governance_validate_data(
    *,
    path: str,
    checks: list[dict[str, Any]],
    advisories: list[dict[str, Any]],
    preflight: dict[str, Any],
    consistency_reason: str,
    exit_code: int,
    root_seed_drift_reason: str = "root-seed drift check not configured",
) -> dict[str, Any]:
    """Build canonical data payload for `governance validate`."""
    return {
        "path": path,
        "checks": checks,
        "advisories": advisories,
        "preflight": preflight,
        "consistency_reason": consistency_reason,
        "root_seed_drift_reason": root_seed_drift_reason,
        "exit_code": exit_code,
    }


def build_governance_generate_data(
    *,
    path: str,
    output_base: str,
    seeds_dir: str,
    generated_files: list[dict[str, Any]],
    skills_generated: bool,
    skill_index_generated: bool,
    cli_index_generated: bool,
    exit_code: int,
) -> dict[str, Any]:
    """Build canonical data payload for `governance generate`."""
    return {
        "path": path,
        "output_base": output_base,
        "seeds_dir": seeds_dir,
        "generated_files": generated_files,
        "skills_generated": skills_generated,
        "skill_index_generated": skill_index_generated,
        "cli_index_generated": cli_index_generated,
        "exit_code": exit_code,
    }


def build_governance_reconcile_data(
    *, mode: str, summary: dict[str, Any], exit_code: int
) -> dict[str, Any]:
    """Build canonical data payload for `governance reconcile`."""
    return {
        "mode": mode,
        "summary": summary,
        "exit_code": exit_code,
    }
