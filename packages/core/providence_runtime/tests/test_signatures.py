from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from providence_runtime import signatures as sig


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _valid_sig_payload(artifact_name: str, payload_hash: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "algorithm": "ed25519",
        "key_id": "key-1",
        "artifact_name": artifact_name,
        "profile": "master",
        "payload_hash": payload_hash,
        "signature": "c2ln",  # base64("sig")
        "signed_at": "2026-01-01T00:00:00Z",
    }


def test_remediation_and_fail_helpers() -> None:
    assert sig._remediation_for("SIG_MISSING") == "providence governance compile"
    r = sig._fail("SIG_INVALID", "bad", strict=True)
    assert r.blocking is True
    assert r.code == "SIG_INVALID"
    ok = sig._ok(trust_source="canonical")
    assert ok.ok is True


def test_load_json_requires_object(tmp_path: Path) -> None:
    p = tmp_path / "x.json"
    p.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="expected JSON object"):
        sig._load_json(p)


def test_validate_manifest_schema_errors() -> None:
    assert "missing required fields" in (sig._validate_manifest_schema({}) or "")
    bad = _valid_sig_payload("a", "a" * 64)
    bad["algorithm"] = "rsa"
    assert sig._validate_manifest_schema(bad) == "algorithm must be 'ed25519'"
    bad = _valid_sig_payload("a", "a" * 64)
    bad["key_id"] = "!!"
    assert sig._validate_manifest_schema(bad) == "invalid key_id pattern"
    bad = _valid_sig_payload("a", "a" * 64)
    bad["profile"] = "x"
    assert sig._validate_manifest_schema(bad) == "profile must be master|client"
    bad = _valid_sig_payload("a", "X" * 64)
    assert (
        sig._validate_manifest_schema(bad)
        == "payload_hash must be lowercase hex sha256"
    )
    bad = _valid_sig_payload("a", "a" * 64)
    bad["signature"] = "   "
    assert sig._validate_manifest_schema(bad) == "signature must be non-empty base64"
    bad = _valid_sig_payload("a", "a" * 64)
    bad["signed_at"] = "2026-01-01"
    assert "signed_at must be RFC3339" in (sig._validate_manifest_schema(bad) or "")


def test_resolve_public_key_pem_variants() -> None:
    assert sig._resolve_public_key_pem({"public_key_pem": " PEM "}) == "PEM"
    b64 = base64.b64encode(b"PEM2").decode()
    assert sig._resolve_public_key_pem({"public_key": b64}) == "PEM2"
    assert sig._resolve_public_key_pem({"public_key": "%%%bad%%%"}) is None


def test_verify_ed25519_signature_invalid_base64_short_circuit() -> None:
    assert (
        sig._verify_ed25519_signature(
            public_key_pem="x", message=b"m", signature_b64="bad@@@"
        )
        is False
    )


def test_verify_ed25519_signature_native_backend_success_and_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Runner:
        def __init__(self, valid: bool) -> None:
            self._valid = valid

        def verify(
            self, *, public_key_pem: str, message: str, signature_b64: str
        ) -> dict[str, bool]:
            return {"ok": True, "valid": self._valid}

    sig_b64 = base64.b64encode(b"sig").decode()
    monkeypatch.setattr(
        "providence_core.utils.compiler_runner.CompilerRunner", lambda: _Runner(True)
    )
    assert (
        sig._verify_ed25519_signature(
            public_key_pem="pem", message=b"m", signature_b64=sig_b64
        )
        is True
    )
    monkeypatch.setattr(
        "providence_core.utils.compiler_runner.CompilerRunner", lambda: _Runner(False)
    )
    assert (
        sig._verify_ed25519_signature(
            public_key_pem="pem", message=b"m", signature_b64=sig_b64
        )
        is False
    )


def test_verify_ed25519_signature_backend_unavailable_returns_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise() -> None:
        raise RuntimeError("sdd-compile binary not found")

    sig_b64 = base64.b64encode(b"sig").decode()
    monkeypatch.setattr("providence_core.utils.compiler_runner.CompilerRunner", _raise)
    assert (
        sig._verify_ed25519_signature(
            public_key_pem="pem", message=b"m", signature_b64=sig_b64
        )
        is False
    )


