"""Dataclasses for parsed mandate.spec / guidelines.dsl entries."""

from dataclasses import dataclass
from typing import Any


@dataclass
class Mandate:
    """Represents a mandate from mandate.spec"""

    id: str
    type: str
    title: str
    description: str
    category: str
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        """To Dict."""
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "rationale": self.rationale,
        }


@dataclass
class Guideline:
    """Represents a guideline from guidelines.dsl"""

    id: str
    type: str
    title: str
    description: str
    category: str

    def to_dict(self) -> dict[str, Any]:
        """To Dict."""
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "category": self.category,
        }
