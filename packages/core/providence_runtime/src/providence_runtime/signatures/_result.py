"""Signature check result type and constructors."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SignatureCheckResult:
    """SignatureCheckResult."""

    code: str
    ok: bool
    blocking: bool
    reason: str
    remediation: str = ""
    trust_source: str = "none"
    deprecation_warning: str = ""


def _remediation_for(code: str) -> str:
    mapping = {
        "SIG_MISSING": "providence governance compile",
        "SIG_PARSE_ERROR": "providence governance compile",
        "SIG_SCHEMA_ERROR": "providence governance compile",
        "SIG_UNTRUSTED_KEY": "refresh trusted keyring and re-run validation",
        "SIG_INVALID": "rebuild signed artifacts with valid signer key",
        "SIG_PAYLOAD_HASH_MISMATCH": "recompile artifacts and investigate tampering",
    }
    return mapping.get(code, "review governance artifact signatures")


def _ok(
    *,
    trust_source: str = "none",
    deprecation_warning: str = "",
) -> SignatureCheckResult:
    return SignatureCheckResult(
        code="OK",
        ok=True,
        blocking=False,
        reason="ok",
        trust_source=trust_source,
        deprecation_warning=deprecation_warning,
    )


def _fail(
    code: str,
    reason: str,
    strict: bool,
    *,
    trust_source: str = "none",
    deprecation_warning: str = "",
) -> SignatureCheckResult:
    return SignatureCheckResult(
        code=code,
        ok=False,
        blocking=bool(strict),
        reason=reason,
        remediation=_remediation_for(code),
        trust_source=trust_source,
        deprecation_warning=deprecation_warning,
    )
