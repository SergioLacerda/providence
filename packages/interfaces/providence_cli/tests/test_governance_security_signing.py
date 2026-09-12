"""Tests for providence_cli.services.governance_security_handlers  artifact signing and keyring."""

from __future__ import annotations

import json
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import typer
from rich.console import Console

from providence_cli.services._governance_security_support import (
    perform_artifact_signing_flow,
)
from providence_cli.services.governance_security_handlers import (
    _perform_artifact_signing,
    _update_trusted_keyring,
)

pytestmark = pytest.mark.unit

_CONSOLE = Console(highlight=False)


def _fake_signing_runner() -> MagicMock:
    """A CompilerRunner stand-in whose .sign() writes a compatible manifest."""
    runner = MagicMock()

    def fake_sign(*, artifact_path, key_path, key_id, profile):  # noqa: ANN001
        sig_path = Path(artifact_path).with_suffix(Path(artifact_path).suffix + ".sig")
        manifest = {
            "schema_version": "1.0",
            "algorithm": "ed25519",
            "key_id": key_id,
            "artifact_name": Path(artifact_path).name,
            "profile": profile,
            "payload_hash": "a" * 64,
            "signature": "ZmFrZS1zaWc=",
            "signed_at": "2026-01-01T00:00:00Z",
        }
        sig_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return {"ok": True, "sig_path": str(sig_path)}

    runner.sign.side_effect = fake_sign
    return runner


# ---------------------------------------------------------------------------
# _perform_artifact_signing
# ---------------------------------------------------------------------------


