"""Regression tests for governance_seeds refactor.

Verifies that the template extraction to _governance_templates.py did not
change any observable behaviour of GovernanceSeedsGenerator.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from providence_core.utils.text_io import read_text_utf8, write_text_utf8
from providence_wizard.orchestration.seedlings.governance_seeds import (
    GovernanceSeedsGenerator,
    generate_agent_instructions_from_config,
    generate_root_bootstrap_from_config,
)
from providence_wizard.templates.seedling_templates import (
    build_activation_guide,
    build_verification_script,
)

FINGERPRINT = "abc12345"
MANDATE_IDS = ["M001", "M002", "M003"]
GENERATED_AT = "2026-05-23T00:00:00Z"


def _make_gen(tmp_path: Path) -> GovernanceSeedsGenerator:
    seedlings_dir = tmp_path / ".providence" / "seedlings"
    seedlings_dir.mkdir(parents=True, exist_ok=True)
    gen = GovernanceSeedsGenerator(
        output_base=tmp_path,
        seedlings_dir=seedlings_dir,
        config={"language": "python", "adoption_level": "standard"},
        spec_fingerprint=FINGERPRINT,
        mandate_ids=MANDATE_IDS,
        active_categories=["testing"],
        generated_at=GENERATED_AT,
        verbose=False,
    )
    gen.mandates = [
        {"id": "M001", "title": "Clean Architecture"},
        {"id": "M002", "title": "Test Coverage"},
        {"id": "M003", "title": "Documentation"},
    ]
    return gen


def test_templates_module_has_activation_guide_template() -> None:
    result = build_activation_guide(
        fingerprint=FINGERPRINT,
        generated_at=GENERATED_AT,
        enforcement_label="Alertas (Warnings only)",
        enforcement_explanation="Show warnings but allow violations",
        enforcement_behavior="- **Violations show WARNINGS**",
        language="PYTHON",
        mandates_list=" M001: Clean Architecture",
        guidelines_list=" TESTING",
        mandate_ids_joined="M001, M002, M003",
    )
    assert "# Governance Activation Guide" in result
    assert f"<!-- Governance fingerprint: {FINGERPRINT} -->" in result
    assert GENERATED_AT in result
    assert "M001, M002, M003" in result


def test_templates_module_has_verification_script_template() -> None:
    result = build_verification_script(mandate_ids_str="M001', 'M002', 'M003")
    assert "#!/usr/bin/env python3" in result
    assert "class GovernanceVerifier" in result
    assert "M001" in result


def test_generate_activation_guide_uses_template(tmp_path: Path) -> None:
    gen = _make_gen(tmp_path)
    assert gen.generate_activation_guide() is True
    guide = read_text_utf8(
        tmp_path / ".providence" / "seedlings" / "ACTIVATION_GUIDE.md"
    )
    assert "# Governance Activation Guide" in guide
    assert f"<!-- Governance fingerprint: {FINGERPRINT} -->" in guide
    assert "M001" in guide


def test_generate_verification_script_uses_template(tmp_path: Path) -> None:
    gen = _make_gen(tmp_path)
    assert gen.generate_verification_script() is True
    script = read_text_utf8(tmp_path / ".providence" / "seedlings" / "verify.py")
    assert "class GovernanceVerifier" in script
    assert "M001" in script


def test_generate_agent_instructions_still_works(tmp_path: Path) -> None:
    config = {
        "items": [
            {
                "type": "MANDATE",
                "id": "M001",
                "title": "Clean Architecture",
                "description": "Layered design",
            },
            {"type": "MANDATE", "id": "M002", "title": "Test Coverage"},
        ],
        "core_fingerprint": FINGERPRINT,
    }
    assert generate_agent_instructions_from_config(tmp_path, config) is True
    instructions = read_text_utf8(tmp_path / ".providence" / "agent-instructions.md")
    assert "M001" in instructions
    assert FINGERPRINT in instructions
    assert "governance_fingerprint" in instructions
    assert "providence governance handshake --init" in instructions
    assert "providence governance handshake --response" in instructions


def test_generate_root_bootstrap_from_config_updates_root_files(tmp_path: Path) -> None:
    config = {
        "items": [
            {"type": "MANDATE", "id": "M001", "title": "Clean Architecture"},
            {"type": "MANDATE", "id": "M002", "title": "Test Coverage"},
        ],
        "core_fingerprint": FINGERPRINT,
    }
    assert generate_root_bootstrap_from_config(tmp_path, config) is True
    for filename in ("AGENTS.md", "CLAUDE.md", "GEMINI.md"):
        content = read_text_utf8(tmp_path / filename)
        assert FINGERPRINT in content
        assert "fingerprints.combined" in content
        assert "governance_fingerprint" not in content


def test_generate_root_bootstrap_from_config_preserves_hand_added_content(
    tmp_path: Path,
) -> None:
    """`providence governance compile` regenerates CLAUDE.md/AGENTS.md/GEMINI.md
    on every run — it must not destroy content a human or another tool added
    outside the managed block, the same guarantee AISeedsGenerator already
    provides. See
    `.analysis/refined/20260913-providence-seeds-entrypoint-brand-refinement/design.md` § 3."""
    config = {
        "items": [{"type": "MANDATE", "id": "M001", "title": "Clean Architecture"}],
        "core_fingerprint": FINGERPRINT,
    }
    hand_note = "\n<!-- hand-added notes, unrelated to governance -->\n"

    assert generate_root_bootstrap_from_config(tmp_path, config) is True
    for filename in ("AGENTS.md", "CLAUDE.md", "GEMINI.md"):
        path = tmp_path / filename
        write_text_utf8(path, read_text_utf8(path) + hand_note)

    config["core_fingerprint"] = "def67890"
    assert generate_root_bootstrap_from_config(tmp_path, config) is True

    for filename in ("AGENTS.md", "CLAUDE.md", "GEMINI.md"):
        content = read_text_utf8(tmp_path / filename)
        assert hand_note.strip() in content, (
            f"{filename} lost hand-added content across regeneration"
        )
        assert "def67890" in content
        assert FINGERPRINT not in content


def test_generate_root_bootstrap_from_config_does_not_overwrite_on_malformed_markers(
    tmp_path: Path,
) -> None:
    """Unbalanced managed-block markers must fail the regeneration (returns
    False) rather than silently falling back to a whole-file overwrite —
    same fail-closed guarantee as `AISeedsGenerator`."""
    config = {
        "items": [{"type": "MANDATE", "id": "M001", "title": "Clean Architecture"}],
        "core_fingerprint": FINGERPRINT,
    }
    claude_path = tmp_path / "CLAUDE.md"
    write_text_utf8(
        claude_path, "<!-- providence:managed:begin -->\nstale, no end marker\n"
    )

    assert generate_root_bootstrap_from_config(tmp_path, config) is False
    assert read_text_utf8(claude_path) == (
        "<!-- providence:managed:begin -->\nstale, no end marker\n"
    )


def test_governance_seeds_module_size_reduced() -> None:
    source = read_text_utf8(Path(inspect.getfile(GovernanceSeedsGenerator)))
    lines = source.splitlines()
    assert len(lines) < 900, (
        f"governance_seeds.py grew to {len(lines)} lines  "
        "verify that templates are still in templates/seedling_templates.py"
    )
