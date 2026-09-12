from __future__ import annotations

from pathlib import Path

import pytest

from providence_cli.extensions.framework.extension_framework import (
    BaseExtension,
    Category,
    CustomGuideline,
    CustomMandate,
    ExtensionMetadata,
    ExtensionRegistry,
    get_extension,
    get_registry,
    register_extension,
)
from providence_cli.extensions.framework.plugin_loader import (
    PluginLoader,
    load_all_plugins,
)


class _ValidExtension(BaseExtension):
    metadata = ExtensionMetadata("Test", "1.0", "Author", "Desc", "test-domain")
    mandates = [CustomMandate("M001", "HARD", "Title", "Desc", category="general")]
    guidelines = [CustomGuideline("G001", "SOFT", "Guide", category="testing")]

    def initialize(self) -> None:
        self.initialized = True

    def validate(self) -> list[str]:
        return []


class _InvalidExtension(BaseExtension):
    metadata = ExtensionMetadata("Invalid", "1.0", "Author", "Desc", "invalid-domain")

    def initialize(self) -> None:
        pass

    def validate(self) -> list[str]:
        return ["bad config"]


def test_custom_mandate_and_guideline_validation_and_dicts() -> None:
    mandate = CustomMandate(
        "M001", "HARD", "Title", "Desc", category=Category.GENERAL.value
    )
    guideline = CustomGuideline(
        "G001", "SOFT", "Guide", category=Category.TESTING.value
    )
    assert mandate.validate() == []
    assert guideline.validate() == []
    assert mandate.to_dict()["id"] == "M001"
    assert guideline.to_dict()["id"] == "G001"


def test_custom_items_report_validation_errors() -> None:
    mandate = CustomMandate("", "BAD", "", "", category="oops")
    guideline = CustomGuideline("", "BAD", "", category="oops")
    assert len(mandate.validate()) >= 4
    assert len(guideline.validate()) >= 4


def test_extension_metadata_and_base_extension_dict() -> None:
    ext = _ValidExtension()
    data = ext.to_dict()
    assert data["metadata"]["domain"] == "test-domain"
    assert data["mandates"][0]["id"] == "M001"
    assert data["guidelines"][0]["id"] == "G001"


def test_registry_registers_valid_extensions_and_tracks_invalid_ones() -> None:
    registry = ExtensionRegistry()
    assert registry.register("test-domain", _ValidExtension()) is True
    assert registry.register("invalid-domain", _InvalidExtension()) is False
    assert registry.get("test-domain") is not None
    assert registry.get_mandates("test-domain")[0].id == "M001"
    assert registry.get_guidelines("test-domain")[0].id == "G001"
    stats = registry.get_stats()
    assert stats["total_extensions"] == 1
    assert stats["errors"] == 1


def test_global_registry_helpers_register_and_lookup() -> None:
    registry = get_registry()
    registry.extensions.clear()
    registry.errors.clear()
    assert register_extension("test-domain", _ValidExtension()) is True
    assert get_extension("test-domain") is not None


def test_plugin_loader_discover_and_error_paths(tmp_path: Path) -> None:
    root = tmp_path / "plugins"
    loader = PluginLoader()
    loader.plugins_dir = root
    assert loader.discover_plugins() == []
    assert loader.load_errors

    plugin_dir = root / "demo"
    plugin_dir.mkdir(parents=True)
    assert loader.load_plugin(plugin_dir) is None


