from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from providence_cli.services.ask_governance import (
    _compiled_candidates,
    fingerprint_file,
    load_compiled_governance,
    signature_mode,
    try_sdd_compiled_dir,
)


def _mk_compiled_artifact(compiled_dir: Path) -> None:
    compiled_dir.mkdir(parents=True, exist_ok=True)
    payload = {"fingerprint": "abcd1234ef", "mandates": [{"id": "M001"}]}
    (compiled_dir / "governance-core.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def test_compiled_candidates_only_returns_active_dir(tmp_path: Path) -> None:
    active = tmp_path / ".providence" / "compiled" / "active"
    candidates = _compiled_candidates(tmp_path, compiled_active_dir_fn=lambda _: active)
    assert candidates == [active]
    assert (tmp_path / ".providence" / "compiled") not in candidates


def test_load_compiled_governance_does_not_use_legacy_extra_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "providence_cli.services.ask_governance.load_governance_via_runtime",
        lambda *args, **kwargs: None,
    )
    active = tmp_path / "missing-active-dir"
    legacy = tmp_path / ".providence" / "compiled"
    _mk_compiled_artifact(legacy)

    source, fingerprint, mandates_count, *_ = load_compiled_governance(
        tmp_path,
        compiled_active_dir_fn=lambda _: active,
    )
    assert source == "none"
    assert fingerprint == ""
    assert mandates_count == 0


def test_load_compiled_governance_reads_from_active_dir(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(
        "providence_cli.services.ask_governance.load_governance_via_runtime",
        lambda *args, **kwargs: None,
    )
    active = tmp_path / ".providence" / "compiled" / "active"
    _mk_compiled_artifact(active)

    source, fingerprint, mandates_count, *_ = load_compiled_governance(
        tmp_path,
        compiled_active_dir_fn=lambda _: active,
    )
    assert source == "compiled"
    assert fingerprint
    assert mandates_count == 1


# ---------------------------------------------------------------------------
# fingerprint_file
# ---------------------------------------------------------------------------


def test_fingerprint_file_returns_8_char_hex(tmp_path: Path) -> None:
    f = tmp_path / "gov.json"
    f.write_bytes(b"hello")
    fp = fingerprint_file(f)
    assert len(fp) == 8
    assert all(c in "0123456789abcdef" for c in fp)


# ---------------------------------------------------------------------------
# signature_mode
# ---------------------------------------------------------------------------


def test_signature_mode_default_is_warn(monkeypatch) -> None:
    monkeypatch.delenv("SDD_SIGNATURE_MODE", raising=False)
    assert signature_mode() == "warn"


def test_signature_mode_off(monkeypatch) -> None:
    monkeypatch.setenv("SDD_SIGNATURE_MODE", "off")
    assert signature_mode() == "off"


def test_signature_mode_strict(monkeypatch) -> None:
    monkeypatch.setenv("SDD_SIGNATURE_MODE", "strict")
    assert signature_mode() == "strict"


def test_signature_mode_invalid_returns_warn(monkeypatch) -> None:
    monkeypatch.setenv("SDD_SIGNATURE_MODE", "bogus")
    assert signature_mode() == "warn"


# ---------------------------------------------------------------------------
# try_sdd_compiled_dir
# ---------------------------------------------------------------------------


def test_try_sdd_compiled_dir_file_not_exist(tmp_path: Path) -> None:
    result = try_sdd_compiled_dir(tmp_path)
    assert result is None


def test_try_sdd_compiled_dir_data_not_dict(tmp_path: Path) -> None:
    (tmp_path / "governance-core.json").write_text("[]", encoding="utf-8")
    result = try_sdd_compiled_dir(tmp_path)
    assert result is None


def test_try_sdd_compiled_dir_mandates_none_with_logger(tmp_path: Path) -> None:
    logger = MagicMock()
    (tmp_path / "governance-core.json").write_text(
        json.dumps({"other": "key"}), encoding="utf-8"
    )
    result = try_sdd_compiled_dir(tmp_path, logger=logger)
    assert result is None
    logger.debug.assert_called()


def test_try_sdd_compiled_dir_mandates_not_list(tmp_path: Path) -> None:
    (tmp_path / "governance-core.json").write_text(
        json.dumps({"mandates": "bad"}), encoding="utf-8"
    )
    result = try_sdd_compiled_dir(tmp_path)
    assert result is None


def test_try_sdd_compiled_dir_exception_with_logger(tmp_path: Path) -> None:
    logger = MagicMock()
    (tmp_path / "governance-core.json").write_bytes(b"\xff\xfe invalid json")
    result = try_sdd_compiled_dir(tmp_path, logger=logger)
    assert result is None
    logger.debug.assert_called()


def test_try_sdd_compiled_dir_success_with_fingerprint_in_data(tmp_path: Path) -> None:
    payload = {
        "fingerprint": "aabbccdd1122",
        "mandates": [{"id": "M001"}, {"id": "M002"}],
    }
    (tmp_path / "governance-core.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    result = try_sdd_compiled_dir(tmp_path)
    assert result is not None
    source, fp, count = result
    assert source == "compiled"
    assert fp == "aabbccd"[:8] or len(fp) == 8
    assert count == 2


def test_try_sdd_compiled_dir_success_fallback_fingerprint(tmp_path: Path) -> None:
    payload = {"mandates": [{"id": "M001"}]}
    (tmp_path / "governance-core.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    result = try_sdd_compiled_dir(tmp_path)
    assert result is not None
    source, fp, count = result
    assert source == "compiled"
    assert len(fp) == 8
    assert count == 1


def test_try_sdd_compiled_dir_uses_items_key(tmp_path: Path) -> None:
    payload = {"items": [{"id": "M001"}]}
    (tmp_path / "governance-core.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    result = try_sdd_compiled_dir(tmp_path)
    assert result is not None
    assert result[2] == 1