class TestPerformArtifactSigning:
    def test_signs_existing_artifact(self, tmp_path: Path) -> None:
        artifact = tmp_path / "governance-core.json"
        artifact.write_text('{"key": "value"}', encoding="utf-8")

        count = perform_artifact_signing_flow(
            c_dir=tmp_path,
            k_path=tmp_path / "mykey.key",
            key_id="mykey",
            targets=["governance-core.json"],
            console=_CONSOLE,
            compiler_runner_factory=_fake_signing_runner,
        )

        assert count == 1
        sig_file = tmp_path / "governance-core.json.sig"
        assert sig_file.exists()
        manifest = json.loads(sig_file.read_text(encoding="utf-8"))
        assert manifest["key_id"] == "mykey"
        assert manifest["algorithm"] == "ed25519"

    def test_skips_missing_artifact(self, tmp_path: Path) -> None:
        factory = MagicMock(side_effect=_fake_signing_runner)
        count = perform_artifact_signing_flow(
            c_dir=tmp_path,
            k_path=tmp_path / "key.key",
            key_id="k",
            targets=["nonexistent.json"],
            console=_CONSOLE,
            compiler_runner_factory=factory,
        )
        assert count == 0
        factory.assert_not_called()

    def test_profile_uses_core_in_name(self, tmp_path: Path) -> None:
        artifact = tmp_path / "governance-core.json"
        artifact.write_text("{}", encoding="utf-8")

        perform_artifact_signing_flow(
            c_dir=tmp_path,
            k_path=tmp_path / "k.key",
            key_id="k",
            targets=["governance-core.json"],
            console=_CONSOLE,
            compiler_runner_factory=_fake_signing_runner,
        )

        sig = json.loads(
            (tmp_path / "governance-core.json.sig").read_text(encoding="utf-8")
        )
        assert sig["profile"] == "master"

    def test_profile_client_for_non_core(self, tmp_path: Path) -> None:
        artifact = tmp_path / "skill-registry.json"
        artifact.write_text("{}", encoding="utf-8")

        perform_artifact_signing_flow(
            c_dir=tmp_path,
            k_path=tmp_path / "k.key",
            key_id="k",
            targets=["skill-registry.json"],
            console=_CONSOLE,
            compiler_runner_factory=_fake_signing_runner,
        )

        sig = json.loads(
            (tmp_path / "skill-registry.json.sig").read_text(encoding="utf-8")
        )
        assert sig["profile"] == "client"

    def test_missing_native_backend_reports_actionable_dependency_error(
        self, tmp_path: Path
    ) -> None:
        artifact = tmp_path / "governance-core.json"
        artifact.write_text("{}", encoding="utf-8")
        output = StringIO()
        console = Console(file=output, highlight=False, force_terminal=False)

        def factory() -> MagicMock:
            raise RuntimeError("sdd-compile binary not found")

        with pytest.raises(typer.Exit) as exc_info:
            perform_artifact_signing_flow(
                c_dir=tmp_path,
                k_path=tmp_path / ".providence" / "trust" / "dev-01.key",
                key_id="dev-01",
                targets=["governance-core.json"],
                console=console,
                compiler_runner_factory=factory,
            )

        assert exc_info.value.exit_code == 1
        text = output.getvalue()
        assert "Native signing backend (sdd-compile) is not available" in text
        assert "sdd-compile binary not found" in text
        assert "full bootstrap defaults to key id 'dev-01'" in text

    def test_signing_backend_failure_reports_actionable_error(
        self, tmp_path: Path
    ) -> None:
        artifact = tmp_path / "governance-core.json"
        artifact.write_text("{}", encoding="utf-8")
        output = StringIO()
        console = Console(file=output, highlight=False, force_terminal=False)

        runner = MagicMock()
        runner.sign.side_effect = RuntimeError("sign failed: bad key")

        with pytest.raises(typer.Exit) as exc_info:
            perform_artifact_signing_flow(
                c_dir=tmp_path,
                k_path=tmp_path / "k.key",
                key_id="k",
                targets=["governance-core.json"],
                console=console,
                compiler_runner_factory=lambda: runner,
            )

        assert exc_info.value.exit_code == 1
        assert "Signing failed for governance-core.json" in output.getvalue()

    def test_uses_default_compiler_runner_when_no_factory_given(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        artifact = tmp_path / "governance-core.json"
        artifact.write_text("{}", encoding="utf-8")

        runner = _fake_signing_runner()
        monkeypatch.setattr(
            "providence_cli.services._governance_security_support.CompilerRunner",
            lambda: runner,
        )

        count = perform_artifact_signing_flow(
            c_dir=tmp_path,
            k_path=tmp_path / "k.key",
            key_id="k",
            targets=["governance-core.json"],
            console=_CONSOLE,
        )

        assert count == 1
        runner.sign.assert_called_once()


# ---------------------------------------------------------------------------
# _perform_artifact_signing (wrapper)
# ---------------------------------------------------------------------------


class TestPerformArtifactSigningWrapper:
    def test_delegates_to_flow(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        artifact = tmp_path / "governance-core.json"
        artifact.write_text("{}", encoding="utf-8")

        runner = _fake_signing_runner()
        monkeypatch.setattr(
            "providence_cli.services._governance_security_support.CompilerRunner",
            lambda: runner,
        )

        count = _perform_artifact_signing(
            c_dir=tmp_path,
            k_path=tmp_path / "k.key",
            key_id="k",
            targets=["governance-core.json"],
            console=_CONSOLE,
        )
        assert count == 1


# ---------------------------------------------------------------------------
# _update_trusted_keyring
# ---------------------------------------------------------------------------


class TestUpdateTrustedKeyring:
    def test_creates_keyring_with_new_key(self, tmp_path: Path) -> None:
        k_path = tmp_path / "mykey.key"
        pub_path = tmp_path / "mykey.pub.pem"
        k_path.write_text("priv", encoding="utf-8")
        pub_path.write_text("-----BEGIN PUBLIC KEY-----\n", encoding="utf-8")

        _update_trusted_keyring(
            ws_root=tmp_path, k_path=k_path, key_id="mykey", console=_CONSOLE
        )

        keyring_path = tmp_path / ".providence" / "trust" / "trusted-keys.json"
        assert keyring_path.exists()
        data = json.loads(keyring_path.read_text(encoding="utf-8"))
        assert any(k["key_id"] == "mykey" for k in data["keys"])

    def test_updates_existing_key(self, tmp_path: Path) -> None:
        trust_dir = tmp_path / ".providence" / "trust"
        trust_dir.mkdir(parents=True)
        keyring_path = trust_dir / "trusted-keys.json"
        keyring_path.write_text(
            json.dumps({"keys": [{"key_id": "mykey", "status": "retired"}]}),
            encoding="utf-8",
        )
        k_path = tmp_path / "mykey.key"
        pub_path = tmp_path / "mykey.pub.pem"
        k_path.write_text("priv", encoding="utf-8")
        pub_path.write_text("-----BEGIN PUBLIC KEY-----\n", encoding="utf-8")

        _update_trusted_keyring(
            ws_root=tmp_path, k_path=k_path, key_id="mykey", console=_CONSOLE
        )

        data = json.loads(keyring_path.read_text(encoding="utf-8"))
        entry = next(k for k in data["keys"] if k["key_id"] == "mykey")
        assert entry["status"] == "active"

    def test_no_pub_key_returns_early(self, tmp_path: Path) -> None:
        k_path = tmp_path / "mykey.key"
        k_path.write_text("priv", encoding="utf-8")
        # No .pub.pem file

        _update_trusted_keyring(
            ws_root=tmp_path, k_path=k_path, key_id="mykey", console=_CONSOLE
        )

        keyring_path = tmp_path / ".providence" / "trust" / "trusted-keys.json"
        assert not keyring_path.exists()

    def test_handles_corrupted_keyring(self, tmp_path: Path) -> None:
        trust_dir = tmp_path / ".providence" / "trust"
        trust_dir.mkdir(parents=True)
        keyring_path = trust_dir / "trusted-keys.json"
        keyring_path.write_text("not valid json", encoding="utf-8")

        k_path = tmp_path / "mykey.key"
        pub_path = tmp_path / "mykey.pub.pem"
        k_path.write_text("priv", encoding="utf-8")
        pub_path.write_text("-----BEGIN PUBLIC KEY-----\n", encoding="utf-8")

        # Should not raise
        _update_trusted_keyring(
            ws_root=tmp_path, k_path=k_path, key_id="mykey", console=_CONSOLE
        )