def test_resolve_keyring_path_modes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = tmp_path / "ws"
    compiled = ws / "generated"
    canonical = ws / ".providence" / "trust"
    canonical.mkdir(parents=True)
    compiled.mkdir(parents=True)
    (canonical / "trusted-keys.json").write_text('{"keys":[]}', encoding="utf-8")

    path, source, warning = sig._resolve_keyring_path(
        compiled, strict=True, workspace_root=ws
    )
    assert path is not None
    assert source == "canonical"
    assert warning == ""

    # Legacy path no longer exists in candidates — only canonical and override are checked.
    (canonical / "trusted-keys.json").unlink()
    monkeypatch.delenv("SDD_TRUSTED_KEYRING", raising=False)
    path, source, warning = sig._resolve_keyring_path(
        compiled, strict=False, workspace_root=ws
    )
    assert path is None
    assert source == "none"
    assert warning == ""
    path, source, warning = sig._resolve_keyring_path(
        compiled, strict=True, workspace_root=ws
    )
    assert path is None
    assert source == "none"
    assert "strict mode requires canonical keyring" in warning


def test_resolve_keyring_path_uses_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    compiled = tmp_path / "compiled"
    compiled.mkdir()
    override = tmp_path / "override.json"
    override.write_text('{"keys":[]}', encoding="utf-8")
    monkeypatch.setenv("SDD_TRUSTED_KEYRING", str(override))
    path, source, _ = sig._resolve_keyring_path(
        compiled, strict=False, workspace_root=tmp_path
    )
    assert path == override
    assert source == "override"


def test_resolve_keyring_canonical_wins_over_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Canonical path takes priority over SDD_TRUSTED_KEYRING when both exist."""
    ws = tmp_path / "ws"
    compiled = ws / "generated"
    canonical_dir = ws / ".providence" / "trust"
    canonical_dir.mkdir(parents=True)
    compiled.mkdir(parents=True)
    canonical_file = canonical_dir / "trusted-keys.json"
    canonical_file.write_text('{"keys":[]}', encoding="utf-8")

    override = tmp_path / "override.json"
    override.write_text('{"keys":[]}', encoding="utf-8")
    monkeypatch.setenv("SDD_TRUSTED_KEYRING", str(override))

    path, source, warning = sig._resolve_keyring_path(
        compiled, strict=False, workspace_root=ws
    )
    assert source == "canonical"
    assert path == canonical_file
    assert warning == ""


def test_resolve_keyring_override_fallback_emits_warning(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When canonical is absent and override is used, a warning is emitted."""
    compiled = tmp_path / "compiled"
    compiled.mkdir()
    override = tmp_path / "override.json"
    override.write_text('{"keys":[]}', encoding="utf-8")
    monkeypatch.setenv("SDD_TRUSTED_KEYRING", str(override))

    path, source, warning = sig._resolve_keyring_path(
        compiled, strict=False, workspace_root=tmp_path
    )
    assert source == "override"
    assert path == override
    assert "canonical keyring not found" in warning


def test_is_key_time_valid_branches() -> None:
    assert sig._is_key_time_valid({"not_before": "2999-01-01T00:00:00Z"}) is False
    assert sig._is_key_time_valid({"not_after": "2000-01-01T00:00:00Z"}) is False
    assert sig._is_key_time_valid({"not_before": "bad"}) is False


def test_validate_artifact_signature_core_flows(tmp_path: Path) -> None:
    artifact = tmp_path / "governance-core.json"
    artifact.write_text('{"x":1}', encoding="utf-8")
    sig_path = tmp_path / "governance-core.json.sig"

    # missing sig
    r = sig.validate_artifact_signature(
        artifact_path=artifact, sig_path=sig_path, strict=False, workspace_root=tmp_path
    )
    assert r.code == "SIG_MISSING"

    # parse error
    sig_path.write_text("{bad", encoding="utf-8")
    r = sig.validate_artifact_signature(
        artifact_path=artifact, sig_path=sig_path, strict=False, workspace_root=tmp_path
    )
    assert r.code == "SIG_PARSE_ERROR"

    # schema error
    _write_json(sig_path, {"schema_version": "1.0"})
    r = sig.validate_artifact_signature(
        artifact_path=artifact, sig_path=sig_path, strict=False, workspace_root=tmp_path
    )
    assert r.code == "SIG_SCHEMA_ERROR"


