#!/usr/bin/env python3
"""Environment boundary gates for CI/CD workflows.

This script implements lightweight, deterministic checks aligned with the
`enforce-environment-separation` OpenSpec change.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess  # nosec B404
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GateResult:
    gate: str
    mode: str
    ok: bool
    code: str
    message: str
    details: dict[str, object]


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _emit(result: GateResult) -> int:
    payload = {
        "gate": result.gate,
        "mode": result.mode,
        "ok": result.ok,
        "code": result.code,
        "message": result.message,
        "details": result.details,
    }
    print(json.dumps(payload, ensure_ascii=True))
    prefix = "PASS" if result.ok else ("WARN" if result.mode == "warn" else "FAIL")
    print(f"{prefix}: {result.code}: {result.message}")
    if result.ok or result.mode == "warn":
        return 0
    return 1


def _allowed_in_test_path(path: Path) -> bool:
    resolved = path.resolve()
    markers = (
        "/tmp/",  # nosec B108 — detection string only, not temp file creation
        "\\tmp\\",
        "sdd-shadow-repo",
        ".pytest-of-",
        "pytest-",
    )
    if any(m in str(resolved) for m in markers):
        return True
    test_root = os.environ.get("SDD_TEST_OUTPUT_DIR", "").strip()
    if test_root:
        try:
            root = Path(test_root).resolve()
            if resolved.is_relative_to(root):
                return True
        except Exception:
            return False
    return False


def gate_env_boundary_lint(mode: str, context: str) -> GateResult:
    forbidden_by_context: dict[str, set[str]] = {
        "test": {"SDD_GOVERNANCE_MODE"},
        "security": set(),
        "health": set(),
    }
    required_by_context: dict[str, set[str]] = {
        "test": set(),
        "security": set(),
        "health": set(),
    }
    forbidden = forbidden_by_context.get(context, set())
    required = required_by_context.get(context, set())
    found_forbidden = sorted(
        var for var in forbidden if os.environ.get(var, "").strip()
    )
    missing_required = sorted(
        var for var in required if not os.environ.get(var, "").strip()
    )
    if found_forbidden or missing_required:
        return GateResult(
            gate="env-boundary-lint",
            mode=mode,
            ok=False,
            code="ENV_BOUNDARY_VIOLATION",
            message="Variable policy mismatch for current context",
            details={
                "context": context,
                "forbidden_present": found_forbidden,
                "required_missing": missing_required,
            },
        )
    return GateResult(
        gate="env-boundary-lint",
        mode=mode,
        ok=True,
        code="OK",
        message="Environment variable policy is valid for context",
        details={"context": context},
    )


def gate_workspace_root_resolution_check(mode: str) -> GateResult:
    raw = os.environ.get("SDD_WORKSPACE_ROOT", "").strip()
    if not raw:
        return GateResult(
            gate="workspace-root-resolution-check",
            mode=mode,
            ok=True,
            code="OK",
            message="No explicit SDD_WORKSPACE_ROOT override set",
            details={},
        )
    path = Path(raw)
    if not path.exists() or not path.is_dir():
        return GateResult(
            gate="workspace-root-resolution-check",
            mode=mode,
            ok=False,
            code="WORKSPACE_ROOT_POLICY_VIOLATION",
            message="Invalid SDD_WORKSPACE_ROOT override",
            details={"path": raw},
        )
    return GateResult(
        gate="workspace-root-resolution-check",
        mode=mode,
        ok=True,
        code="OK",
        message="Workspace root override exists and is a directory",
        details={"path": str(path.resolve())},
    )


def gate_test_isolation_preflight(mode: str) -> GateResult:
    has_output_dir = bool(os.environ.get("SDD_TEST_OUTPUT_DIR", "").strip())
    allow_repo_mutation = _truthy(os.environ.get("SDD_ALLOW_REPO_SDD_MUTATION"))
    if has_output_dir or allow_repo_mutation:
        return GateResult(
            gate="test-isolation-preflight",
            mode=mode,
            ok=True,
            code="OK",
            message="Test isolation preflight satisfied",
            details={
                "has_sdd_test_output_dir": has_output_dir,
                "allow_repo_sdd_mutation": allow_repo_mutation,
            },
        )
    return GateResult(
        gate="test-isolation-preflight",
        mode=mode,
        ok=False,
        code="TEST_ISOLATION_REQUIRED",
        message="Isolated output root is missing",
        details={},
    )


def gate_repo_providence_mutation_guard(mode: str) -> GateResult:
    root = Path.cwd()
    result = subprocess.run(  # nosec B603
        ["git", "status", "--porcelain", ".providence"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return GateResult(
            gate="repo-providence-mutation-guard",
            mode=mode,
            ok=False,
            code="TEST_POLICY_VIOLATION",
            message="Could not evaluate repository .providence status",
            details={"stderr": result.stderr.strip()},
        )
    dirty = [line for line in result.stdout.splitlines() if line.strip()]
    if dirty:
        return GateResult(
            gate="repo-providence-mutation-guard",
            mode=mode,
            ok=False,
            code="TEST_POLICY_VIOLATION",
            message="Repository .providence mutation detected",
            details={"entries": dirty[:20]},
        )
    return GateResult(
        gate="repo-providence-mutation-guard",
        mode=mode,
        ok=True,
        code="OK",
        message="Repository .providence is clean",
        details={},
    )


# Compatibility alias: "repo-sdd-mutation-guard" is the pre-rename gate id.
# Keep it importable/callable under the old name until a deprecation plan lands.
gate_repo_sdd_mutation_guard = gate_repo_providence_mutation_guard


def gate_runtime_seed_drift_check(mode: str) -> GateResult:
    """Detect drift in managed runtime/seed artifacts."""
    root = Path.cwd()
    targets = [
        ".providence/runtime",
        ".providence/trust",
        ".providence/commands/registry.json",
        ".providence/skills/registry.json",
        "CLAUDE.md",
        ".claude",
        ".gemini",
        ".cursor/rules",
        ".vscode/ai-rules.md",
        ".github/copilot-instructions.md",
    ]
    cmd = ["git", "status", "--porcelain", *targets]
    result = subprocess.run(  # nosec B603
        cmd,
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return GateResult(
            gate="runtime-seed-drift-check",
            mode=mode,
            ok=False,
            code="RUNTIME_SEED_DRIFT_VIOLATION",
            message="Could not evaluate runtime/seed drift status",
            details={"stderr": result.stderr.strip()},
        )
    dirty = [line for line in result.stdout.splitlines() if line.strip()]
    if dirty:
        return GateResult(
            gate="runtime-seed-drift-check",
            mode=mode,
            ok=False,
            code="RUNTIME_SEED_DRIFT_VIOLATION",
            message="Runtime/seed artifacts drift detected",
            details={"entries": dirty[:40]},
        )
    return GateResult(
        gate="runtime-seed-drift-check",
        mode=mode,
        ok=True,
        code="OK",
        message="No runtime/seed drift detected",
        details={},
    )


def gate_telemetry_path_scope_check(mode: str) -> GateResult:
    offenders: list[str] = []
    for var in ("SDD_TELEMETRY_PATH", "SDD_COMPLIANCE_EVENTS_PATH"):
        raw = os.environ.get(var, "").strip()
        if not raw:
            continue
        if not _allowed_in_test_path(Path(raw)):
            offenders.append(f"{var}={raw}")
    if offenders:
        return GateResult(
            gate="telemetry-path-scope-check",
            mode=mode,
            ok=False,
            code="TELEMETRY_PATH_SCOPE_VIOLATION",
            message="Telemetry path outside allowed test scope",
            details={"offenders": offenders},
        )
    return GateResult(
        gate="telemetry-path-scope-check",
        mode=mode,
        ok=True,
        code="OK",
        message="Telemetry path scope is valid",
        details={},
    )


def gate_trusted_keyring_precedence_check(mode: str) -> GateResult:
    sig_mode = os.environ.get("SDD_SIGNATURE_MODE", "warn").strip().lower()
    override = os.environ.get("SDD_TRUSTED_KEYRING", "").strip()
    canonical = Path(".providence/trust/trusted-keys.json")
    if sig_mode == "strict" and override and not canonical.exists():
        return GateResult(
            gate="trusted-keyring-precedence-check",
            mode=mode,
            ok=False,
            code="KEYRING_PRECEDENCE_VIOLATION",
            message="Canonical trusted keyring required in strict mode",
            details={"canonical": str(canonical), "override": override},
        )
    return GateResult(
        gate="trusted-keyring-precedence-check",
        mode=mode,
        ok=True,
        code="OK",
        message="Trusted keyring precedence is valid",
        details={"signature_mode": sig_mode},
    )


def gate_signature_mode_policy_check(mode: str) -> GateResult:
    value = os.environ.get("SDD_SIGNATURE_MODE", "").strip().lower() or "warn"
    if value not in {"off", "warn", "strict"}:
        return GateResult(
            gate="signature-mode-policy-check",
            mode=mode,
            ok=False,
            code="SIGNATURE_MODE_POLICY_VIOLATION",
            message="Invalid signature mode value",
            details={"value": value},
        )
    if mode == "enforce" and value != "strict":
        return GateResult(
            gate="signature-mode-policy-check",
            mode=mode,
            ok=False,
            code="SIGNATURE_MODE_POLICY_VIOLATION",
            message="Signature mode does not satisfy stage policy",
            details={"value": value, "required": "strict"},
        )
    return GateResult(
        gate="signature-mode-policy-check",
        mode=mode,
        ok=True,
        code="OK",
        message="Signature mode policy satisfied",
        details={"value": value},
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run CI environment boundary gates")
    parser.add_argument(
        "gate",
        choices=[
            "env-boundary-lint",
            "workspace-root-resolution-check",
            "test-isolation-preflight",
            "repo-providence-mutation-guard",
            "repo-sdd-mutation-guard",  # compatibility alias, see gate_repo_sdd_mutation_guard
            "runtime-seed-drift-check",
            "telemetry-path-scope-check",
            "trusted-keyring-precedence-check",
            "signature-mode-policy-check",
        ],
    )
    parser.add_argument("--mode", choices=["warn", "enforce"], default="warn")
    parser.add_argument(
        "--context", choices=["health", "test", "security"], default="test"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.gate == "env-boundary-lint":
        return _emit(gate_env_boundary_lint(args.mode, args.context))
    if args.gate == "workspace-root-resolution-check":
        return _emit(gate_workspace_root_resolution_check(args.mode))
    if args.gate == "test-isolation-preflight":
        return _emit(gate_test_isolation_preflight(args.mode))
    if args.gate in ("repo-providence-mutation-guard", "repo-sdd-mutation-guard"):
        return _emit(gate_repo_providence_mutation_guard(args.mode))
    if args.gate == "runtime-seed-drift-check":
        return _emit(gate_runtime_seed_drift_check(args.mode))
    if args.gate == "telemetry-path-scope-check":
        return _emit(gate_telemetry_path_scope_check(args.mode))
    if args.gate == "trusted-keyring-precedence-check":
        return _emit(gate_trusted_keyring_precedence_check(args.mode))
    if args.gate == "signature-mode-policy-check":
        return _emit(gate_signature_mode_policy_check(args.mode))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
