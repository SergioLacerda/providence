"""Tests for providence_cli.generators._plugins  generate_plugins_registry."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

from tests.helpers.text_io import read_text_utf8

from providence_cli.generators._plugins import (
    _STRATEGIST_ENTRY,
    generate_plugins_registry,
)


class TestStrategistEntry:
    def test_has_required_keys(self) -> None:
        assert _STRATEGIST_ENTRY["id"] == "strategist"
        assert _STRATEGIST_ENTRY["type"] == "analysis_orchestrator"
        assert _STRATEGIST_ENTRY["status"] == "active"

    def test_sdd_injection_block(self) -> None:
        inj = _STRATEGIST_ENTRY["sdd_injection"]
        assert inj["execution_provider"] == "sdd-ask"
        assert inj["approval_gate"] == "required"
        assert ".providence/analysis" in inj["base_path"]

    def test_forbidden_list_present(self) -> None:
        assert isinstance(_STRATEGIST_ENTRY["forbidden"], list)
        assert len(_STRATEGIST_ENTRY["forbidden"]) > 0


class TestGeneratePluginsRegistry:
    def test_creates_registry_yaml(self, tmp_path: Path) -> None:
        result = generate_plugins_registry(str(tmp_path), {})
        registry_path = Path(result["registry_path"])
        assert registry_path.exists()
        assert registry_path.name == "registry.yaml"

    def test_registry_in_sdd_plugins_dir(self, tmp_path: Path) -> None:
        result = generate_plugins_registry(str(tmp_path), {})
        assert ".providence/plugins" in result["registry_path"]

    def test_plugin_count_is_one(self, tmp_path: Path) -> None:
        result = generate_plugins_registry(str(tmp_path), {})
        assert result["plugin_count"] == 1

    def test_registry_yaml_contains_strategist(self, tmp_path: Path) -> None:
        generate_plugins_registry(str(tmp_path), {})
        content = read_text_utf8(tmp_path / ".providence" / "plugins" / "registry.yaml")
        assert "strategist" in content

    def test_registry_yaml_contains_schema_version(self, tmp_path: Path) -> None:
        generate_plugins_registry(str(tmp_path), {})
        content = read_text_utf8(tmp_path / ".providence" / "plugins" / "registry.yaml")
        assert "schema_version" in content

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "c"
        result = generate_plugins_registry(str(nested), {})
        assert Path(result["registry_path"]).exists()

    def test_returns_dict_with_expected_keys(self, tmp_path: Path) -> None:
        result = generate_plugins_registry(str(tmp_path), {})
        assert "registry_path" in result
        assert "plugin_count" in result

    def test_yaml_import_error_returns_fallback(self, tmp_path: Path) -> None:
        with patch.dict(sys.modules, {"yaml": None}):
            result = generate_plugins_registry(str(tmp_path), {})
        assert result["registry_path"] is None
        assert result["plugin_count"] == 0
        assert "error" in result