def test_validate_artifact_signature_success_and_failures(tmp_path: Path) -> None:
    artifact = tmp_path / "governance-core.json"
    artifact.write_text('{"x":1}', encoding="utf-8")
    payload_hash = __import__("hashlib").sha256(artifact.read_bytes()).hexdigest()
    sig_path = tmp_path / "governance-core.json.sig"
    _write_json(sig_path, _valid_sig_payload(artifact.name, payload_hash))

    ws = tmp_path / "ws"
    trust = ws / ".providence" / "trust"
    trust.mkdir(parents=True)
    keyring = trust / "trusted-keys.json"
    _write_json(
        keyring,
        {
            "keys": [
                {
                    "key_id": "key-1",
                    "status": "active",
                    "public_key_pem": "pem",
                    "not_before": "2000-01-01T00:00:00Z",
                    "not_after": "2999-01-01T00:00:00Z",
                }
            ]
        },
    )

    with patch(
        "providence_runtime.signatures._validate._verify_ed25519_signature",
        return_value=True,
    ):
        ok = sig.validate_artifact_signature(
            artifact_path=artifact, sig_path=sig_path, strict=True, workspace_root=ws
        )
        assert ok.code == "OK"
        assert ok.ok is True

    with patch(
        "providence_runtime.signatures._validate._verify_ed25519_signature",
        return_value=False,
    ):
        bad_sig = sig.validate_artifact_signature(
            artifact_path=artifact, sig_path=sig_path, strict=True, workspace_root=ws
        )
        assert bad_sig.code == "SIG_INVALID"

    # untrusted key
    _write_json(keyring, {"keys": []})
    untrusted = sig.validate_artifact_signature(
        artifact_path=artifact, sig_path=sig_path, strict=True, workspace_root=ws
    )
    assert untrusted.code == "SIG_UNTRUSTED_KEY"

    # invalid keyring format
    _write_json(keyring, {"keys": {}})
    invalid_format = sig.validate_artifact_signature(
        artifact_path=artifact, sig_path=sig_path, strict=True, workspace_root=ws
    )
    assert invalid_format.reason == "invalid keyring format"

    # revoked / invalid status / outside window / missing key
    _write_json(
        keyring,
        {"keys": [{"key_id": "key-1", "status": "revoked", "public_key_pem": "pem"}]},
    )
    revoked = sig.validate_artifact_signature(
        artifact_path=artifact, sig_path=sig_path, strict=True, workspace_root=ws
    )
    assert "revoked" in revoked.reason

    _write_json(
        keyring,
        {"keys": [{"key_id": "key-1", "status": "paused", "public_key_pem": "pem"}]},
    )
    bad_status = sig.validate_artifact_signature(
        artifact_path=artifact, sig_path=sig_path, strict=True, workspace_root=ws
    )
    assert "invalid status" in bad_status.reason

    _write_json(
        keyring,
        {
            "keys": [
                {
                    "key_id": "key-1",
                    "status": "active",
                    "not_before": "2999-01-01T00:00:00Z",
                    "public_key_pem": "pem",
                }
            ]
        },
    )
    bad_window = sig.validate_artifact_signature(
        artifact_path=artifact, sig_path=sig_path, strict=True, workspace_root=ws
    )
    assert "outside validity window" in bad_window.reason

    _write_json(
        keyring,
        {"keys": [{"key_id": "key-1", "status": "active"}]},
    )
    missing_key = sig.validate_artifact_signature(
        artifact_path=artifact, sig_path=sig_path, strict=True, workspace_root=ws
    )
    assert "missing public key" in missing_key.reason


def test_validate_artifact_signature_name_hash_and_keyring_load_errors(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "governance-core.json"
    artifact.write_text('{"x":1}', encoding="utf-8")
    payload_hash = __import__("hashlib").sha256(artifact.read_bytes()).hexdigest()
    sig_path = tmp_path / "governance-core.json.sig"
    base = _valid_sig_payload("other-name.json", payload_hash)
    _write_json(sig_path, base)
    mismatch = sig.validate_artifact_signature(
        artifact_path=artifact, sig_path=sig_path, strict=False, workspace_root=tmp_path
    )
    assert mismatch.code == "SIG_SCHEMA_ERROR"

    bad_hash = _valid_sig_payload(artifact.name, "b" * 64)
    _write_json(sig_path, bad_hash)
    mismatch_hash = sig.validate_artifact_signature(
        artifact_path=artifact, sig_path=sig_path, strict=False, workspace_root=tmp_path
    )
    assert mismatch_hash.code == "SIG_PAYLOAD_HASH_MISMATCH"

    ws = tmp_path / "ws"
    trust = ws / ".providence" / "trust"
    trust.mkdir(parents=True)
    keyring = trust / "trusted-keys.json"
    keyring.write_text("{bad-json", encoding="utf-8")
    _write_json(sig_path, _valid_sig_payload(artifact.name, payload_hash))
    bad_keyring = sig.validate_artifact_signature(
        artifact_path=artifact, sig_path=sig_path, strict=True, workspace_root=ws
    )
    assert "could not load trusted keyring" in bad_keyring.reason


def test_validate_compiled_signatures(tmp_path: Path) -> None:
    compiled = tmp_path / "compiled"
    compiled.mkdir()
    (compiled / "governance-core.json").write_text("{}", encoding="utf-8")
    (compiled / "governance-client.json").write_text("{}", encoding="utf-8")
    with patch(
        "providence_runtime.signatures._validate.validate_artifact_signature"
    ) as mocked:
        mocked.return_value = sig._ok()
        results = sig.validate_compiled_signatures(
            compiled, strict=False, workspace_root=tmp_path
        )
        assert len(results) == 2
