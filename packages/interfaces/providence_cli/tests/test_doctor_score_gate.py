"""Coverage tests for doctor command score and adherence gates."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import typer

import providence_core.governance.compliance as compliance_mod
import providence_core.governance.handshake as handshake_mod
import providence_core.governance.scoring as scoring_mod
import providence_core.utils.environment as env_mod
from providence_cli.commands import doctor as doctor_mod
from providence_cli.commands import doctor_gates as doctor_gates_mod


class TestDoctorHelpers:
    def test_get_default_spec_uses_repo_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(doctor_mod, "detect_repo_root", lambda: tmp_path)
        assert (
            doctor_mod._get_default_spec()
            .as_posix()
            .endswith(
                "packages/features/providence_integration/src/providence_integration/protocol/integration_flow.yaml"
            )
        )

    def test_apply_score_gate_disabled_and_policy_short_circuit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        doctor_mod._apply_score_gate(0)

        monkeypatch.setattr(
            doctor_gates_mod, "resolve_workspace_root", lambda: tmp_path
        )
        monkeypatch.setattr(
            doctor_gates_mod, "enforce_path_policy", lambda ws_root, **kwargs: None
        )
        doctor_mod._apply_score_gate(10)

    def test_apply_score_gate_profile_not_initialized(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        compiled_dir = tmp_path / ".providence" / "compiled"
        compiled_dir.mkdir(parents=True)
        (compiled_dir / "governance-core.json").write_text(
            json.dumps({"fingerprint": "0123456789abcdef"}),
            encoding="utf-8",
        )

        monkeypatch.setattr(
            doctor_gates_mod, "resolve_workspace_root", lambda: tmp_path
        )
        monkeypatch.setattr(
            doctor_gates_mod, "enforce_path_policy", lambda ws_root, **kwargs: ws_root
        )
        monkeypatch.setattr(
            doctor_gates_mod, "compiled_active_dir", lambda ws_root: compiled_dir
        )

        class _FakeAHP:
            def __init__(self, project_root: Path) -> None:
                self.project_root = project_root

            def validate(self, output_mode: str):
                return None, SimpleNamespace(confidence=100.0)

        monkeypatch.setattr(handshake_mod, "AgentHandshakeProtocol", _FakeAHP)
        monkeypatch.setattr(
            env_mod,
            "resolve_profile",
            lambda root: (_ for _ in ()).throw(
                env_mod.WorkspaceNotInitializedError("not ready")
            ),
        )
        monkeypatch.setattr(scoring_mod, "compute_governance_score", lambda checks: 100)
        doctor_mod._apply_score_gate(50)

    def test_apply_score_gate_exit_and_exception(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        compiled_dir = tmp_path / ".providence" / "compiled"
        compiled_dir.mkdir(parents=True)
        artifact = compiled_dir / "governance-core.json"
        artifact.write_text(
            json.dumps({"fingerprint": "0123456789abcdef"}), encoding="utf-8"
        )

        monkeypatch.setattr(
            doctor_gates_mod, "resolve_workspace_root", lambda: tmp_path
        )
        monkeypatch.setattr(
            doctor_gates_mod, "enforce_path_policy", lambda ws_root, **kwargs: ws_root
        )
        monkeypatch.setattr(
            doctor_gates_mod, "compiled_active_dir", lambda ws_root: compiled_dir
        )

        class _FakeAHP:
            def __init__(self, project_root: Path) -> None:
                self.project_root = project_root

            def validate(self, output_mode: str):
                return None, SimpleNamespace(confidence=100.0)

        monkeypatch.setattr(handshake_mod, "AgentHandshakeProtocol", _FakeAHP)
        monkeypatch.setattr(
            env_mod,
            "resolve_profile",
            lambda root: SimpleNamespace(core_hash="0123456789abcdef"),
        )
        monkeypatch.setattr(scoring_mod, "compute_governance_score", lambda checks: 10)

        with pytest.raises(typer.Exit):
            doctor_mod._apply_score_gate(50)

        monkeypatch.setattr(
            scoring_mod,
            "compute_governance_score",
            lambda checks: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        doctor_mod._apply_score_gate(50)

    def test_apply_score_gate_fingerprint_fallback(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        compiled_dir = tmp_path / ".providence" / "compiled"
        compiled_dir.mkdir(parents=True)
        artifact_path = compiled_dir / "governance-core.json"
        payload = {"alpha": 1, "beta": 2}
        artifact_path.write_text(json.dumps(payload), encoding="utf-8")
        expected_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()[:16]

        monkeypatch.setattr(
            doctor_gates_mod, "resolve_workspace_root", lambda: tmp_path
        )
        monkeypatch.setattr(
            doctor_gates_mod, "enforce_path_policy", lambda ws_root, **kwargs: ws_root
        )
        monkeypatch.setattr(
            doctor_gates_mod, "compiled_active_dir", lambda ws_root: compiled_dir
        )

        class _FakeAHP:
            def __init__(self, project_root: Path) -> None:
                self.project_root = project_root

            def validate(self, output_mode: str):
                return None, SimpleNamespace(confidence=100.0)

        monkeypatch.setattr(handshake_mod, "AgentHandshakeProtocol", _FakeAHP)
        monkeypatch.setattr(
            env_mod,
            "resolve_profile",
            lambda root: SimpleNamespace(core_hash=expected_hash),
        )
        monkeypatch.setattr(scoring_mod, "compute_governance_score", lambda checks: 100)
        doctor_mod._apply_score_gate(50)

    def test_apply_score_gate_hash_decode_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        compiled_dir = tmp_path / ".providence" / "compiled"
        compiled_dir.mkdir(parents=True)
        (compiled_dir / "governance-core.json").write_bytes(b"not-json")

        monkeypatch.setattr(
            doctor_gates_mod, "resolve_workspace_root", lambda: tmp_path
        )
        monkeypatch.setattr(
            doctor_gates_mod, "enforce_path_policy", lambda ws_root, **kwargs: ws_root
        )
        monkeypatch.setattr(
            doctor_gates_mod, "compiled_active_dir", lambda ws_root: compiled_dir
        )

        class _FakeAHP:
            def __init__(self, project_root: Path) -> None:
                self.project_root = project_root

            def validate(self, output_mode: str):
                return None, SimpleNamespace(confidence=100.0)

        monkeypatch.setattr(handshake_mod, "AgentHandshakeProtocol", _FakeAHP)
        monkeypatch.setattr(
            env_mod,
            "resolve_profile",
            lambda root: SimpleNamespace(core_hash="0123456789abcdef"),
        )
        monkeypatch.setattr(scoring_mod, "compute_governance_score", lambda checks: 100)
        doctor_mod._apply_score_gate(50)

    def test_apply_adherence_gate_variants(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        doctor_mod._apply_adherence_gate(0)

        monkeypatch.setattr(
            compliance_mod,
            "compute_governance_adherence",
            lambda workspace_root: {"score": 10},
        )
        monkeypatch.setattr(
            doctor_gates_mod, "resolve_workspace_root", lambda: Path("/tmp")
        )
        with pytest.raises(typer.Exit):
            doctor_mod._apply_adherence_gate(50)

        monkeypatch.setattr(
            compliance_mod,
            "compute_governance_adherence",
            lambda workspace_root: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        doctor_mod._apply_adherence_gate(50)
