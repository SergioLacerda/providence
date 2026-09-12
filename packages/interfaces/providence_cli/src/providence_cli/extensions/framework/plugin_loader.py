"""
SDD Extension Plugin Loader

Discovers and loads extension plugins from the examples directory.
Handles error reporting and validation.
"""

import importlib.util
import sys
from pathlib import Path
from typing import Any, cast

from .extension_framework import BaseExtension, ExtensionRegistry, get_registry


class PluginLoader:
    """Dynamically loads extension plugins from filesystem"""

    def __init__(self, plugins_dir: str | None = None):
        """Initialize loader with plugins directory

        Args:
            plugins_dir: Directory containing extension plugins
                        Default: core/extensions/examples/
        """
        if plugins_dir is None:
            # Auto-detect relative to this framework location
            plugins_dir = str(Path(__file__).parent.parent / "examples")

        self.plugins_dir = Path(plugins_dir)
        self.loaded_plugins: dict[str, BaseExtension] = {}
        self.load_errors: list[str] = []

    def discover_plugins(self) -> list[Path]:
        """Discover plugin modules in plugins directory"""
        plugins: list[Path] = []

        if not self.plugins_dir.exists():
            self.load_errors.append(f"Plugins directory not found: {self.plugins_dir}")
            return plugins

        # Look for __init__.py files in subdirectories
        for item in self.plugins_dir.iterdir():
            if item.is_dir():
                init_file = item / "__init__.py"
                if init_file.exists():
                    plugins.append(item)

        return plugins

    def load_plugin(self, plugin_dir: Path) -> BaseExtension | None:
        """Load a single plugin from directory

        Args:
            plugin_dir: Directory containing the plugin

        Returns:
            BaseExtension instance or None if loading failed
        """
        try:
            init_file = plugin_dir / "__init__.py"

            if not init_file.exists():
                error = f"Plugin {plugin_dir.name}: missing __init__.py"
                self.load_errors.append(error)
                return None

            # Load the module
            spec = importlib.util.spec_from_file_location(
                f"extension_{plugin_dir.name}", init_file
            )

            if spec is None or spec.loader is None:
                error = f"Plugin {plugin_dir.name}: could not load module"
                self.load_errors.append(error)
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

            # Look for Extension class
            if hasattr(module, "Extension"):
                extension_class = module.Extension

                # Instantiate and initialize
                extension = extension_class()
                extension.initialize()

                # Validate
                validation_errors = extension.validate()
                if validation_errors:
                    error = f"Plugin {plugin_dir.name} validation failed:\n"
                    error += "\n".join(f"  - {e}" for e in validation_errors)
                    self.load_errors.append(error)
                    return None

                self.loaded_plugins[plugin_dir.name] = extension
                return cast(BaseExtension, extension)
            else:
                error = f"Plugin {plugin_dir.name}: missing Extension class"
                self.load_errors.append(error)
                return None

        except Exception as e:
            error = f"Plugin {plugin_dir.name}: {type(e).__name__}: {str(e)}"
            self.load_errors.append(error)
            return None

    def load_all(self) -> dict[str, BaseExtension]:
        """Load all discovered plugins"""
        self.loaded_plugins = {}
        self.load_errors = []

        plugins = self.discover_plugins()

        for plugin_dir in plugins:
            self.load_plugin(plugin_dir)

        return self.loaded_plugins

    def register_all(self, registry: ExtensionRegistry | None = None) -> int:
        """Register all loaded plugins in registry

        Args:
            registry: Registry to register in (uses global if None)

        Returns:
            Number of successfully registered plugins
        """
        if registry is None:
            registry = get_registry()

        registered = 0

        for _name, extension in self.loaded_plugins.items():
            domain = extension.metadata.domain
            if registry.register(domain, extension):
                registered += 1

        return registered

    def get_stats(self) -> dict[str, Any]:
        """Get loading statistics"""
        return {
            "plugins_found": len(self.discover_plugins()),
            "plugins_loaded": len(self.loaded_plugins),
            "load_errors": len(self.load_errors),
            "error_details": self.load_errors,
        }


def load_all_plugins(
    plugins_dir: str | None = None,
) -> tuple[ExtensionRegistry, dict[str, Any]]:
    """Convenience function to load all plugins and return registry + stats

    Args:
        plugins_dir: Directory containing plugins (default: relative to framework)

    Returns:
        Tuple of (registry, stats)
    """
    loader = PluginLoader(plugins_dir)
    loader.load_all()

    registry = get_registry()
    loader.register_all(registry)

    return registry, loader.get_stats()


if __name__ == "__main__":
    print("SDD Extension Plugin Loader")  # noqa: T201
    print("=" * 50)  # noqa: T201

    # Load all plugins
    registry, stats = load_all_plugins()

    print(f"\nPlugins Found: {stats['plugins_found']}")  # noqa: T201
    print(f"Plugins Loaded: {stats['plugins_loaded']}")  # noqa: T201
    print(f"Errors: {stats['load_errors']}")  # noqa: T201

    if stats["error_details"]:
        print("\nError Details:")  # noqa: T201
        for error in stats["error_details"]:
            print(f"  {error}")  # noqa: T201

    print("\nRegistry Stats:")  # noqa: T201
    reg_stats = registry.get_stats()
    print(f"  Extensions: {reg_stats['total_extensions']}")  # noqa: T201
    print(f"  Mandates: {reg_stats['total_mandates']}")  # noqa: T201
    print(f"  Guidelines: {reg_stats['total_guidelines']}")  # noqa: T201

    if reg_stats["domains"]:
        print("\nRegistered Domains:")  # noqa: T201
        for domain in reg_stats["domains"]:
            print(f"  - {domain}")  # noqa: T201
