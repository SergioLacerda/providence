"""Tests for SDD Extension Framework registry, plugin loader, and global registry."""

from pathlib import Path
from typing import Any, cast

import pytest

from providence_cli.extensions.framework.extension_framework import (
    BaseExtension,
    CustomGuideline,
    CustomMandate,
    ExtensionMetadata,
    ExtensionRegistry,
    get_registry,
)
from providence_cli.extensions.framework.plugin_loader import PluginLoader


def _registry() -> Any:
    return cast(Any, ExtensionRegistry)()


class TestExtensionRegistry:
    """Test ExtensionRegistry"""

    def test_create_registry(self) -> None:
        """Test creating empty registry"""
        registry = _registry()

        assert len(registry.get_all()) == 0

    def test_register_extension(self) -> None:
        """Test registering an extension"""
        registry = _registry()

        # Create a mock extension
        class MockExtension(BaseExtension):
            metadata = ExtensionMetadata("Test", "1.0", "Author", "Desc", "test")
            mandates = []
            guidelines = []

            def initialize(self) -> None:
                pass

            def validate(self) -> list[str]:
                return []

        ext = MockExtension()
        result = registry.register("test-domain", ext)

        assert result is True
        assert registry.get("test-domain") is not None

    def test_get_mandates_all(self) -> None:
        """Test getting all mandates from registry"""
        registry = _registry()

        class MockExtension(BaseExtension):
            metadata = ExtensionMetadata("Test", "1.0", "Author", "Desc", "test")
            mandates = [
                CustomMandate("M001", "HARD", "Test", "Test", category="general")
            ]
            guidelines = []

            def initialize(self) -> None:
                pass

            def validate(self) -> list[str]:
                return []

        ext = MockExtension()
        registry.register("test-domain", ext)

        mandates = registry.get_mandates()
        assert len(mandates) == 1

    def test_get_stats(self) -> None:
        """Test getting registry statistics"""
        registry = _registry()

        class MockExtension(BaseExtension):
            metadata = ExtensionMetadata("Test", "1.0", "Author", "Desc", "test")
            mandates = [
                CustomMandate("M001", "HARD", "Test", "Test", category="general")
            ]
            guidelines = [CustomGuideline("G01", "SOFT", "Test", category="general")]

            def initialize(self) -> None:
                pass

            def validate(self) -> list[str]:
                return []

        ext = MockExtension()
        registry.register("test-domain", ext)

        stats = registry.get_stats()

        assert stats["total_extensions"] == 1
        assert stats["total_mandates"] == 1
        assert stats["total_guidelines"] == 1
        assert "test-domain" in stats["domains"]


class TestPluginLoader:
    """Test PluginLoader (if plugin examples exist)"""

    def test_discover_plugins(self) -> None:
        """Test plugin discovery"""
        # Create a test loader pointing to examples directory
        loader = PluginLoader(str(Path(__file__).parent.parent / "examples"))

        plugins = loader.discover_plugins()

        # Should find at least the examples (if they exist)
        # For now, just test that the method works
        assert isinstance(plugins, list)


class TestGlobalRegistry:
    """Test global registry functions"""

    def test_get_registry(self) -> None:
        """Test getting global registry"""
        registry = get_registry()

        assert registry is not None
        assert isinstance(registry, ExtensionRegistry)

    def test_get_registry_singleton(self) -> None:
        """Test that global registry is singleton"""
        registry1 = get_registry()
        registry2 = get_registry()

        assert registry1 is registry2


# Stub for testing (would be replaced by actual plugin)
class MockGameMasterExtension(BaseExtension):
    """Mock Game Master extension for testing"""

    metadata = ExtensionMetadata(
        name="Game Master API",
        version="1.0.0",
        author="Test",
        description="Test GM extension",
        domain="game-master-api",
    )
    mandates = [
        CustomMandate(
            "GMM001", "HARD", "Narrative State", "Test", category="architecture"
        )
    ]
    guidelines = [
        CustomGuideline("GMG01", "SOFT", "Random Generation", category="security")
    ]

    def initialize(self) -> None:
        pass

    def validate(self) -> list[str]:
        return []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
