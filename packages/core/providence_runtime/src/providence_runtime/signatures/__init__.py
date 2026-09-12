"""Signature validation for compiled governance artifacts.

This module provides a deterministic verification contract with canonical
result codes while keeping backward compatibility for unsigned legacy artifacts.
"""

from __future__ import annotations

from ._keyring import (
    _is_key_time_valid,
    _load_json,
    _resolve_keyring_path,
    _resolve_public_key_pem,
    _verify_ed25519_signature,
)
from ._manifest import _HEX64_PATTERN, _KEY_ID_PATTERN, _validate_manifest_schema
from ._result import SignatureCheckResult, _fail, _ok, _remediation_for
from ._validate import validate_artifact_signature, validate_compiled_signatures

__all__ = [
    "_HEX64_PATTERN",
    "_KEY_ID_PATTERN",
    "SignatureCheckResult",
    "_fail",
    "_is_key_time_valid",
    "_load_json",
    "_ok",
    "_remediation_for",
    "_resolve_keyring_path",
    "_resolve_public_key_pem",
    "_validate_manifest_schema",
    "_verify_ed25519_signature",
    "validate_artifact_signature",
    "validate_compiled_signatures",
]
