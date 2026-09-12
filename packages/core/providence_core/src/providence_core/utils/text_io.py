"""Text Io."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_text_utf8(path: Path, errors: str = "strict") -> str:
    """Read UTF-8 text deterministically across platforms."""
    return path.read_text(encoding="utf-8", errors=errors)


def write_text_utf8(path: Path, content: str) -> None:
    """Write UTF-8 text deterministically across platforms."""
    path.write_text(content, encoding="utf-8")


def read_json_utf8(path: Path, errors: str = "strict") -> dict[str, Any]:
    """Read Json Utf8."""
    payload = json.loads(read_text_utf8(path, errors=errors))
    if not isinstance(payload, dict):
        raise ValueError(
            f"Expected JSON object in {path}, got {type(payload).__name__}"
        )
    return payload


def write_json_utf8(path: Path, payload: dict[str, Any], *, indent: int = 2) -> None:
    """Write Json Utf8."""
    write_text_utf8(path, json.dumps(payload, indent=indent, ensure_ascii=False))
