"""Governance AST — structured intermediate representation for compiled artifacts.

The AST sits between source markdown/DSL and the final compiled JSON artifacts.
It provides:
  - Typed, versioned representation of every governance item
  - Semantic diffing with explicit breaking/non-breaking classification
  - Stable serialisation for golden-snapshot comparisons

Design principles (§12 Compiler-Runtime Boundary):
  - Compiler defines governance meaning; this module belongs to the compiler layer.
  - AST is derived from compiled JSON artifacts, not from re-parsing canonical docs.
  - Same input always produces the same AST (determinism gate §9.4).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AST_VERSION = "1.0"

# ---------------------------------------------------------------------------
# Core data types
# ---------------------------------------------------------------------------


@dataclass
class GovernanceItem:
    """A single governance item extracted from a compiled artifact.

    Rule card variants (Phase 4 I3) support progressive disclosure:
    - summary_minimal: One-line summary for quick reference
    - summary_runtime: Detailed rule for agent enforcement
    - summary_full: Full markdown description with rationale
    """

    id: str
    title: str
    item_type: str  # MANDATE | POLICY | GUIDELINE | RULE
    description: str = ""
    summary_minimal: str | None = None
    summary_runtime: str | None = None
    summary_full: str | None = None
    criticality: str = "medium"
    enforcement_steps: list[str] | None = None
    requirements: list[str] | None = None
    rationale: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """To Dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GovernanceItem:
        """From Dict."""
        return cls(
            id=str(data.get("id", "")),
            title=str(data.get("title", "")),
            item_type=str(data.get("item_type", data.get("type", ""))),
            description=str(data.get("description", "")),
            summary_minimal=data.get("summary_minimal"),
            summary_runtime=data.get("summary_runtime"),
            summary_full=data.get("summary_full"),
            criticality=str(data.get("criticality", "medium")),
            enforcement_steps=data.get("enforcement_steps"),
            requirements=data.get("requirements"),
            rationale=data.get("rationale"),
        )


