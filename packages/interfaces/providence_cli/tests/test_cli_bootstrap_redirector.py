"""Regression tests: providence governance generate must produce redirectors, not inline mandates.

Acceptance criteria:
- All agent instruction files from generate_agent_instruction_files() are redirectors
- All files contain governance fingerprint
- Copilot remains .providence-only redirector (unchanged)
- generate_agent_instructions_from_config() produces valid agent-instructions.md
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from providence_cli.generators._instruction_files import (
    generate_agent_instruction_files,
)
from providence_wizard.orchestration.seedlings.governance_seeds import (
    generate_agent_instructions_from_config,
)

FINGERPRINT = "21b6f7d81c88d0c0"
MANDATE_DESCRIPTION = (
    "Clean Architecture mandate long description text that should not appear inline"
)


def _sample_config() -> dict[str, Any]:
    return {
        "core_fingerprint": FINGERPRINT,
        "client_fingerprint": "792a262a16f8e344",
        "items": [
            {
                "id": "M001",
                "type": "MANDATE",
                "title": "Clean Architecture",
                "description": MANDATE_DESCRIPTION,
            },
            {
                "id": "M002",
                "type": "MANDATE",
                "title": "Test Coverage",
                "description": "Test coverage desc",
            },
            {
                "id": "G001",
                "type": "GUIDELINE",
                "title": "Style",
                "description": "Style desc",
            },
        ],
    }


# ---------------------------------------------------------------------------
# Fingerprint presence
# ---------------------------------------------------------------------------


def test_cli_claude_instructions_has_fingerprint(tmp_path: Path) -> None:
    generate_agent_instruction_files(tmp_path, _sample_config())
    content = (tmp_path / ".claude" / "claude-instructions.md").read_text(
        encoding="utf-8"
    )
    assert FINGERPRINT in content
    assert "fingerprints.combined" in content
    assert "governance_fingerprint" not in content


def test_cli_gemini_instructions_has_fingerprint(tmp_path: Path) -> None:
    generate_agent_instruction_files(tmp_path, _sample_config())
    content = (tmp_path / ".gemini" / "gemini-instructions.md").read_text(
        encoding="utf-8"
    )
    assert FINGERPRINT in content


def test_cli_vscode_instructions_has_fingerprint(tmp_path: Path) -> None:
    generate_agent_instruction_files(tmp_path, _sample_config())
    content = (tmp_path / ".vscode" / "ai-rules.md").read_text(encoding="utf-8")
    assert FINGERPRINT in content


def test_cli_cursor_instructions_has_fingerprint(tmp_path: Path) -> None:
    generate_agent_instruction_files(tmp_path, _sample_config())
    content = (tmp_path / ".cursor" / "rules" / "sdd-governance.mdc").read_text(
        encoding="utf-8"
    )
    assert FINGERPRINT in content


# ---------------------------------------------------------------------------
# Redirector: reference to .providence/agent-instructions.md
# ---------------------------------------------------------------------------


def test_cli_claude_instructions_is_redirector(tmp_path: Path) -> None:
    generate_agent_instruction_files(tmp_path, _sample_config())
    content = (tmp_path / ".claude" / "claude-instructions.md").read_text(
        encoding="utf-8"
    )
    assert ".providence/agent-instructions.md" in content


def test_cli_gemini_instructions_is_redirector(tmp_path: Path) -> None:
    generate_agent_instruction_files(tmp_path, _sample_config())
    content = (tmp_path / ".gemini" / "gemini-instructions.md").read_text(
        encoding="utf-8"
    )
    assert ".providence/agent-instructions.md" in content


def test_cli_vscode_instructions_is_redirector(tmp_path: Path) -> None:
    generate_agent_instruction_files(tmp_path, _sample_config())
    content = (tmp_path / ".vscode" / "ai-rules.md").read_text(encoding="utf-8")
    assert ".providence/agent-instructions.md" in content


def test_cli_cursor_instructions_is_redirector(tmp_path: Path) -> None:
    generate_agent_instruction_files(tmp_path, _sample_config())
    content = (tmp_path / ".cursor" / "rules" / "sdd-governance.mdc").read_text(
        encoding="utf-8"
    )
    assert ".providence/agent-instructions.md" in content


# ---------------------------------------------------------------------------
# Anti-regression: no inline mandate descriptions
# ---------------------------------------------------------------------------


def test_cli_claude_instructions_has_no_inline_mandates(tmp_path: Path) -> None:
    generate_agent_instruction_files(tmp_path, _sample_config())
    content = (tmp_path / ".claude" / "claude-instructions.md").read_text(
        encoding="utf-8"
    )
    assert MANDATE_DESCRIPTION not in content


def test_cli_gemini_instructions_has_no_inline_mandates(tmp_path: Path) -> None:
    generate_agent_instruction_files(tmp_path, _sample_config())
    content = (tmp_path / ".gemini" / "gemini-instructions.md").read_text(
        encoding="utf-8"
    )
    assert MANDATE_DESCRIPTION not in content


# ---------------------------------------------------------------------------
# Copilot unchanged (already redirector, no regression)
# ---------------------------------------------------------------------------


def test_cli_copilot_is_still_redirector(tmp_path: Path) -> None:
    generate_agent_instruction_files(tmp_path, _sample_config())
    content = (tmp_path / ".github" / "copilot-instructions.md").read_text(
        encoding="utf-8"
    )
    assert ".providence/agent-instructions.md" in content
    assert MANDATE_DESCRIPTION not in content


# ---------------------------------------------------------------------------
# generate_agent_instructions_from_config standalone
# ---------------------------------------------------------------------------


def test_standalone_agent_instructions_regeneration(tmp_path: Path) -> None:
    config = {
        "core_fingerprint": FINGERPRINT,
        "items": [
            {
                "id": "M001",
                "type": "MANDATE",
                "title": "Clean Architecture",
                "description": "desc",
            },
        ],
    }
    assert generate_agent_instructions_from_config(tmp_path, config)
    content = (tmp_path / ".providence" / "agent-instructions.md").read_text(
        encoding="utf-8"
    )
    assert FINGERPRINT in content
    assert "M001" in content
    assert "governance_fingerprint" in content


def test_standalone_agent_instructions_contains_fingerprint_section(
    tmp_path: Path,
) -> None:
    config = {"core_fingerprint": FINGERPRINT, "items": []}
    generate_agent_instructions_from_config(tmp_path, config)
    content = (tmp_path / ".providence" / "agent-instructions.md").read_text(
        encoding="utf-8"
    )
    assert "Fingerprint" in content or "fingerprint" in content
