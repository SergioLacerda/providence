from __future__ import annotations

from pathlib import Path

from providence_runtime._skill_executor import CompressContextHandler, _compress_context


def test_compress_context_preserves_critical_keys() -> None:
    compressed, report = _compress_context(
        {
            "governance_fingerprint": "abc123",
            "execution_contract": {"task_id": "task-1"},
            "notes": "x" * 200,
        }
    )

    assert compressed["governance_fingerprint"] == "abc123"
    assert compressed["execution_contract"] == {"task_id": "task-1"}
    assert compressed["notes"]["type"] == "string"
    assert "notes" in report["archival_candidates"]


def test_compress_context_summarizes_collection_values() -> None:
    compressed, report = _compress_context(
        {
            "events": ["a", "b", "c", "d"],
            "payload": {"a": 1, "b": 2, "c": 3, "d": 4},
        }
    )

    assert compressed["events"]["type"] == "list"
    assert compressed["events"]["count"] == 4
    assert compressed["payload"]["type"] == "dict"
    assert compressed["payload"]["count"] == 4
    assert sorted(report["summarized_keys"]) == ["events", "payload"]
    assert report["compression_ratio"] > 0.0


def test_compress_context_handler_returns_expected_artifacts() -> None:
    handler = CompressContextHandler()
    outcome = handler.pre_run(
        {
            "governance_fingerprint": "abc123",
            "chat_log": "y" * 150,
        },
        learning=None,
        skill=None,
        profile="default",
        footer_fn=lambda d, g: "",
    )

    assert outcome.early_result is None
    assert outcome.artifacts["compressed_context"]["governance_fingerprint"] == "abc123"
    assert outcome.artifacts["compression_report"]["original_key_count"] == 2


def test_compress_context_handler_archives_candidates(tmp_path: Path) -> None:
    handler = CompressContextHandler()
    outcome = handler.pre_run(
        {
            "_project_root": str(tmp_path),
            "governance_fingerprint": "abc123",
            "chat_log": "y" * 150,
            "events": ["a", "b", "c", "d"],
        },
        learning=None,
        skill=None,
        profile="default",
        footer_fn=lambda d, g: "",
    )

    report = outcome.artifacts["compression_report"]
    assert report["archive_dir"].startswith(".providence/runtime/context-archive/")
    assert report["summary_path"].endswith("compression-summary.json")
    summary_path = tmp_path / report["summary_path"]
    assert summary_path.exists()
    assert any(item["key"] == "chat_log" for item in report["archived_items"])
