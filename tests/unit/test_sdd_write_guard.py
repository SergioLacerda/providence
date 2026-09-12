from __future__ import annotations

from pathlib import Path

import pytest


def _repo_sdd_path() -> Path:
    return Path(__file__).resolve().parents[2] / ".providence"


def test_blocks_write_text_in_repo_sdd() -> None:
    target = _repo_sdd_path() / "runtime" / "guard-write-text.tmp"
    with pytest.raises(
        RuntimeError, match="write to repository .providence is forbidden"
    ):
        target.write_text("forbidden", encoding="utf-8")


def test_blocks_open_write_in_repo_sdd() -> None:
    target = _repo_sdd_path() / "runtime" / "guard-open.tmp"
    with (
        pytest.raises(
            RuntimeError, match="write to repository .providence is forbidden"
        ),
        open(target, "w", encoding="utf-8") as fh,
    ):  # noqa: PTH123
        fh.write("forbidden")


def test_blocks_mkdir_in_repo_sdd() -> None:
    target = _repo_sdd_path() / "runtime" / "guard-mkdir-dir"
    with pytest.raises(
        RuntimeError, match="write to repository .providence is forbidden"
    ):
        target.mkdir(parents=True, exist_ok=True)


def test_blocks_rename_into_repo_sdd(tmp_path: Path) -> None:
    src = tmp_path / "source.txt"
    src.write_text("ok", encoding="utf-8")
    target = _repo_sdd_path() / "runtime" / "guard-rename.txt"
    with pytest.raises(
        RuntimeError, match="write to repository .providence is forbidden"
    ):
        src.rename(target)


def test_allows_write_outside_repo_sdd(tmp_path: Path) -> None:
    target = tmp_path / "outside.txt"
    target.write_text("allowed", encoding="utf-8")
    assert target.read_text(encoding="utf-8") == "allowed"
