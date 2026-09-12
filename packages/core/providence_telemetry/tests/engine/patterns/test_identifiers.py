"""Tests for identifier patterns — Fix 6: Base64 padding regex."""

import re

from providence_telemetry.engine.patterns.identifiers import IDENTIFIER_PATTERNS


def _match_id007(value: str) -> bool:
    return bool(re.match(IDENTIFIER_PATTERNS["ID007"]["regex"], value))


def test_id007_accepts_valid_base64_no_padding() -> None:
    assert _match_id007("SGVsbG8")


def test_id007_accepts_valid_base64_single_padding() -> None:
    assert _match_id007("SGVsbG8=")


def test_id007_accepts_valid_base64_double_padding() -> None:
    assert _match_id007("SGVsbA==")


def test_id007_rejects_excessive_padding() -> None:
    assert not _match_id007("abc========")
    assert not _match_id007("SGVsbG8===")


def test_id007_rejects_invalid_chars() -> None:
    assert not _match_id007("SGVs bG8=")  # space is invalid
