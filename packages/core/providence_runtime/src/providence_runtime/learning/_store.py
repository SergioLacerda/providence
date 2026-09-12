"""SupervisedLearningStore — file-backed learning registry with human approval gate."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from ._failure_ledger_entry import FailureLedgerEntry
from ._rule_candidate import RuleCandidate
from ._rule_registry import _RuleRegistryMixin


class SupervisedLearningStore(_RuleRegistryMixin):
    """File-backed learning registry with human approval gate."""

    def __init__(self, project_root: Path) -> None:
        self._runtime_dir = project_root / ".providence" / "runtime"
        self._runtime_dir.mkdir(parents=True, exist_ok=True)
        self._ledger_path = self._runtime_dir / "failure-ledger.jsonl"
        self._candidates_path = self._runtime_dir / "rule-candidates.json"
        self._registry_path = self._runtime_dir / "rule-registry.json"
        self._impact_path = self._runtime_dir / "rule-impact.jsonl"

    def append_failure(self, entry: FailureLedgerEntry) -> None:
        """Append Failure."""
        with self._ledger_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry), ensure_ascii=True) + "\n")

    def list_failures(self, *, limit: int | None = None) -> list[dict[str, Any]]:
        """Return most recent failure rows, newest first."""
        rows = list(reversed(self._read_jsonl(self._ledger_path)))
        if limit is None or limit <= 0:
            return rows
        return rows[:limit]

    def find_similar_failures(
        self,
        *,
        symptom: str,
        root_cause: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return ledger entries matching symptom and optionally root_cause."""
        matches = [
            row
            for row in self.list_failures()
            if str(row.get("symptom", "")) == symptom
            and (
                root_cause is None or str(row.get("root_cause", "")) == str(root_cause)
            )
        ]
        if limit is None or limit <= 0:
            return matches
        return matches[:limit]

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for raw in path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            rows.append(json.loads(raw))
        return rows

    def _read_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, path: Path, payload: Any) -> None:
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8"
        )

    def generate_candidates_from_ledger(
        self, *, min_occurrences: int = 2
    ) -> list[RuleCandidate]:
        """Generate candidates from recurring failure ledger patterns."""
        ledger = self._read_jsonl(self._ledger_path)
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in ledger:
            key = f"{row.get('symptom', '')}|{row.get('root_cause', '')}"
            grouped.setdefault(key, []).append(row)

        existing = self._read_json(self._candidates_path, {"candidates": []})
        existing_patterns = {
            str(item.get("pattern", "")) for item in existing.get("candidates", [])
        }
        created: list[RuleCandidate] = []
        for key, rows in grouped.items():
            if len(rows) < min_occurrences:
                continue
            symptom, root_cause = key.split("|", 1)
            evidence_refs = sorted(
                {
                    ref
                    for row in rows
                    for ref in row.get("evidence_refs", [])
                    if isinstance(ref, str) and ref.strip()
                }
            )
            if not evidence_refs or key in existing_patterns:
                continue
            created.append(
                RuleCandidate(
                    candidate_id=f"rc-{uuid4().hex[:12]}",
                    pattern=key,
                    proposed_guardrail=(
                        f"Block speculative correction when pattern '{symptom}' "
                        f"with root cause '{root_cause}' appears without evidence."
                    ),
                    risk_level="medium",
                    expected_impact="reduce_rework",
                    evidence_refs=evidence_refs,
                    source_count=len(rows),
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
            )

        if created:
            payload = existing
            payload.setdefault("candidates", [])
            payload["candidates"].extend(asdict(item) for item in created)
            self._write_json(self._candidates_path, payload)
        return created
