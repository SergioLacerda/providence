"""Extension metadata and base class for SDD extension lifecycle."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from providence_cli.extensions.framework.loader import CustomGuideline, CustomMandate


class ExtensionMetadata:
    """Metadata for extension packages."""

    def __init__(
        self,
        name: str,
        version: str,
        author: str,
        description: str,
        domain: str,
        dependencies: list[str] | None = None,
        license: str = "MIT",
    ):
        self.name = name
        self.version = version
        self.author = author
        self.description = description
        self.domain = domain
        self.dependencies = dependencies or []
        self.license = license

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "domain": self.domain,
            "dependencies": self.dependencies,
            "license": self.license,
        }


class BaseExtension(ABC):
    """Base class for all SDD extensions."""

    # Subclasses must define these
    metadata: ExtensionMetadata
    mandates: list[CustomMandate] = []
    guidelines: list[CustomGuideline] = []

    @abstractmethod
    def initialize(self) -> None:
        """Initialize extension  called on load."""

    @abstractmethod
    def validate(self) -> list[str]:
        """Validate extension structure."""

    def get_mandates(self) -> list[CustomMandate]:
        """Get all mandates from this extension."""
        return self.mandates

    def get_guidelines(self) -> list[CustomGuideline]:
        """Get all guidelines from this extension."""
        return self.guidelines

    def to_dict(self) -> dict[str, Any]:
        """Convert extension to dictionary."""
        return {
            "metadata": self.metadata.to_dict(),
            "mandates": [m.to_dict() for m in self.mandates],
            "guidelines": [g.to_dict() for g in self.guidelines],
        }