@dataclass
class GovernanceAST:
    """Versioned AST built from a compiled governance artifact.

    Fields
    ------
    ast_version:
        Schema version of this AST representation (semver string).
    source_fingerprint:
        SHA-256 fingerprint of the source compiled artifact.
    generated_at:
        ISO-8601 UTC timestamp when this AST was built.
    profile:
        Governance profile the artifact was compiled for (master | client).
    items:
        Ordered list of governance items.
    """

    ast_version: str
    source_fingerprint: str
    generated_at: str
    profile: str
    items: list[GovernanceItem] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def from_compiled_json(cls, artifact_path: Path) -> GovernanceAST:
        """Build an AST from a ``governance-core.json`` compiled artifact.

        Raises FileNotFoundError if *artifact_path* does not exist.
        Raises ValueError if the file cannot be parsed as a governance artifact.
        """
        if not artifact_path.exists():
            raise FileNotFoundError(f"Artifact not found: {artifact_path}")

        raw = json.loads(artifact_path.read_text(encoding="utf-8"))
        items = _extract_items(raw)
        fingerprint = str(
            raw.get("fingerprint", _fingerprint_bytes(artifact_path.read_bytes()))
        )
        profile = str(raw.get("profile", raw.get("category", "master"))).lower()

        return cls(
            ast_version=AST_VERSION,
            source_fingerprint=fingerprint,
            generated_at=_utc_now(),
            profile=profile,
            items=items,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GovernanceAST:
        """Deserialise from a previously serialised dict (e.g. golden snapshot)."""
        return cls(
            ast_version=str(data.get("ast_version", AST_VERSION)),
            source_fingerprint=str(data.get("source_fingerprint", "")),
            generated_at=str(data.get("generated_at", "")),
            profile=str(data.get("profile", "")),
            items=[GovernanceItem.from_dict(i) for i in data.get("items", [])],
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """To Dict."""
        return {
            "ast_version": self.ast_version,
            "source_fingerprint": self.source_fingerprint,
            "generated_at": self.generated_at,
            "profile": self.profile,
            "items": [i.to_dict() for i in self.items],
        }

    def to_json(self, indent: int = 2) -> str:
        """To Json."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------

    def item_by_id(self, item_id: str) -> GovernanceItem | None:
        """Case-insensitive lookup by ID."""
        target = item_id.upper()
        return next((i for i in self.items if i.id.upper() == target), None)

    def items_by_type(self, item_type: str) -> list[GovernanceItem]:
        """Items By Type."""
        target = item_type.upper()
        return [i for i in self.items if i.item_type.upper() == target]

    # ------------------------------------------------------------------
    # Semantic diff
    # ------------------------------------------------------------------

    def diff(self, other: GovernanceAST) -> ASTDiff:
        """Return the semantic diff between *self* (baseline) and *other* (current).

        Breaking changes (§4 Phase 2 criteria):
          - Item removed from baseline
          - Item ID renamed (same title, different ID)

        Non-breaking changes:
          - Item added
          - Title or description changed
          - item_type changed (rare, still non-breaking by default)
        """
        baseline = {i.id.upper(): i for i in self.items}
        current = {i.id.upper(): i for i in other.items}

        breaking: list[DiffEntry] = []
        non_breaking: list[DiffEntry] = []
        added: list[DiffEntry] = []
        removed: list[DiffEntry] = []

        # Removed items (breaking)
        for item_id, item in baseline.items():
            if item_id not in current:
                entry = DiffEntry(
                    change_type="removed",
                    breaking=True,
                    item_id=item.id,
                    before=item.title,
                    after="",
                )
                removed.append(entry)
                breaking.append(entry)

        # Added items (non-breaking)
        for item_id, item in current.items():
            if item_id not in baseline:
                entry = DiffEntry(
                    change_type="added",
                    breaking=False,
                    item_id=item.id,
                    before="",
                    after=item.title,
                )
                added.append(entry)
                non_breaking.append(entry)

        # Modified items
        for item_id in baseline:
            if item_id not in current:
                continue
            before = baseline[item_id]
            after = current[item_id]
            for changed_field in ("title", "description", "item_type"):
                v_before = getattr(before, changed_field)
                v_after = getattr(after, changed_field)
                if v_before != v_after:
                    entry = DiffEntry(
                        change_type="modified",
                        breaking=False,
                        item_id=before.id,
                        field=changed_field,
                        before=v_before,
                        after=v_after,
                    )
                    non_breaking.append(entry)

        return ASTDiff(
            breaking_changes=breaking,
            non_breaking_changes=non_breaking,
            added_items=added,
            removed_items=removed,
        )


# ---------------------------------------------------------------------------
# Diff types
# ---------------------------------------------------------------------------


@dataclass
class DiffEntry:
    """A single semantic change between two AST snapshots."""

    change_type: str  # added | removed | modified
    breaking: bool
    item_id: str
    field: str = ""  # populated for "modified" entries
    before: str = ""
    after: str = ""

    def to_dict(self) -> dict[str, Any]:
        """To Dict."""
        return asdict(self)


@dataclass
class ASTDiff:
    """Complete semantic diff between a baseline and a current AST."""

    breaking_changes: list[DiffEntry] = field(default_factory=list)
    non_breaking_changes: list[DiffEntry] = field(default_factory=list)
    added_items: list[DiffEntry] = field(default_factory=list)
    removed_items: list[DiffEntry] = field(default_factory=list)

    @property
    def has_breaking_changes(self) -> bool:
        """Has Breaking Changes."""
        return len(self.breaking_changes) > 0

    @property
    def is_clean(self) -> bool:
        """Is Clean."""
        return (
            len(self.breaking_changes) == 0
            and len(self.non_breaking_changes) == 0
            and len(self.added_items) == 0
            and len(self.removed_items) == 0
        )

    def summary(self) -> str:
        """Return a human-readable one-line diff summary."""
        if self.is_clean:
            return "No changes detected."
        parts: list[str] = []
        if self.breaking_changes:
            parts.append(f"{len(self.breaking_changes)} breaking")
        if self.non_breaking_changes:
            parts.append(f"{len(self.non_breaking_changes)} non-breaking")
        if self.added_items:
            parts.append(f"{len(self.added_items)} added")
        if self.removed_items:
            parts.append(f"{len(self.removed_items)} removed")
        return ", ".join(parts) + "."

    def to_dict(self) -> dict[str, Any]:
        """To Dict."""
        return {
            "has_breaking_changes": self.has_breaking_changes,
            "breaking_changes": [e.to_dict() for e in self.breaking_changes],
            "non_breaking_changes": [e.to_dict() for e in self.non_breaking_changes],
            "added_items": [e.to_dict() for e in self.added_items],
            "removed_items": [e.to_dict() for e in self.removed_items],
        }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def _fingerprint_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _extract_items(raw: dict[str, Any]) -> list[GovernanceItem]:
    """Extract GovernanceItem list from a compiled JSON artifact dict."""
    result: list[GovernanceItem] = []
    for entry in raw.get("items", []):
        # Support both flat schema and nested metadata schema (§12.1)
        meta = entry.get("metadata", {})
        item_type = (
            entry.get("item_type") or entry.get("type") or meta.get("type") or "UNKNOWN"
        )
        description = entry.get("description") or meta.get("description") or ""
        result.append(
            GovernanceItem(
                id=str(entry.get("id", "")),
                title=str(entry.get("title", "")),
                item_type=str(item_type).upper(),
                description=str(description),
                summary_minimal=entry.get("summary_minimal"),
                summary_runtime=entry.get("summary_runtime"),
                summary_full=entry.get("summary_full"),
                criticality=str(entry.get("criticality", "medium")),
                enforcement_steps=entry.get("enforcement_steps"),
                requirements=entry.get("requirements"),
                rationale=entry.get("rationale"),
            )
        )
    return result
