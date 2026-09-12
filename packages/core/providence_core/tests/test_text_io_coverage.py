"""Coverage tests for providence_core.utils.text_io."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from providence_core.utils.text_io import (
    read_json_utf8,
    read_text_utf8,
    write_json_utf8,
    write_text_utf8,
)


def test_write_and_read_text_utf8(tmp_path: Path) -> None:
    p = tmp_path / "out.txt"
    write_text_utf8(p, "hello world")
    assert read_text_utf8(p) == "hello world"


def test_write_and_read_json_utf8(tmp_path: Path) -> None:
    p = tmp_path / "data.json"
    write_json_utf8(p, {"key": "value"})
    result = read_json_utf8(p)
    assert result == {"key": "value"}


def test_write_json_utf8_custom_indent(tmp_path: Path) -> None:
    p = tmp_path / "data.json"
    write_json_utf8(p, {"a": 1}, indent=4)
    raw = p.read_text(encoding="utf-8")
    assert "    " in raw  # 4-space indent present


def test_read_json_utf8_raises_for_non_dict(tmp_path: Path) -> None:
    p = tmp_path / "list.json"
    p.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    with pytest.raises(ValueError, match="Expected JSON object"):
        read_json_utf8(p)


def test_read_text_utf8_with_replace_errors(tmp_path: Path) -> None:
    p = tmp_path / "bad.txt"
    p.write_bytes(b"hello \xff world")
    result = read_text_utf8(p, errors="replace")
    assert "hello" in result
