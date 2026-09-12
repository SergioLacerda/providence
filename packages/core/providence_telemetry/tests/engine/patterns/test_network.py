"""Tests for network patterns — Fix 5: IPv4 octet range validation."""

import re

from providence_telemetry.engine.patterns.network import NETWORK_PATTERNS


def _match_net001(value: str) -> bool:
    return bool(re.match(NETWORK_PATTERNS["NET001"]["regex"], value))


def test_net001_accepts_valid_ipv4() -> None:
    assert _match_net001("192.168.1.1")
    assert _match_net001("10.0.0.1")
    assert _match_net001("172.16.254.1")


def test_net001_accepts_boundary_values() -> None:
    assert _match_net001("0.0.0.0")
    assert _match_net001("255.255.255.255")


def test_net001_rejects_invalid_octet_999() -> None:
    assert not _match_net001("999.999.999.999")


def test_net001_rejects_octet_256() -> None:
    assert not _match_net001("256.0.0.1")
    assert not _match_net001("0.0.0.256")


def test_net001_rejects_incomplete_address() -> None:
    assert not _match_net001("192.168.1")
    assert not _match_net001("192.168.1.1.5")


def test_net001_rejects_non_numeric() -> None:
    assert not _match_net001("abc.def.ghi.jkl")
