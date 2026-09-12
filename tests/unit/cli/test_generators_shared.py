"""Unit tests for providence_cli.generators._shared and _seeds."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# _shared helpers
# ---------------------------------------------------------------------------


class TestFingerprintPrefix:
    def test_returns_na_when_key_missing(self) -> None:
        from providence_cli.generators._shared import _fingerprint_prefix

        result = _fingerprint_prefix({}, "core_fingerprint")
        assert result == "N/A"

    def test_returns_na_when_value_empty(self) -> None:
        from providence_cli.generators._shared import _fingerprint_prefix

        result = _fingerprint_prefix({"core_fingerprint": ""}, "core_fingerprint")
        assert result == "N/A"

    def test_returns_value_truncated_to_size(self) -> None:
        from providence_cli.generators._shared import _fingerprint_prefix

        result = _fingerprint_prefix(
            {"core_fingerprint": "abcdef1234567890"}, "core_fingerprint", size=8
        )
        assert result == "abcdef12"

    def test_full_value_when_shorter_than_size(self) -> None:
        from providence_cli.generators._shared import _fingerprint_prefix

        result = _fingerprint_prefix({"k": "abc"}, "k", size=32)
        assert result == "abc"


class TestFormatRules:
    def test_empty_returns_no_mandatory_rules(self) -> None:
        from providence_cli.generators._shared import _format_rules

        result = _format_rules([])
        assert "No mandatory rules" in result

    def test_single_rule_formatted(self) -> None:
        from providence_cli.generators._shared import _format_rules

        rules = [{"name": "Rule A", "description": "Do this"}]
        result = _format_rules(rules)
        assert "Rule A" in result
        assert "Do this" in result

    def test_multiple_rules_numbered(self) -> None:
        from providence_cli.generators._shared import _format_rules

        rules = [
            {"name": "A", "description": "desc A"},
            {"name": "B", "description": "desc B"},
        ]
        result = _format_rules(rules)
        assert "1." in result
        assert "2." in result

    def test_missing_name_uses_default(self) -> None:
        from providence_cli.generators._shared import _format_rules

        rules = [{"description": "desc"}]
        result = _format_rules(rules)
        assert "Rule 1" in result

    def test_missing_description_uses_default(self) -> None:
        from providence_cli.generators._shared import _format_rules

        rules = [{"name": "MyRule"}]
        result = _format_rules(rules)
        assert "No description" in result


class TestCollectInstructionSections:
    def _make_item(
        self, item_type: str = "", meta_type: str = "", criticality: str = ""
    ) -> dict[str, Any]:
        return {
            "type": item_type,
            "metadata": {"type": meta_type, "criticality": criticality},
            "id": "X001",
            "name": "Item",
            "description": "desc",
        }

    def test_mandate_type_classified_as_mandate(self) -> None:
        from providence_cli.generators._shared import _collect_instruction_sections

        config = {"items": [self._make_item("MANDATE")]}
        sections = _collect_instruction_sections(config)
        assert len(sections["mandates"]) == 1
        assert len(sections["guidelines"]) == 0

    def test_guideline_type_classified_as_guideline(self) -> None:
        from providence_cli.generators._shared import _collect_instruction_sections

        config = {"items": [self._make_item("GUIDELINE")]}
        sections = _collect_instruction_sections(config)
        assert len(sections["guidelines"]) == 1

    def test_decision_type_classified_as_decision(self) -> None:
        from providence_cli.generators._shared import _collect_instruction_sections

        config = {"items": [self._make_item("DECISION")]}
        sections = _collect_instruction_sections(config)
        assert len(sections["decisions"]) == 1

    def test_empty_items_all_empty_lists(self) -> None:
        from providence_cli.generators._shared import _collect_instruction_sections

        config: dict[str, Any] = {"items": []}
        sections = _collect_instruction_sections(config)
        assert sections["mandates"] == []
        assert sections["guidelines"] == []
        assert sections["decisions"] == []
        assert sections["items"] == []

    def test_mandatory_criticality_classified_as_mandate(self) -> None:
        from providence_cli.generators._shared import _collect_instruction_sections

        config = {"items": [self._make_item(criticality="MANDATORY")]}
        sections = _collect_instruction_sections(config)
        assert len(sections["mandates"]) == 1

    def test_unknown_item_defaults_to_guideline(self) -> None:
        from providence_cli.generators._shared import _collect_instruction_sections

        config = {"items": [self._make_item("UNKNOWN", "", "")]}
        sections = _collect_instruction_sections(config)
        assert len(sections["guidelines"]) == 1


class TestRenderClaudeBootstrapSections:
    def test_returns_non_empty_list(self) -> None:
        from providence_cli.generators._shared import _render_claude_bootstrap_sections

        result = _render_claude_bootstrap_sections()
        assert len(result) > 0

    def test_contains_bootstrap_header(self) -> None:
        from providence_cli.generators._shared import _render_claude_bootstrap_sections

        result = _render_claude_bootstrap_sections()
        joined = "\n".join(result)
        assert "Agent Entrypoint" in joined

    def test_contains_git_protocol(self) -> None:
        from providence_cli.generators._shared import _render_claude_bootstrap_sections

        result = _render_claude_bootstrap_sections()
        joined = "\n".join(result)
        assert "Git" in joined


class TestRenderInstructionDocument:
    def _make_config(self, items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        return {
            "core_fingerprint": "abc123",
            "client_fingerprint": "def456",
            "items": items or [],
        }

    def test_returns_string(self) -> None:
        from providence_cli.generators._shared import _render_instruction_document

        result = _render_instruction_document(
            "Claude", ["# Header"], self._make_config()
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_tool_name(self) -> None:
        from providence_cli.generators._shared import _render_instruction_document

        result = _render_instruction_document("Claude", [], self._make_config())
        assert "Claude" in result

    def test_includes_claude_bootstrap_for_claude(self) -> None:
        from providence_cli.generators._shared import _render_instruction_document

        result = _render_instruction_document("Claude", [], self._make_config())
        assert "Agent Entrypoint" in result

    def test_no_bootstrap_for_other_tool(self) -> None:
        from providence_cli.generators._shared import _render_instruction_document

        result = _render_instruction_document("Cursor", [], self._make_config())
        assert "Agent Entrypoint" not in result

    def test_mandate_items_in_output(self) -> None:
        from providence_cli.generators._shared import _render_instruction_document

        items = [
            {
                "id": "M001",
                "type": "MANDATE",
                "name": "Test Mandate",
                "description": "do it",
                "metadata": {},
            }
        ]
        result = _render_instruction_document("Claude", [], self._make_config(items))
        assert "M001" in result

    def test_no_items_shows_governance_context(self) -> None:
        from providence_cli.generators._shared import _render_instruction_document

        result = _render_instruction_document("Claude", [], self._make_config())
        assert "Governance" in result

    def test_guideline_title_whitespace_falls_back_to_id(self) -> None:
        from providence_cli.generators._shared import _render_instruction_document

        items = [
            {
                "id": "G001",
                "type": "GUIDELINE",
                "title": "   ",
                "description": "Prefer DTO boundaries.",
                "metadata": {},
            }
        ]
        result = _render_instruction_document("Claude", [], self._make_config(items))
        assert "**[G001] G001**: Prefer DTO boundaries." in result

    def test_guideline_with_description_does_not_use_unavailable_placeholder(
        self,
    ) -> None:
        from providence_cli.generators._shared import _render_instruction_document

        items = [
            {
                "id": "G001",
                "type": "GUIDELINE",
                "title": "Dependency inversion",
                "description": "Inject interfaces rather than concrete implementations.",
                "metadata": {},
            }
        ]
        result = _render_instruction_document("Claude", [], self._make_config(items))
        assert "(description unavailable)" not in result


# ---------------------------------------------------------------------------
# _seeds: generate_agent_seeds
# ---------------------------------------------------------------------------


class TestGenerateAgentSeeds:
    def _make_config(self) -> dict[str, Any]:
        return {
            "core_fingerprint": "abc12345678901234567",
            "client_fingerprint": "def12345678901234567",
            "items": [
                {
                    "id": "M001",
                    "type": "MANDATE",
                    "name": "Rule 1",
                    "description": "desc1",
                    "is_immutable": True,
                },
                {
                    "id": "G001",
                    "type": "GUIDELINE",
                    "name": "Guide 1",
                    "description": "desc2",
                    "is_immutable": False,
                },
            ],
        }

    def test_returns_list_of_results(self, tmp_path: Path) -> None:
        from providence_cli.generators._seeds import generate_agent_seeds

        results = generate_agent_seeds(tmp_path, self._make_config())
        assert isinstance(results, list)
        assert len(results) > 0

    def test_creates_files_in_output_dir(self, tmp_path: Path) -> None:
        from providence_cli.generators._seeds import generate_agent_seeds

        generate_agent_seeds(tmp_path, self._make_config())
        files = list(tmp_path.glob("*.md"))
        assert len(files) >= 5  # cursor, copilot, generic, claude, gemini, antigravity

    def test_each_result_is_tuple_of_three(self, tmp_path: Path) -> None:
        from providence_cli.generators._seeds import generate_agent_seeds

        results = generate_agent_seeds(tmp_path, self._make_config())
        for r in results:
            assert len(r) == 3
            label, path, status = r
            assert isinstance(label, str)
            assert isinstance(path, Path)
            assert status == "Generated"

    def test_claude_agent_file_contains_bootstrap(self, tmp_path: Path) -> None:
        from providence_cli.generators._seeds import generate_agent_seeds

        generate_agent_seeds(tmp_path, self._make_config())
        claude_file = tmp_path / "claude-agent.md"
        assert claude_file.exists()
        content = claude_file.read_text(encoding="utf-8")
        assert "Agent Entrypoint" in content

    def test_cursor_agent_file_created(self, tmp_path: Path) -> None:
        from providence_cli.generators._seeds import generate_agent_seeds

        generate_agent_seeds(tmp_path, self._make_config())
        assert (tmp_path / "cursor-agent.md").exists()

    def test_empty_items_still_generates_files(self, tmp_path: Path) -> None:
        from providence_cli.generators._seeds import generate_agent_seeds

        config: dict[str, Any] = {
            "core_fingerprint": "abc",
            "client_fingerprint": "def",
            "items": [],
        }
        results = generate_agent_seeds(tmp_path, config)
        assert len(results) > 0

    def test_creates_output_dir_if_missing(self, tmp_path: Path) -> None:
        from providence_cli.generators._seeds import generate_agent_seeds

        output = tmp_path / "new_dir" / "seeds"
        generate_agent_seeds(output, self._make_config())
        assert output.is_dir()

    def test_seed_content_prefers_sdd_authority(self, tmp_path: Path) -> None:
        from providence_cli.generators._seeds import generate_agent_seeds

        generate_agent_seeds(tmp_path, self._make_config())
        content = (tmp_path / "generic-agent.md").read_text(encoding="utf-8")
        assert ".providence/" in content
        assert "compiled/" in content
        assert "source/" in content
        assert "docs/spec/canonical/" not in content
