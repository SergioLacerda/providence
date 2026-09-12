"""Tests for providence_cli.services.analysis_helpers."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from providence_cli.services import analysis_helpers


def _write_mission(path: Path, days_ago: int = 0) -> None:
    path.write_text("# mission\n", encoding="utf-8")
    timestamp = (datetime.now(tz=timezone.utc) - timedelta(days=days_ago)).timestamp()
    os.utime(path, (timestamp, timestamp))


def _make_analysis_workspace(tmp_path: Path) -> Path:
    for state in ("todo", "pending", "refined", "done"):
        (tmp_path / ".providence" / "analysis" / state).mkdir(
            parents=True, exist_ok=True
        )
    return tmp_path


def test_parse_duration_variants() -> None:
    assert analysis_helpers._parse_duration("2d") == timedelta(days=2)
    assert analysis_helpers._parse_duration("3h") == timedelta(hours=3)
    assert analysis_helpers._parse_duration("4m") == timedelta(minutes=4)
    assert analysis_helpers._parse_duration("nope") is None


def test_analysis_root_builds_expected_path(tmp_path: Path) -> None:
    assert (
        analysis_helpers._analysis_root(tmp_path)
        == tmp_path / ".providence" / "analysis"
    )


def test_collect_missions_skips_non_markdown_and_missing_dirs(tmp_path: Path) -> None:
    analysis_root = _make_analysis_workspace(tmp_path) / ".providence" / "analysis"
    _write_mission(analysis_root / "pending" / "mission-a.md", days_ago=1)
    (analysis_root / "pending" / "ignore.txt").write_text("x", encoding="utf-8")

    missions = analysis_helpers._collect_missions(analysis_root)

    assert [item["mission_id"] for item in missions["pending"]] == ["mission-a"]
    assert missions["todo"] == []
    assert missions["refined"] == []


def test_collect_missions_with_missing_state_dir(tmp_path: Path) -> None:
    analysis_root = tmp_path / ".providence" / "analysis"
    (analysis_root / "todo").mkdir(parents=True, exist_ok=True)
    _write_mission(analysis_root / "todo" / "mission-a.md")

    missions = analysis_helpers._collect_missions(analysis_root)

    assert missions["todo"]
    assert missions["pending"] == []
    assert missions["refined"] == []
    assert missions["done"] == []


def test_collect_expired_handles_missing_dir(tmp_path: Path) -> None:
    cutoff = datetime.now(tz=timezone.utc)
    assert (
        analysis_helpers._collect_expired(tmp_path / "done", cutoff, dry_run=True) == []
    )


def test_collect_expired_dry_run_and_delete(tmp_path: Path) -> None:
    done_dir = _make_analysis_workspace(tmp_path) / ".providence" / "analysis" / "done"
    old_file = done_dir / "old.md"
    new_file = done_dir / "new.md"
    (done_dir / "folder").mkdir()
    _write_mission(old_file, days_ago=10)
    _write_mission(new_file, days_ago=0)
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=1)

    dry_run = analysis_helpers._collect_expired(done_dir, cutoff, dry_run=True)
    assert dry_run == [str(old_file)]
    assert old_file.exists()

    removed = analysis_helpers._collect_expired(done_dir, cutoff, dry_run=False)
    assert removed == [str(old_file)]
    assert not old_file.exists()
    assert new_file.exists()


def test_next_action_map_and_unknown() -> None:
    assert analysis_helpers._next_action("todo").startswith("move to pending")
    assert analysis_helpers._next_action("pending").startswith("discovery in progress")
    assert analysis_helpers._next_action("refined").startswith("plan ready")
    assert analysis_helpers._next_action("done") == "mission complete"
    assert analysis_helpers._next_action("other") == "unknown"
