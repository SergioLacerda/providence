"""Unit tests for governance_config_reader  pure config/drift checks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from providence_cli.services.governance_config_reader import (
    check_fingerprints_valid,
    check_no_conflicts,
    check_root_seed_drift,
)

pytestmark = pytest.mark.unit


def _write_metadata(root: Path, **fields: object) -> None:
    (root / ".providence").mkdir(parents=True, exist_ok=True)
    (root / ".providence" / "metadata.json").write_text(
        json.dumps(fields), encoding="utf-8"
    )


def _write_seed(root: Path, name: str, fingerprint: str) -> None:
    """Write a seed file with a real managed block (current sdd format)."""
    (root / name).write_text(
        "<!-- sdd:managed:begin -->\n"
        f"# Governance fingerprint: {fingerprint}\n"
        "<!-- sdd:managed:end -->\n\nBody.\n",
        encoding="utf-8",
    )


def _write_unmanaged_seed(root: Path, name: str, fingerprint: str) -> None:
    """Write a seed file in the pre-managed-block format (no markers)
    the realistic state of every already-deployed root seed file
    immediately after this fix ships."""
    (root / name).write_text(
        f"# Governance fingerprint: {fingerprint}\n\nBody.\n", encoding="utf-8"
    )


class TestCheckFingerprintsValid:
    def test_none_config_is_invalid(self) -> None:
        assert check_fingerprints_valid(None) is False

    def test_valid_when_both_fingerprints_present(self) -> None:
        config = {"core_fingerprint": "a", "client_fingerprint": "b"}
        assert check_fingerprints_valid(config) is True


class TestCheckNoConflicts:
    def test_none_config_reports_conflict(self) -> None:
        assert check_no_conflicts(None) is False

    def test_matching_fingerprints_is_a_conflict(self) -> None:
        assert (
            check_no_conflicts({"core_fingerprint": "a", "client_fingerprint": "a"})
            is False
        )

    def test_differing_fingerprints_is_not_a_conflict(self) -> None:
        assert (
            check_no_conflicts({"core_fingerprint": "a", "client_fingerprint": "b"})
            is True
        )


class TestCheckRootSeedDrift:
    def test_passes_when_metadata_missing(self, tmp_path: Path) -> None:
        ok, reason = check_root_seed_drift(str(tmp_path / ".providence"))
        assert ok is True
        assert "not found" in reason

    def test_passes_when_no_fingerprint_in_metadata(self, tmp_path: Path) -> None:
        _write_metadata(tmp_path, version="3.0")
        ok, reason = check_root_seed_drift(str(tmp_path / ".providence"))
        assert ok is True
        assert "no governance_fingerprint" in reason

    def test_passes_when_seeds_match_top_level_fingerprint(
        self, tmp_path: Path
    ) -> None:
        _write_metadata(tmp_path, governance_fingerprint="abc123")
        _write_seed(tmp_path, "AGENTS.md", "abc123")
        _write_seed(tmp_path, "CLAUDE.md", "abc123")
        ok, reason = check_root_seed_drift(str(tmp_path / ".providence"))
        assert ok is True
        assert "no root-seed drift" in reason

    def test_falls_back_to_combined_fingerprint_when_top_level_absent(
        self, tmp_path: Path
    ) -> None:
        _write_metadata(tmp_path, fingerprints={"combined": "abc123"})
        _write_seed(tmp_path, "CLAUDE.md", "abc123")
        ok, reason = check_root_seed_drift(str(tmp_path / ".providence"))
        assert ok is True
        assert "no root-seed drift" in reason

    def test_fails_when_seed_fingerprint_mismatches(self, tmp_path: Path) -> None:
        _write_metadata(tmp_path, governance_fingerprint="abc123")
        _write_seed(tmp_path, "CLAUDE.md", "deadbeef99")
        ok, reason = check_root_seed_drift(str(tmp_path / ".providence"))
        assert ok is False
        assert "CLAUDE.md" in reason

    def test_missing_seed_files_are_not_drift(self, tmp_path: Path) -> None:
        _write_metadata(tmp_path, governance_fingerprint="abc123")
        ok, reason = check_root_seed_drift(str(tmp_path / ".providence"))
        assert ok is True
        assert "no root-seed drift" in reason

    def test_unmanaged_seed_with_stale_fingerprint_is_not_drift(
        self, tmp_path: Path
    ) -> None:
        """T3 regression: a file with no managed-block markers  the
        realistic state of every already-deployed root seed file right
        after this fix ships  must never fail the check, even if its
        (unmanaged) content happens to mention a stale fingerprint. sdd has
        no claim over content it never delimited as its own.
        `.analysis/refined/20260906-root-seed-githook-necessity/design.md`.
        """
        _write_metadata(tmp_path, governance_fingerprint="abc123")
        _write_unmanaged_seed(tmp_path, "CLAUDE.md", "deadbeef99")
        ok, reason = check_root_seed_drift(str(tmp_path / ".providence"))
        assert ok is True
        assert "no managed block found in: CLAUDE.md" in reason

    def test_malformed_managed_block_is_not_drift(self, tmp_path: Path) -> None:
        """A hand-broken marker pair degrades safely to 'unmanaged', never
        to a validator crash or a false drift failure."""
        _write_metadata(tmp_path, governance_fingerprint="abc123")
        (tmp_path / "CLAUDE.md").write_text(
            "<!-- sdd:managed:begin -->\nstale content, no end marker\n",
            encoding="utf-8",
        )
        ok, reason = check_root_seed_drift(str(tmp_path / ".providence"))
        assert ok is True

    def test_tracked_status_is_irrelevant_to_managed_block_drift(
        self, tmp_path: Path
    ) -> None:
        """Revision 1 regression: a stale managed block fails the check
        purely on content, independent of git-tracked status  there is no
        tracked/untracked branch anywhere in `check_root_seed_drift`
        (Revision 0's tracked-only mechanism was fully replaced, not
        layered on top of). This test runs outside any git repository
        (`tmp_path` is never `git init`ed) and the stale block still fails,
        proving tracked status is never consulted."""
        _write_metadata(tmp_path, governance_fingerprint="abc123")
        _write_seed(tmp_path, "AGENTS.md", "deadbeef99")
        ok, reason = check_root_seed_drift(str(tmp_path / ".providence"))
        assert ok is False
        assert "AGENTS.md" in reason
