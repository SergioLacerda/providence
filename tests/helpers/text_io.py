from __future__ import annotations

from pathlib import Path

from providence_core.utils.text_io import read_text_utf8, write_text_utf8


def read_text_utf8_replace(path: Path) -> str:
    """Test helper for permissive reads when fixture files may contain bad bytes."""
    return read_text_utf8(path, errors="replace")


__all__ = ["read_text_utf8", "write_text_utf8", "read_text_utf8_replace"]
