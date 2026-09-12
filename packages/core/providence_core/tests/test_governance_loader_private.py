from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import msgpack
import pytest

from providence_core.utils.loader import GovernanceLoader


def _write_msgpack(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(msgpack.packb(payload, use_bin_type=True))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _make_compiled_dir(tmp_path: Path) -> Path:
    compiled = tmp_path / "compiled"
    _write_msgpack(
        compiled / "governance-core.compiled.msgpack",
        {"items": [{"id": "M1", "type": "MANDATE"}]},
    )
    _write_msgpack(
        compiled / "governance-client-template.compiled.msgpack",
        {"items": [{"id": "G1", "type": "GUIDELINE"}]},
    )
    _write_json(compiled / "metadata-core.json", {"fingerprint": "core-fp"})
    _write_json(
        compiled / "metadata-client-template.json",
        {"fingerprint": "client-fp", "fingerprint_salt": "core-fp"},
    )
    return compiled


def test_init_uses_master_compiled_for_master_profile(tmp_path: Path) -> None:
    paths = {
        "master_compiled": tmp_path / "master",
        "client_compiled": tmp_path / "client",
    }
    with (
        patch("providence_core.utils.loader.get_sdd_paths", return_value=paths),
        patch("providence_core.utils.loader.resolve_profile") as mock_profile,
    ):
        mock_profile.return_value.type = "master"
        loader = GovernanceLoader()
    assert loader.compiled_dir == paths["master_compiled"]


def test_init_uses_client_compiled_for_client_profile(tmp_path: Path) -> None:
    paths = {
        "master_compiled": tmp_path / "master",
        "client_compiled": tmp_path / "client",
    }
    with (
        patch("providence_core.utils.loader.get_sdd_paths", return_value=paths),
        patch("providence_core.utils.loader.resolve_profile") as mock_profile,
    ):
        mock_profile.return_value.type = "client"
        loader = GovernanceLoader()
    assert loader.compiled_dir == paths["client_compiled"]


def test_init_falls_back_to_master_compiled_on_profile_error(tmp_path: Path) -> None:
    paths = {
        "master_compiled": tmp_path / "master",
        "client_compiled": tmp_path / "client",
    }
    with (
        patch("providence_core.utils.loader.get_sdd_paths", return_value=paths),
        patch(
            "providence_core.utils.loader.resolve_profile",
            side_effect=RuntimeError("boom"),
        ),
    ):
        loader = GovernanceLoader()
    assert loader.compiled_dir == paths["master_compiled"]


def test_load_core_reads_msgpack_and_metadata(tmp_path: Path) -> None:
    compiled = _make_compiled_dir(tmp_path)
    loader = GovernanceLoader(str(compiled))

    data = loader.load_core()

    assert data["items"][0]["id"] == "M1"
    assert loader.packages_metadata == {"fingerprint": "core-fp"}


def test_load_core_raises_when_missing(tmp_path: Path) -> None:
    loader = GovernanceLoader(str(tmp_path / "missing"))
    with pytest.raises(FileNotFoundError, match="Core msgpack not found"):
        loader.load_core()


def test_load_client_falls_back_to_compiled_dir_when_override_missing(
    tmp_path: Path,
) -> None:
    compiled = _make_compiled_dir(tmp_path)
    loader = GovernanceLoader(str(compiled))

    data = loader.load_client(compiled / "other")

    assert data["items"][0]["id"] == "G1"
    assert loader._client_metadata == {
        "fingerprint": "client-fp",
        "fingerprint_salt": "core-fp",
    }


def test_load_client_raises_when_missing_everywhere(tmp_path: Path) -> None:
    compiled = tmp_path / "compiled"
    compiled.mkdir()
    loader = GovernanceLoader(str(compiled))
    with pytest.raises(FileNotFoundError, match="Client msgpack not found"):
        loader.load_client(compiled / "other")


def test_get_all_items_and_filter_by_type(tmp_path: Path) -> None:
    compiled = _make_compiled_dir(tmp_path)
    loader = GovernanceLoader(str(compiled))

    assert [item["id"] for item in loader.get_all_items()] == ["M1", "G1"]
    assert [item["id"] for item in loader.get_items_by_type("guideline")] == ["G1"]


def test_load_compiled_binary_reads_msgpack(tmp_path: Path) -> None:
    binary = tmp_path / "payload.msgpack"
    _write_msgpack(binary, {"ok": True})
    loader = GovernanceLoader(str(tmp_path))
    assert loader.load_compiled_binary(binary) == {"ok": True}


def test_load_compiled_binary_raises_when_missing(tmp_path: Path) -> None:
    loader = GovernanceLoader(str(tmp_path))
    with pytest.raises(FileNotFoundError, match="Binary file not found"):
        loader.load_compiled_binary(tmp_path / "missing.msgpack")


def test_get_fingerprints_loads_metadata_on_demand(tmp_path: Path) -> None:
    compiled = _make_compiled_dir(tmp_path)
    loader = GovernanceLoader(str(compiled))
    assert loader.get_fingerprints() == {
        "core": "core-fp",
        "client": "client-fp",
        "salt": "core-fp",
    }


def test_load_all_returns_summary(tmp_path: Path) -> None:
    compiled = _make_compiled_dir(tmp_path)
    loader = GovernanceLoader(str(compiled))

    summary = loader.load_all()

    assert summary == {
        "status": "loaded",
        "core_items": 1,
        "client_items": 1,
        "core_fingerprint": "core-fp",
        "client_fingerprint": "client-fp",
        "context_source": "msgpack",
    }


def test_load_all_raises_on_integrity_failure(tmp_path: Path) -> None:
    compiled = _make_compiled_dir(tmp_path)
    loader = GovernanceLoader(str(compiled))
    with (
        patch.object(loader, "_validate_integrity", return_value=False),
        pytest.raises(RuntimeError, match="Governance integrity validation failed"),
    ):
        loader.load_all()


def test_validate_integrity_covers_false_branches(tmp_path: Path) -> None:
    compiled = _make_compiled_dir(tmp_path)
    loader = GovernanceLoader(str(compiled))
    loader.packages_data = {"items": []}
    loader._client_data = {"items": [{"id": "G1"}]}
    loader.packages_metadata = {"fingerprint": ""}
    loader._client_metadata = {"fingerprint": "client-fp", "fingerprint_salt": "bad"}

    assert loader._validate_integrity() is False