def test_plugin_loader_loads_valid_plugin_and_registers(tmp_path: Path) -> None:
    root = tmp_path / "plugins"
    plugin_dir = root / "demo"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "__init__.py").write_text(
        "\n".join(
            [
                "from providence_cli.extensions.framework.extension_framework import BaseExtension, ExtensionMetadata, CustomMandate, CustomGuideline",
                "class Extension(BaseExtension):",
                "    metadata = ExtensionMetadata('Demo', '1.0', 'Author', 'Desc', 'demo-domain')",
                "    mandates = [CustomMandate('M1', 'HARD', 'T', 'D', category='general')]",
                "    guidelines = [CustomGuideline('G1', 'SOFT', 'Guide', category='testing')]",
                "    def initialize(self): self.ready = True",
                "    def validate(self): return []",
            ]
        ),
        encoding="utf-8",
    )

    loader = PluginLoader(str(root))
    found = loader.discover_plugins()
    assert found == [plugin_dir]
    ext = loader.load_plugin(plugin_dir)
    assert ext is not None
    assert "demo" in loader.loaded_plugins
    registry = ExtensionRegistry()
    assert loader.register_all(registry) == 1
    assert registry.get("demo-domain") is not None
    assert loader.get_stats()["plugins_loaded"] == 1


def test_plugin_loader_handles_missing_extension_and_exec_errors(
    tmp_path: Path,
) -> None:
    root = tmp_path / "plugins"
    missing_class = root / "missing-class"
    missing_class.mkdir(parents=True)
    (missing_class / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")

    broken = root / "broken"
    broken.mkdir(parents=True)
    (broken / "__init__.py").write_text(
        "raise RuntimeError('boom')\n", encoding="utf-8"
    )

    loader = PluginLoader(str(root))
    assert loader.load_plugin(missing_class) is None
    assert loader.load_plugin(broken) is None
    assert len(loader.load_errors) == 2


def test_plugin_loader_handles_spec_none_and_validation_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin_dir = tmp_path / "demo"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "__init__.py").write_text("x = 1\n", encoding="utf-8")

    loader = PluginLoader(str(tmp_path))

    monkeypatch.setattr(
        "importlib.util.spec_from_file_location",
        lambda *args, **kwargs: None,
    )
    assert loader.load_plugin(plugin_dir) is None
    assert "could not load module" in loader.load_errors[-1]

    class _Spec:
        name = "extension_demo"
        loader = type("_Loader", (), {"exec_module": lambda self, module: None})()

    class _Module:
        class Extension(_InvalidExtension):
            pass

    monkeypatch.setattr(
        "importlib.util.spec_from_file_location", lambda *args, **kwargs: _Spec()
    )
    monkeypatch.setattr("importlib.util.module_from_spec", lambda spec: _Module())
    assert loader.load_plugin(plugin_dir) is None
    assert "validation failed" in loader.load_errors[-1]


def test_plugin_loader_registers_with_global_registry_when_none_provided(
    tmp_path: Path,
) -> None:
    root = tmp_path / "plugins"
    plugin_dir = root / "demo"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "__init__.py").write_text(
        "\n".join(
            [
                "from providence_cli.extensions.framework.extension_framework import BaseExtension, ExtensionMetadata",
                "class Extension(BaseExtension):",
                "    metadata = ExtensionMetadata('Demo', '1.0', 'Author', 'Desc', 'demo-domain-3')",
                "    mandates = []",
                "    guidelines = []",
                "    def initialize(self): pass",
                "    def validate(self): return []",
            ]
        ),
        encoding="utf-8",
    )
    loader = PluginLoader(str(root))
    loader.load_all()
    get_registry().extensions.clear()
    assert loader.register_all() == 1


def test_load_all_plugins_returns_registry_and_stats(tmp_path: Path) -> None:
    root = tmp_path / "plugins"
    plugin_dir = root / "demo"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "__init__.py").write_text(
        "\n".join(
            [
                "from providence_cli.extensions.framework.extension_framework import BaseExtension, ExtensionMetadata",
                "class Extension(BaseExtension):",
                "    metadata = ExtensionMetadata('Demo', '1.0', 'Author', 'Desc', 'demo-domain-2')",
                "    mandates = []",
                "    guidelines = []",
                "    def initialize(self): pass",
                "    def validate(self): return []",
            ]
        ),
        encoding="utf-8",
    )
    registry, stats = load_all_plugins(str(root))
    assert stats["plugins_found"] == 1
    assert stats["plugins_loaded"] == 1
    assert registry.get("demo-domain-2") is not None
