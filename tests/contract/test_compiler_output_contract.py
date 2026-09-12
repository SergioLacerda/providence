"""Contract tests for compiler I/O artifact format.

These tests run against the current Python GovernanceCompiler output and will
continue to run against Go sdd-compile binary output after Phase 7 deletion.
All tests verify format and structural contracts defined in
docs/spec/canonical/specifications/compiler_io_contract.md.

To run:
    uv run python -m pytest tests/contract/test_compiler_output_contract.py -v
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import msgpack
import pytest

from providence_cli.utils.providence_authority import compiled_active_dir

_FINGERPRINT_RE = re.compile(r"^[0-9a-f]{64}$")
_ITEM_ID_RE = re.compile(r"^[A-Z]\d{2,3}$")


@pytest.fixture(scope="module")
def compiled_dir() -> Path:
    return compiled_active_dir()


def test_governance_core_json_schema(compiled_dir: Path) -> None:
    data = json.loads(
        (compiled_dir / "governance-core.json").read_text(encoding="utf-8")
    )
    assert "category" in data
    assert "version" in data
    assert "fingerprint" in data
    assert "items" in data
    assert isinstance(data["items"], list)
    assert len(data["items"]) >= 1
    for item in data["items"]:
        assert "id" in item, f"item missing 'id': {item}"
        assert "type" in item, f"item missing 'type': {item}"
        assert "title" in item, f"item missing 'title': {item}"
        assert _ITEM_ID_RE.match(str(item["id"])), (
            f"item id {item['id']!r} does not match ^[A-Z]\\d{{2,3}}$"
        )


def test_governance_core_msgpack_readable(compiled_dir: Path) -> None:
    raw = (compiled_dir / "governance-core.compiled.msgpack").read_bytes()
    assert len(raw) > 0, "governance-core.compiled.msgpack must not be empty"
    data = msgpack.unpackb(raw, raw=False)
    assert isinstance(data, dict), "msgpack must decode to a dict"
    assert "fingerprint" in data
    assert "items" in data


def test_metadata_core_schema(compiled_dir: Path) -> None:
    meta = json.loads((compiled_dir / "metadata-core.json").read_text(encoding="utf-8"))
    for field in ("version", "type", "generated_at", "fingerprint", "item_count"):
        assert field in meta, f"metadata-core.json missing required field: {field}"
    assert _FINGERPRINT_RE.match(str(meta["fingerprint"])), (
        f"metadata-core fingerprint {meta['fingerprint']!r} is not 64 lowercase hex chars"
    )
    assert isinstance(meta["item_count"], int)
    assert meta["item_count"] >= 1


def test_fingerprint_format_64_hex_chars(compiled_dir: Path) -> None:
    core = json.loads(
        (compiled_dir / "governance-core.json").read_text(encoding="utf-8")
    )
    assert _FINGERPRINT_RE.match(str(core["fingerprint"])), (
        f"Core fingerprint {core['fingerprint']!r} is not 64 lowercase hex chars"
    )
    client = json.loads(
        (compiled_dir / "governance-client.json").read_text(encoding="utf-8")
    )
    assert _FINGERPRINT_RE.match(str(client["fingerprint"])), (
        f"Client fingerprint {client['fingerprint']!r} is not 64 lowercase hex chars"
    )


def test_msgpack_no_magic_header(compiled_dir: Path) -> None:
    for name in (
        "governance-core.compiled.msgpack",
        "governance-client-template.compiled.msgpack",
    ):
        raw = (compiled_dir / name).read_bytes()
        assert len(raw) > 0, f"{name} must not be empty"
        data = msgpack.unpackb(raw, raw=False)
        assert isinstance(data, dict), (
            f"{name}: plain msgpack must decode to dict, got {type(data).__name__}"
        )


def test_client_fingerprint_salt_equals_core_fingerprint(compiled_dir: Path) -> None:
    core = json.loads(
        (compiled_dir / "governance-core.json").read_text(encoding="utf-8")
    )
    client = json.loads(
        (compiled_dir / "governance-client.json").read_text(encoding="utf-8")
    )
    assert "fingerprint_core_salt" in client, (
        "governance-client.json must contain 'fingerprint_core_salt'"
    )
    assert client["fingerprint_core_salt"] == core["fingerprint"], (
        "client fingerprint_core_salt must equal core fingerprint"
    )


def test_metadata_fingerprint_matches_json(compiled_dir: Path) -> None:
    core_json = json.loads(
        (compiled_dir / "governance-core.json").read_text(encoding="utf-8")
    )
    meta = json.loads((compiled_dir / "metadata-core.json").read_text(encoding="utf-8"))
    assert meta["fingerprint"] == core_json["fingerprint"], (
        "metadata-core.json fingerprint must match governance-core.json fingerprint"
    )


def test_core_and_client_fingerprints_differ(compiled_dir: Path) -> None:
    core = json.loads(
        (compiled_dir / "governance-core.json").read_text(encoding="utf-8")
    )
    client = json.loads(
        (compiled_dir / "governance-client.json").read_text(encoding="utf-8")
    )
    assert core["fingerprint"] != client["fingerprint"], (
        "Core and client fingerprints must be different values"
    )


def test_governance_client_json_schema(compiled_dir: Path) -> None:
    data = json.loads(
        (compiled_dir / "governance-client.json").read_text(encoding="utf-8")
    )
    for field in (
        "category",
        "version",
        "fingerprint",
        "fingerprint_core_salt",
        "items",
    ):
        assert field in data, f"governance-client.json missing required field: {field}"
    assert isinstance(data["items"], list)


def test_governance_client_msgpack_readable(compiled_dir: Path) -> None:
    raw = (compiled_dir / "governance-client-template.compiled.msgpack").read_bytes()
    assert len(raw) > 0
    data = msgpack.unpackb(raw, raw=False)
    assert isinstance(data, dict), "client msgpack must decode to a dict"
    assert "fingerprint" in data
    assert "items" in data
