"""Top-level signature validation entrypoints for compiled artifacts."""

from __future__ import annotations

import hashlib
from pathlib import Path

from ._keyring import (
    _is_key_time_valid,
    _load_json,
    _resolve_keyring_path,
    _resolve_public_key_pem,
    _verify_ed25519_signature,
)
from ._manifest import _validate_manifest_schema
from ._result import SignatureCheckResult, _fail, _ok


def validate_artifact_signature(  # noqa: C901
    *,
    artifact_path: Path,
    sig_path: Path,
    strict: bool = False,
    workspace_root: Path | None = None,
) -> SignatureCheckResult:
    """Validate Artifact Signature."""
    if not sig_path.exists():
        return _fail("SIG_MISSING", f"missing signature file: {sig_path}", strict)

    try:
        sig = _load_json(sig_path)
    except Exception as exc:
        return _fail("SIG_PARSE_ERROR", f"invalid signature json: {exc}", strict)

    schema_error = _validate_manifest_schema(sig)
    if schema_error:
        return _fail("SIG_SCHEMA_ERROR", schema_error, strict)

    expected_name = artifact_path.name
    actual_name = str(sig.get("artifact_name", ""))
    if expected_name != actual_name:
        return _fail(
            "SIG_SCHEMA_ERROR",
            f"artifact_name mismatch: expected {expected_name}, got {actual_name}",
            strict,
        )

    payload_hash = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    signed_hash = str(sig.get("payload_hash", ""))
    if payload_hash != signed_hash:
        return _fail(
            "SIG_PAYLOAD_HASH_MISMATCH",
            "artifact bytes do not match signed payload hash",
            strict,
        )

    keyring_path, trust_source, trust_warning = _resolve_keyring_path(
        artifact_path.parent, strict=strict, workspace_root=workspace_root
    )
    if keyring_path is None:
        reason = "trusted keyring not found"
        if trust_warning:
            reason = trust_warning
        return _fail(
            "SIG_UNTRUSTED_KEY",
            reason,
            strict,
            trust_source=trust_source,
            deprecation_warning=trust_warning,
        )

    try:
        keyring = _load_json(keyring_path)
    except Exception as exc:
        return _fail(
            "SIG_UNTRUSTED_KEY",
            f"could not load trusted keyring: {exc}",
            strict,
            trust_source=trust_source,
            deprecation_warning=trust_warning,
        )

    records = keyring.get("keys", [])
    if not isinstance(records, list):
        return _fail(
            "SIG_UNTRUSTED_KEY",
            "invalid keyring format",
            strict,
            trust_source=trust_source,
            deprecation_warning=trust_warning,
        )

    key_id = str(sig.get("key_id", ""))
    record = next((r for r in records if str(r.get("key_id")) == key_id), None)
    if record is None:
        return _fail(
            "SIG_UNTRUSTED_KEY",
            f"key_id '{key_id}' not trusted",
            strict,
            trust_source=trust_source,
            deprecation_warning=trust_warning,
        )

    status = str(record.get("status", "active")).lower()
    if status == "revoked":
        return _fail(
            "SIG_UNTRUSTED_KEY",
            f"key_id '{key_id}' is revoked",
            strict,
            trust_source=trust_source,
            deprecation_warning=trust_warning,
        )
    if status not in {"active", "deprecated"}:
        return _fail(
            "SIG_UNTRUSTED_KEY",
            f"key_id '{key_id}' invalid status",
            strict,
            trust_source=trust_source,
            deprecation_warning=trust_warning,
        )
    if not _is_key_time_valid(record):
        return _fail(
            "SIG_UNTRUSTED_KEY",
            f"key_id '{key_id}' outside validity window",
            strict,
            trust_source=trust_source,
            deprecation_warning=trust_warning,
        )

    public_key_pem = _resolve_public_key_pem(record)
    if not public_key_pem:
        return _fail(
            "SIG_UNTRUSTED_KEY",
            "trusted key missing public key",
            strict,
            trust_source=trust_source,
            deprecation_warning=trust_warning,
        )

    ok = _verify_ed25519_signature(
        public_key_pem=public_key_pem,
        message=signed_hash.encode("utf-8"),
        signature_b64=str(sig.get("signature", "")),
    )
    if not ok:
        return _fail(
            "SIG_INVALID",
            "ed25519 verification failed",
            strict,
            trust_source=trust_source,
            deprecation_warning=trust_warning,
        )

    return _ok(trust_source=trust_source, deprecation_warning=trust_warning)


def validate_compiled_signatures(
    compiled_dir: Path, *, strict: bool = False, workspace_root: Path | None = None
) -> list[SignatureCheckResult]:
    """Validate signatures for known governance compiled artifacts."""
    targets = [
        compiled_dir / "governance-core.json",
        compiled_dir / "governance-client.json",
    ]
    results: list[SignatureCheckResult] = []
    for artifact in targets:
        if not artifact.exists():
            # Existing structural checks already handle this case.
            continue
        results.append(
            validate_artifact_signature(
                artifact_path=artifact,
                sig_path=artifact.with_suffix(artifact.suffix + ".sig"),
                strict=strict,
                workspace_root=workspace_root,
            )
        )
    return results
