"""Tests for metadata patterns — Fix 4: META002 service name regex."""

import re

from providence_telemetry.engine.patterns.metadata import METADATA_PATTERNS


def _match_meta002(value: str) -> bool:
    return bool(re.match(METADATA_PATTERNS["META002"]["regex"], value))


def test_meta002_matches_unprefixed_service_names() -> None:
    assert _match_meta002("runtime")
    assert _match_meta002("compiler")
    assert _match_meta002("gateway")


def test_meta002_still_matches_prefixed_names() -> None:
    assert _match_meta002("providence-runtime")
    assert _match_meta002("api-gateway")
    assert _match_meta002("service-worker")
    assert _match_meta002("worker-pool")


def test_meta002_rejects_uppercase() -> None:
    assert not _match_meta002("RuntimeService")
    assert not _match_meta002("SDD-RUNTIME")


def test_meta002_rejects_single_char() -> None:
    # Regex requires at least 2 chars: ^[a-z][a-z0-9-]{1,62}$
    assert not _match_meta002("a")


def test_meta002_rejects_leading_hyphen() -> None:
    assert not _match_meta002("-runtime")


def test_meta002_rejects_leading_digit() -> None:
    assert not _match_meta002("1runtime")


def test_meta002_accepts_hyphenated_names() -> None:
    assert _match_meta002("providence-telemetry-engine")
    assert _match_meta002("my-service-v2")
