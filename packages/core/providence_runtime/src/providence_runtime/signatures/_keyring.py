"""Trusted keyring loading and ed25519 signature verification."""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast


def _load_json(path: Path) -> dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"expected JSON object in {path}")
    return cast(dict[str, Any], loaded)


def _resolve_keyring_path(
    compiled_dir: Path, *, strict: bool, workspace_root: Path | None = None
) -> tuple[Path | None, str, str]:
    override = os.environ.get("SDD_TRUSTED_KEYRING", "").strip()
    # If workspace_root not provided, try to find it
    if workspace_root is None:
        from providence_core.utils.environment import find_workspace_root

        workspace_root = find_workspace_root(compiled_dir) or Path.cwd()
    canonical = workspace_root / ".providence" / "trust" / "trusted-keys.json"
    if strict:
        if canonical.exists():
            return canonical, "canonical", ""
        return (
            None,
            "none",
            "strict mode requires canonical keyring at .providence/trust/trusted-keys.json",
        )

    candidates: list[tuple[Path, str]] = [
        # Canonical governed path always takes priority.
        (canonical, "canonical"),
    ]
    if override:
        candidates.append((Path(override), "override"))
    for candidate, source in candidates:
        if candidate.exists():
            warning = ""
            if source == "override":
                warning = (
                    "canonical keyring not found at .providence/trust/trusted-keys.json; "
                    "using SDD_TRUSTED_KEYRING override as fallback"
                )
            return candidate, source, warning
    return None, "none", ""


def _resolve_public_key_pem(key_record: dict[str, Any]) -> str | None:
    pem = str(key_record.get("public_key_pem", "")).strip()
    if pem:
        return pem

    b64 = str(key_record.get("public_key", "")).strip()
    if not b64:
        return None
    try:
        decoded = base64.b64decode(b64)
    except Exception:
        return None
    try:
        return decoded.decode("utf-8")
    except Exception:
        return None


def _verify_ed25519_signature(
    *,
    public_key_pem: str,
    message: bytes,
    signature_b64: str,
) -> bool:
    """Verify an Ed25519 signature via the native Go `sdd-compile verify` backend.

    Any failure to decode the signature, load the key, or reach the native
    signing backend is treated as an invalid signature rather than raised,
    matching the previous OpenSSL-backed contract.
    """
    try:
        base64.b64decode(signature_b64)
    except Exception:
        return False

    try:
        from providence_core.utils.compiler_runner import CompilerRunner

        runner = CompilerRunner()
        result = runner.verify(
            public_key_pem=public_key_pem,
            message=message.decode("utf-8"),
            signature_b64=signature_b64,
        )
        return bool(result.get("valid", False))
    except Exception:
        return False


def _is_key_time_valid(record: dict[str, Any]) -> bool:
    now = datetime.now(timezone.utc)
    not_before = str(record.get("not_before", "")).strip()
    not_after = str(record.get("not_after", "")).strip()
    try:
        if not_before:
            nb = datetime.fromisoformat(not_before.replace("Z", "+00:00"))
            if now < nb:
                return False
        if not_after:
            na = datetime.fromisoformat(not_after.replace("Z", "+00:00"))
            if now > na:
                return False
    except Exception:
        return False
    return True
