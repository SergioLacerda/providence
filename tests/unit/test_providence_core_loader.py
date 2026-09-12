"""Unit tests for providence_core.utils.loader.GovernanceLoader and TemplateGenerator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import msgpack
import pytest

pytestmark = pytest.mark.unit


def _write_msgpack(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(msgpack.packb(data, use_bin_type=True))


def _write_metadata(path: Path, fingerprint: str = "abc123", salt: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = {"fingerprint": fingerprint}
    if salt:
        meta["fingerprint_salt"] = salt
    path.write_text(json.dumps(meta), encoding="utf-8")


def _setup_compiled_dir(
    tmp_path: Path,
    core_items: list[Any] | None = None,
    core_fp: str = "core_fp_abcdef1234567890",
    client_fp: str = "client_fp_xyz0987654",
) -> Path:
    """Create a complete compiled dir with core + client artifacts."""
    compiled_dir = tmp_path / "compiled"
    compiled_dir.mkdir(parents=True, exist_ok=True)

    core_data = {
        "items": core_items or [{"id": "M001", "type": "MANDATE"}],
        "version": "3.0",
    }
    _write_msgpack(compiled_dir / "governance-core.compiled.msgpack", core_data)
    _write_metadata(
        compiled_dir / "metadata-core.json", fingerprint=core_fp, salt=core_fp
    )

    client_data = {"items": [], "version": "3.0"}
    _write_msgpack(
        compiled_dir / "governance-client-template.compiled.msgpack", client_data
    )
    _write_metadata(
        compiled_dir / "metadata-client-template.json",
        fingerprint=client_fp,
        salt=core_fp,
    )

    return compiled_dir


def _make_loader(compiled_dir: Path) -> Any:
    from providence_core.utils.loader import GovernanceLoader

    mock_paths = {
        "master_compiled": compiled_dir,
        "client_compiled": compiled_dir,
    }
    with patch("providence_core.utils.loader.get_sdd_paths", return_value=mock_paths):
        loader = GovernanceLoader(compiled_dir=str(compiled_dir))
    return loader


# ---------------------------------------------------------------------------
# GovernanceLoader.load_core
# ---------------------------------------------------------------------------


class TestLoadCore:
    def test_raises_file_not_found_when_no_msgpack(self, tmp_path: Path) -> None:
        from providence_core.utils.loader import GovernanceLoader

        loader = GovernanceLoader(compiled_dir=str(tmp_path))
        with pytest.raises(FileNotFoundError, match="Core msgpack not found"):
            loader.load_core()

    def test_loads_core_data(self, tmp_path: Path) -> None:
        compiled_dir = _setup_compiled_dir(tmp_path)
        loader = _make_loader(compiled_dir)
        result = loader.load_core()
        assert "items" in result
        assert loader.packages_data is not None
        assert loader._core_context_source == "msgpack"

    def test_loads_core_metadata(self, tmp_path: Path) -> None:
        compiled_dir = _setup_compiled_dir(tmp_path)
        loader = _make_loader(compiled_dir)
        loader.load_core()
        assert loader.packages_metadata is not None
        assert "fingerprint" in loader.packages_metadata


# ---------------------------------------------------------------------------
# GovernanceLoader.load_client
# ---------------------------------------------------------------------------


class TestLoadClient:
    def test_raises_file_not_found_when_no_msgpack(self, tmp_path: Path) -> None:
        from providence_core.utils.loader import GovernanceLoader

        loader = GovernanceLoader(compiled_dir=str(tmp_path))
        with pytest.raises(FileNotFoundError, match="Client msgpack not found"):
            loader.load_client()

    def test_loads_client_data(self, tmp_path: Path) -> None:
        compiled_dir = _setup_compiled_dir(tmp_path)
        loader = _make_loader(compiled_dir)
        result = loader.load_client()
        assert "items" in result
        assert loader._client_data is not None

    def test_loads_client_metadata(self, tmp_path: Path) -> None:
        compiled_dir = _setup_compiled_dir(tmp_path)
        loader = _make_loader(compiled_dir)
        loader.load_client()
        assert loader._client_metadata is not None


# ---------------------------------------------------------------------------
# GovernanceLoader.load_compiled_binary
# ---------------------------------------------------------------------------


class TestLoadCompiledBinary:
    def test_raises_when_file_not_found(self, tmp_path: Path) -> None:
        from providence_core.utils.loader import GovernanceLoader

        loader = GovernanceLoader(compiled_dir=str(tmp_path))
        with pytest.raises(FileNotFoundError):
            loader.load_compiled_binary(tmp_path / "nonexistent.msgpack")

    def test_loads_binary_file(self, tmp_path: Path) -> None:
        from providence_core.utils.loader import GovernanceLoader

        data = {"items": [{"id": "M001"}]}
        binary_file = tmp_path / "test.msgpack"
        _write_msgpack(binary_file, data)

        loader = GovernanceLoader(compiled_dir=str(tmp_path))
        result = loader.load_compiled_binary(binary_file)
        assert result["items"][0]["id"] == "M001"


# ---------------------------------------------------------------------------
# GovernanceLoader.get_all_items / get_items_by_type
# ---------------------------------------------------------------------------


class TestGetItems:
    def test_get_all_items_merges_core_and_client(self, tmp_path: Path) -> None:
        compiled_dir = tmp_path / "compiled"
        compiled_dir.mkdir(parents=True)

        core_data = {"items": [{"id": "M001", "type": "MANDATE"}], "version": "3.0"}
        client_data = {"items": [{"id": "G001", "type": "GUIDELINE"}], "version": "3.0"}
        _write_msgpack(compiled_dir / "governance-core.compiled.msgpack", core_data)
        _write_metadata(compiled_dir / "metadata-core.json", "fp1", "fp1")
        _write_msgpack(
            compiled_dir / "governance-client-template.compiled.msgpack", client_data
        )
        _write_metadata(compiled_dir / "metadata-client-template.json", "fp2", "fp1")

        loader = _make_loader(compiled_dir)
        loader.load_core()
        loader.load_client()
        items = loader.get_all_items()
        ids = [i["id"] for i in items]
        assert "M001" in ids
        assert "G001" in ids

    def test_get_items_by_type_filters_correctly(self, tmp_path: Path) -> None:
        compiled_dir = _setup_compiled_dir(
            tmp_path,
            core_items=[
                {"id": "M001", "type": "MANDATE"},
                {"id": "G001", "type": "GUIDELINE"},
            ],
        )
        loader = _make_loader(compiled_dir)
        loader.load_core()
        loader.load_client()
        mandates = loader.get_items_by_type("MANDATE")
        assert all(i["type"] == "MANDATE" for i in mandates)
        assert any(i["id"] == "M001" for i in mandates)


# ---------------------------------------------------------------------------
# GovernanceLoader.get_fingerprints
# ---------------------------------------------------------------------------


class TestGetFingerprints:
    def test_returns_core_and_client_fingerprints(self, tmp_path: Path) -> None:
        compiled_dir = _setup_compiled_dir(
            tmp_path, core_fp="core_fp_abc", client_fp="client_fp_xyz"
        )
        loader = _make_loader(compiled_dir)
        loader.load_core()
        loader.load_client()
        fps = loader.get_fingerprints()
        assert fps["core"] == "core_fp_abc"
        assert fps["client"] == "client_fp_xyz"


# ---------------------------------------------------------------------------
# GovernanceLoader._require_* lazy loaders
# ---------------------------------------------------------------------------


class TestRequireLoaders:
    def test_require_core_data_triggers_load_core(self, tmp_path: Path) -> None:
        compiled_dir = _setup_compiled_dir(tmp_path)
        loader = _make_loader(compiled_dir)
        assert loader.packages_data is None
        data = loader._require_core_data()
        assert data is not None
        assert loader.packages_data is not None

    def test_require_client_data_triggers_load_client(self, tmp_path: Path) -> None:
        compiled_dir = _setup_compiled_dir(tmp_path)
        loader = _make_loader(compiled_dir)
        assert loader._client_data is None
        data = loader._require_client_data()
        assert data is not None

    def test_require_core_metadata_triggers_load(self, tmp_path: Path) -> None:
        compiled_dir = _setup_compiled_dir(tmp_path)
        loader = _make_loader(compiled_dir)
        meta = loader._require_core_metadata()
        assert "fingerprint" in meta

    def test_require_client_metadata_triggers_load(self, tmp_path: Path) -> None:
        compiled_dir = _setup_compiled_dir(tmp_path)
        loader = _make_loader(compiled_dir)
        meta = loader._require_client_metadata()
        assert "fingerprint" in meta


# ---------------------------------------------------------------------------
# GovernanceLoader.load_all
# ---------------------------------------------------------------------------


class TestLoadAll:
    def test_load_all_returns_status_loaded(self, tmp_path: Path) -> None:
        compiled_dir = _setup_compiled_dir(tmp_path)
        loader = _make_loader(compiled_dir)
        result = loader.load_all()
        assert result["status"] == "loaded"
        assert "core_fingerprint" in result
        assert "client_fingerprint" in result

    def test_load_all_raises_on_integrity_failure(self, tmp_path: Path) -> None:
        # Create files where core and client fingerprints are the same (fails integrity)
        # and no salt mismatch => _validate_integrity() would fail
        compiled_dir = tmp_path / "compiled"
        compiled_dir.mkdir(parents=True)

        same_fp = "same_fp_123"
        core_data = {"items": [], "version": "3.0"}  # 0 items → fails integrity
        _write_msgpack(compiled_dir / "governance-core.compiled.msgpack", core_data)
        _write_metadata(
            compiled_dir / "metadata-core.json", fingerprint=same_fp, salt=same_fp
        )
        client_data = {"items": [], "version": "3.0"}
        _write_msgpack(
            compiled_dir / "governance-client-template.compiled.msgpack", client_data
        )
        _write_metadata(
            compiled_dir / "metadata-client-template.json",
            fingerprint=same_fp,
            salt=same_fp,
        )

        loader = _make_loader(compiled_dir)
        with pytest.raises(RuntimeError, match="integrity"):
            loader.load_all()


# ---------------------------------------------------------------------------
# TemplateGenerator
# ---------------------------------------------------------------------------


class TestTemplateGenerator:
    def test_generates_basic_template(self, tmp_path: Path) -> None:
        from providence_core.utils.loader import GovernanceLoader, TemplateGenerator

        compiled_dir = tmp_path / "compiled"
        client_data = {
            "items": [
                {
                    "id": "G001",
                    "type": "GUIDELINE",
                    "title": "Guide 1",
                    "customizable": True,
                }
            ],
            "version": "3.0",
        }
        _write_msgpack(
            compiled_dir / "governance-client-template.compiled.msgpack", client_data
        )
        _write_metadata(compiled_dir / "metadata-client-template.json", "fp2")

        loader = GovernanceLoader(compiled_dir=str(compiled_dir))
        gen = TemplateGenerator(loader)
        template = gen.generate_basic_template()

        assert template["version"] == "3.0"
        assert template["type"] == "customization-template"
        assert "customizations" in template
        assert len(template["customizations"]) == 1
        assert template["customizations"][0]["id"] == "G001"

    def test_prepare_items_maps_fields(self, tmp_path: Path) -> None:
        from providence_core.utils.loader import GovernanceLoader, TemplateGenerator

        compiled_dir = tmp_path / "compiled"
        _write_msgpack(
            compiled_dir / "governance-client-template.compiled.msgpack", {"items": []}
        )
        _write_metadata(compiled_dir / "metadata-client-template.json", "fp2")

        loader = GovernanceLoader(compiled_dir=str(compiled_dir))
        gen = TemplateGenerator(loader)
        items = [{"id": "X001", "title": "X", "type": "MANDATE", "customizable": True}]
        result = gen._prepare_items(items)
        assert result[0]["id"] == "X001"
        assert result[0]["customizable"] is True
