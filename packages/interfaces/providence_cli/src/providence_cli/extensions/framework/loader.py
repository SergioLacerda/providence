"""Data models for SDD extension mandates, guidelines, and item types."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ItemType(str, Enum):
    """SDD item type enumeration."""

    MANDATE = "mandate"
    GUIDELINE = "guideline"


class Category(str, Enum):
    """Standard SDD categories."""

    ARCHITECTURE = "architecture"
    GENERAL = "general"
    PERFORMANCE = "performance"
    SECURITY = "security"
    GIT = "git"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    NAMING = "naming"
    CODE_STYLE = "code-style"


@dataclass
class CustomMandate:
    """Base class for custom mandates in specialized domains."""

    id: str
    type: str  # "HARD" or "SOFT"
    title: str
    description: str
    category: str = Category.GENERAL.value
    domain: str | None = None
    rationale: str | None = None
    validation_commands: list[str] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        """Validate mandate structure."""
        errors = []

        if not self.id:
            errors.append("Mandate ID cannot be empty")

        if not self.type or self.type not in ["HARD", "SOFT"]:
            errors.append(f"Invalid type: {self.type} (must be HARD or SOFT)")

        if not self.title or len(self.title.strip()) == 0:
            errors.append("Mandate title cannot be empty")

        if not self.description or len(self.description.strip()) == 0:
            errors.append("Mandate description cannot be empty")

        if self.category not in [c.value for c in Category]:
            errors.append(f"Invalid category: {self.category}")

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "domain": self.domain,
            "rationale": self.rationale,
            "validation_commands": self.validation_commands,
            "metadata": self.metadata,
        }


@dataclass
class CustomGuideline:
    """Base class for custom guidelines in specialized domains."""

    id: str
    type: str  # "HARD" or "SOFT"
    title: str
    category: str = Category.GENERAL.value
    domain: str | None = None
    description: str | None = None
    examples: list[str] | None = None
    related_mandate: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> list[str]:
        """Validate guideline structure."""
        errors = []

        if not self.id:
            errors.append("Guideline ID cannot be empty")

        if not self.type or self.type not in ["HARD", "SOFT"]:
            errors.append(f"Invalid type: {self.type} (must be HARD or SOFT)")

        if not self.title or len(self.title.strip()) == 0:
            errors.append("Guideline title cannot be empty")

        if self.category not in [c.value for c in Category]:
            errors.append(f"Invalid category: {self.category}")

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "category": self.category,
            "domain": self.domain,
            "description": self.description,
            "examples": self.examples,
            "related_mandate": self.related_mandate,
            "metadata": self.metadata,
        }
