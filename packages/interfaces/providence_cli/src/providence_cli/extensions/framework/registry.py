"""Extension registry: registration, lookup, and global singleton."""

from __future__ import annotations

from typing import Any

from providence_cli.extensions.framework.lifecycle import BaseExtension
from providence_cli.extensions.framework.loader import CustomGuideline, CustomMandate


class ExtensionRegistry:
    """Registry for managing SDD extensions."""

    def __init__(self) -> None:
        self.extensions: dict[str, BaseExtension] = {}
        self.errors: list[str] = []

    def register(self, domain: str, extension: BaseExtension) -> bool:
        """Register an extension."""
        validation_errors = extension.validate()

        if validation_errors:
            self.errors.extend([f"{domain}: {e}" for e in validation_errors])
            return False

        self.extensions[domain] = extension
        return True

    def get(self, domain: str) -> BaseExtension | None:
        """Get extension by domain."""
        return self.extensions.get(domain)

    def get_all(self) -> dict[str, BaseExtension]:
        """Get all registered extensions."""
        return self.extensions.copy()

    def get_mandates(self, domain: str | None = None) -> list[CustomMandate]:
        """Get all mandates, optionally filtered by domain."""
        mandates = []

        if domain:
            ext = self.get(domain)
            if ext:
                mandates = ext.get_mandates()
        else:
            for ext in self.extensions.values():
                mandates.extend(ext.get_mandates())

        return mandates

    def get_guidelines(self, domain: str | None = None) -> list[CustomGuideline]:
        """Get all guidelines, optionally filtered by domain."""
        guidelines = []

        if domain:
            ext = self.get(domain)
            if ext:
                guidelines = ext.get_guidelines()
        else:
            for ext in self.extensions.values():
                guidelines.extend(ext.get_guidelines())

        return guidelines

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about registered extensions."""
        total_mandates = sum(
            len(ext.get_mandates()) for ext in self.extensions.values()
        )
        total_guidelines = sum(
            len(ext.get_guidelines()) for ext in self.extensions.values()
        )

        return {
            "total_extensions": len(self.extensions),
            "domains": list(self.extensions.keys()),
            "total_mandates": total_mandates,
            "total_guidelines": total_guidelines,
            "errors": len(self.errors),
        }


# Global registry singleton
_global_registry: ExtensionRegistry | None = None


def get_registry() -> ExtensionRegistry:
    """Get or create global extension registry."""
    global _global_registry
    if _global_registry is None:
        _global_registry = ExtensionRegistry()
    return _global_registry


def register_extension(domain: str, extension: BaseExtension) -> bool:
    """Register extension in global registry."""
    return get_registry().register(domain, extension)


def get_extension(domain: str) -> BaseExtension | None:
    """Get extension from global registry."""
    return get_registry().get(domain)
