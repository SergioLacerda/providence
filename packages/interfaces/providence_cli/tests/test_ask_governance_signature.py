from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from providence_cli.services.ask_governance import (
    load_governance_via_runtime,
    validate_signature_for_artifact,
)

# ---------------------------------------------------------------------------
# validate_signature_for_artifact
# ---------------------------------------------------------------------------


def test_validate_signature_off_mode(tmp_path: Path) -> None:
    f = tmp_path / "gov.json"
    f.write_bytes(b"data")
    auth, deg, reason, trust = validate_signature_for_artifact(
        f, signature_mode_value="off"
    )
    assert auth is True
    assert deg is False
    assert trust == "none"


def test_validate_signature_exception_strict_mode(tmp_path: Path) -> None:
    f = tmp_path / "gov.json"
    f.write_bytes(b"data")
    import sys

    with patch.dict(
        sys.modules, {"providence_runtime": None, "providence_runtime.signatures": None}
    ):
        auth, deg, reason, trust = validate_signature_for_artifact(
            f, signature_mode_value="strict"
        )
    assert auth is False
    assert deg is False
    assert "signature validation failed" in reason


def test_validate_signature_exception_warn_mode(tmp_path: Path) -> None:
    f = tmp_path / "gov.json"
    f.write_bytes(b"data")
    import sys

    with patch.dict(
        sys.modules, {"providence_runtime": None, "providence_runtime.signatures": None}
    ):
        auth, deg, reason, trust = validate_signature_for_artifact(
            f, signature_mode_value="warn"
        )
    assert auth is False
    assert deg is True
    assert "warn mode" in reason


def test_validate_signature_result_ok(tmp_path: Path) -> None:
    f = tmp_path / "gov.json"
    f.write_bytes(b"data")
    result = MagicMock()
    result.ok = True
    result.blocking = False
    result.deprecation_warning = ""
    result.trust_source = "signed"
    with patch(
        "providence_cli.services.ask_governance.validate_signature_for_artifact"
    ) as mp:
        mp.return_value = (True, False, "", "signed")
        auth, deg, reason, trust = mp(f, signature_mode_value="warn")
    assert auth is True


def test_validate_signature_result_ok_with_deprecation(tmp_path: Path) -> None:
    f = tmp_path / "gov.json"
    f.write_bytes(b"data")
    import sys

    result = MagicMock()
    result.ok = True
    result.blocking = False
    result.deprecation_warning = "old key"
    result.trust_source = "signed"
    mock_validate = MagicMock(return_value=result)
    mock_signatures_module = MagicMock(validate_artifact_signature=mock_validate)
    with patch.dict(
        sys.modules,
        {
            "providence_runtime": MagicMock(),
            "providence_runtime.signatures": mock_signatures_module,
        },
    ):
        auth, deg, reason, trust = validate_signature_for_artifact(
            f, signature_mode_value="warn"
        )
    assert auth is True


def test_validate_signature_result_blocking(tmp_path: Path) -> None:
    f = tmp_path / "gov.json"
    f.write_bytes(b"data")
    result = MagicMock()
    result.ok = False
    result.blocking = True
    result.code = "ERR001"
    result.reason = "expired"
    result.trust_source = "none"
    mock_validate = MagicMock(return_value=result)
    with patch(
        "providence_runtime.signatures.validate_artifact_signature", mock_validate
    ):
        auth, deg, reason, trust = validate_signature_for_artifact(
            f, signature_mode_value="warn"
        )
    assert auth is False
    assert deg is False
    assert "ERR001" in reason


def test_validate_signature_result_non_blocking(tmp_path: Path) -> None:
    f = tmp_path / "gov.json"
    f.write_bytes(b"data")
    result = MagicMock()
    result.ok = False
    result.blocking = False
    result.code = "WARN001"
    result.reason = "degraded key"
    result.trust_source = "partial"
    mock_validate = MagicMock(return_value=result)
    with patch(
        "providence_runtime.signatures.validate_artifact_signature", mock_validate
    ):
        auth, deg, reason, trust = validate_signature_for_artifact(
            f, signature_mode_value="warn"
        )
    assert auth is False
    assert deg is True


# ---------------------------------------------------------------------------
# load_governance_via_runtime
# ---------------------------------------------------------------------------


def test_load_governance_via_runtime_dir_not_dir(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    result = load_governance_via_runtime(
        tmp_path,
        compiled_active_dir_fn=lambda _: missing,
    )
    assert result is None


def test_load_governance_via_runtime_exception_returns_none(tmp_path: Path) -> None:
    logger = MagicMock()
    import sys

    with patch.dict(sys.modules, {"providence_runtime": None}):
        result = load_governance_via_runtime(
            tmp_path,
            compiled_active_dir_fn=lambda _: tmp_path,
            logger=logger,
        )
    assert result is None
    logger.debug.assert_called()


def test_load_governance_via_runtime_injector_loads(tmp_path: Path) -> None:
    injector_result = MagicMock()
    injector_result.loaded = True
    injector_result.artifact_fingerprint = "deadbeef1234"
    injector_result.total_loaded = 5
    injector_result.auth_state = "verified"
    injector_result.trust_source = "signed"
    injector = MagicMock()
    injector.inject_from_path.return_value = injector_result

    import sys

    mock_providence_runtime = MagicMock()
    mock_providence_runtime.GovernanceInjector.return_value = injector
    with patch.dict(sys.modules, {"providence_runtime": mock_providence_runtime}):
        result = load_governance_via_runtime(
            tmp_path,
            compiled_active_dir_fn=lambda _: tmp_path,
        )
    assert result is not None
    source, fp, count, auth_state, trust_source = result
    assert source == "compiled"
    assert count == 5
