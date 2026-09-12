from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


def _load_module():
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "tools" / "ci" / "environment_gates.py"
    spec = importlib.util.spec_from_file_location("environment_gates", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def test_env_boundary_lint_warn_returns_success_on_violation(monkeypatch):
    gates = _load_module()
    monkeypatch.setenv("SDD_GOVERNANCE_MODE", "hardened")
    result = gates.gate_env_boundary_lint("warn", "test")
    assert result.ok is False
    assert result.code == "ENV_BOUNDARY_VIOLATION"
    assert gates._emit(result) == 0


def test_env_boundary_lint_enforce_returns_error_on_violation(monkeypatch):
    gates = _load_module()
    monkeypatch.setenv("SDD_GOVERNANCE_MODE", "hardened")
    result = gates.gate_env_boundary_lint("enforce", "test")
    assert result.ok is False
    assert result.code == "ENV_BOUNDARY_VIOLATION"
    assert gates._emit(result) == 1


def test_test_isolation_preflight_passes_with_test_output_dir(monkeypatch):
    gates = _load_module()
    monkeypatch.setenv("SDD_TEST_OUTPUT_DIR", "/tmp/sdd-test-output")
    result = gates.gate_test_isolation_preflight("enforce")
    assert result.ok is True
    assert result.code == "OK"


def test_telemetry_scope_fails_for_non_test_path(monkeypatch):
    gates = _load_module()
    monkeypatch.setenv("SDD_TELEMETRY_PATH", "/var/log/telemetry.jsonl")
    result = gates.gate_telemetry_path_scope_check("enforce")
    assert result.ok is False
    assert result.code == "TELEMETRY_PATH_SCOPE_VIOLATION"


def test_telemetry_scope_passes_for_tmp_path(monkeypatch):
    gates = _load_module()
    monkeypatch.setenv("SDD_TELEMETRY_PATH", "/tmp/sdd-test-output/telemetry.jsonl")
    result = gates.gate_telemetry_path_scope_check("enforce")
    assert result.ok is True
    assert result.code == "OK"


def test_repo_providence_mutation_guard_detects_dirty(monkeypatch):
    gates = _load_module()

    class _FakeCompleted:
        returncode = 0
        stdout = " M .providence/trust/trusted-keys.json\n"
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: _FakeCompleted())
    result = gates.gate_repo_providence_mutation_guard("enforce")
    assert result.ok is False
    assert result.code == "TEST_POLICY_VIOLATION"
    assert result.gate == "repo-providence-mutation-guard"


def test_repo_sdd_mutation_guard_alias_matches_canonical(monkeypatch):
    gates = _load_module()

    class _FakeCompleted:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: _FakeCompleted())
    result = gates.gate_repo_sdd_mutation_guard("enforce")
    assert result.ok is True
    assert result.gate == "repo-providence-mutation-guard"


def test_runtime_seed_drift_check_detects_dirty(monkeypatch):
    gates = _load_module()

    class _FakeCompleted:
        returncode = 0
        stdout = " M .providence/runtime/governance-state.json\n M CLAUDE.md\n"
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: _FakeCompleted())
    result = gates.gate_runtime_seed_drift_check("warn")
    assert result.ok is False
    assert result.code == "RUNTIME_SEED_DRIFT_VIOLATION"
    assert gates._emit(result) == 0


def test_runtime_seed_drift_check_passes_when_clean(monkeypatch):
    gates = _load_module()

    class _FakeCompleted:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: _FakeCompleted())
    result = gates.gate_runtime_seed_drift_check("enforce")
    assert result.ok is True
    assert result.code == "OK"


def test_trusted_keyring_precedence_strict_requires_canonical(monkeypatch, tmp_path):
    gates = _load_module()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SDD_SIGNATURE_MODE", "strict")
    monkeypatch.setenv("SDD_TRUSTED_KEYRING", "/tmp/override-keyring.json")
    result = gates.gate_trusted_keyring_precedence_check("enforce")
    assert result.ok is False
    assert result.code == "KEYRING_PRECEDENCE_VIOLATION"


def test_signature_mode_policy_warn_accepts_warn(monkeypatch):
    gates = _load_module()
    monkeypatch.setenv("SDD_SIGNATURE_MODE", "warn")
    result = gates.gate_signature_mode_policy_check("warn")
    assert result.ok is True
    assert result.code == "OK"


def test_signature_mode_policy_enforce_requires_strict(monkeypatch):
    gates = _load_module()
    monkeypatch.setenv("SDD_SIGNATURE_MODE", "warn")
    result = gates.gate_signature_mode_policy_check("enforce")
    assert result.ok is False
    assert result.code == "SIGNATURE_MODE_POLICY_VIOLATION"
