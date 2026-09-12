from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from providence_cli.services.ask_governance import (
    load_compiled_governance,
    log_sdd_metadata,
    try_sdd_compiled_fallback,
)

# ---------------------------------------------------------------------------
# try_sdd_compiled_fallback
# ---------------------------------------------------------------------------


def test_try_sdd_compiled_fallback_not_dir(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    result = try_sdd_compiled_fallback(missing, "warn")
    assert result is None


def test_try_sdd_compiled_fallback_try_sdd_returns_none(tmp_path: Path) -> None:
    tmp_path.mkdir(exist_ok=True)
    result = try_sdd_compiled_fallback(tmp_path, "warn")
    assert result is None


def test_try_sdd_compiled_fallback_artifact_exists(tmp_path: Path, monkeypatch) -> None:
    payload = {"mandates": [{"id": "M001"}]}
    (tmp_path / "governance-core.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    monkeypatch.setattr(
        "providence_cli.services.ask_governance.validate_signature_for_artifact",
        lambda *a, **kw: (True, False, "", "signed"),
    )
    result = try_sdd_compiled_fallback(tmp_path, "warn")
    assert result is not None
    assert result[0] == "compiled"
    assert result[3] is True


def test_try_sdd_compiled_fallback_strict_no_artifact(tmp_path: Path) -> None:
    payload = {"items": [{"id": "M001"}]}
    (tmp_path / "governance-client.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    result = try_sdd_compiled_fallback(tmp_path, "strict")
    assert result is not None
    assert result[3] is False
    assert "strict mode" in result[5]


def test_try_sdd_compiled_fallback_warn_no_artifact(tmp_path: Path) -> None:
    payload = {"items": [{"id": "M001"}]}
    (tmp_path / "governance-client.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    result = try_sdd_compiled_fallback(tmp_path, "warn")
    assert result is not None
    assert result[4] is True


# ---------------------------------------------------------------------------
# log_sdd_metadata
# ---------------------------------------------------------------------------


def test_log_sdd_metadata_file_not_exists(tmp_path: Path) -> None:
    logger = MagicMock()
    log_sdd_metadata(tmp_path, logger=logger)
    logger.debug.assert_not_called()


def test_log_sdd_metadata_valid_file(tmp_path: Path) -> None:
    logger = MagicMock()
    sdd_dir = tmp_path / ".providence"
    sdd_dir.mkdir()
    (sdd_dir / "metadata.json").write_text(
        json.dumps({"version": "3.0", "item_count": 12}), encoding="utf-8"
    )
    log_sdd_metadata(tmp_path, logger=logger)
    logger.debug.assert_called()


def test_log_sdd_metadata_invalid_json(tmp_path: Path) -> None:
    logger = MagicMock()
    sdd_dir = tmp_path / ".providence"
    sdd_dir.mkdir()
    (sdd_dir / "metadata.json").write_bytes(b"\xff\xfe invalid")
    log_sdd_metadata(tmp_path, logger=logger)
    logger.debug.assert_called()


def test_log_sdd_metadata_no_logger(tmp_path: Path) -> None:
    sdd_dir = tmp_path / ".providence"
    sdd_dir.mkdir()
    (sdd_dir / "metadata.json").write_text(
        json.dumps({"version": "3.0"}), encoding="utf-8"
    )
    log_sdd_metadata(tmp_path, logger=None)


# ---------------------------------------------------------------------------
# load_compiled_governance  runtime_result not None path
# ---------------------------------------------------------------------------


def test_load_compiled_governance_runtime_verified(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "providence_cli.services.ask_governance.load_governance_via_runtime",
        lambda *a, **kw: ("compiled", "abcd1234", 7, "verified", "signed"),
    )
    source, fp, count, authenticated, degraded, reason, trust = (
        load_compiled_governance(
            tmp_path,
            compiled_active_dir_fn=lambda _: tmp_path,
        )
    )
    assert source == "compiled"
    assert authenticated is True
    assert degraded is False


def test_load_compiled_governance_runtime_degraded(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "providence_cli.services.ask_governance.load_governance_via_runtime",
        lambda *a, **kw: ("compiled", "abcd1234", 3, "degraded", "partial"),
    )
    source, fp, count, authenticated, degraded, reason, trust = (
        load_compiled_governance(
            tmp_path,
            compiled_active_dir_fn=lambda _: tmp_path,
        )
    )
    assert degraded is True
    assert authenticated is False
