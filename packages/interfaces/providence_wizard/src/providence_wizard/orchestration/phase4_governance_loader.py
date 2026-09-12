"""
GovernanceLoader  Phase 4 step: parse compiled governance JSON into mandates/guidelines.
"""

import json
from pathlib import Path
from typing import Any

from providence_core.utils.log import get_logger

logger = get_logger(__name__)


class GovernanceLoader:
    """Load and parse compiled governance JSON from Phase 3 output."""

    def __init__(
        self,
        governance_core_path: Path,
        governance_client_path: Path,
        verbose: bool = False,
    ) -> None:
        self.governance_core_path = governance_core_path
        self.governance_client_path = governance_client_path
        self.verbose = verbose

        self.mandates: list[dict[str, Any]] = []
        self.guidelines: dict[str, dict[str, Any]] = {}
        self.guidelines_by_category: dict[str, list[dict[str, Any]]] = {}

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)  # noqa: T201
        else:
            logger.debug(message)

    def _normalize_item_type(self, item: dict[str, Any], default_type: str = "") -> str:
        """Determine canonical type string (MANDATE or GUIDELINE) for a governance item."""
        raw_type = item.get("type", "")
        if isinstance(raw_type, str):
            normalized = raw_type.strip().upper()
            if normalized in {"MANDATE", "GUIDELINE"}:
                return normalized
        if default_type in {"MANDATE", "GUIDELINE"}:
            return default_type
        item_id = str(item.get("id", "")).upper()
        if item_id.startswith("M"):
            return "MANDATE"
        if item_id.startswith("G"):
            return "GUIDELINE"
        return ""

    def _ingest_items(
        self,
        items: list[dict[str, Any]],
        seen_mandates: "set[str]",
        default_type: str = "",
    ) -> None:
        """Append items into self.mandates / self.guidelines, deduplicating mandates."""
        for item in items:
            item_id = str(item.get("id", "")).strip()
            if not item_id:
                continue
            item_type = self._normalize_item_type(item, default_type)
            if item_type == "MANDATE":
                if item_id not in seen_mandates:
                    seen_mandates.add(item_id)
                    self.mandates.append(item)
            elif item_type == "GUIDELINE":
                self.guidelines[item_id] = item
                category = item.get("category", "other")
                if category not in self.guidelines_by_category:
                    self.guidelines_by_category[category] = []
                self.guidelines_by_category[category].append(item)

    def load(self) -> bool:
        """Load compiled governance from Phase 3 output. Returns True on success."""
        self._log(f"Loading governance-core.json from {self.governance_core_path}")

        if not self.governance_core_path.exists():
            logger.error(
                "governance-core.json not found: %s", self.governance_core_path
            )
            return False

        try:
            with open(
                self.governance_core_path, encoding="utf-8", errors="strict"
            ) as f:
                core_data = json.load(f)

            client_data: dict[str, Any] = {}
            if self.governance_client_path.exists():
                with open(
                    self.governance_client_path, encoding="utf-8", errors="strict"
                ) as f:
                    client_data = json.load(f)

            seen_mandates: set[str] = set()
            self._ingest_items(
                core_data.get("items", []), seen_mandates, default_type=""
            )
            self._ingest_items(
                client_data.get("items", []), seen_mandates, default_type="GUIDELINE"
            )

            self._log(
                f"Loaded {len(self.mandates)} mandates and {len(self.guidelines)} guidelines"
            )
            self._log(f"Categories: {', '.join(self.guidelines_by_category.keys())}")
            return True
        except Exception as e:
            logger.error("Failed to load governance: %s", e)
            import traceback

            traceback.print_exc()
            return False
