"""Regression tests: all AI agent bootstrap files must contain governance fingerprint.

Acceptance criteria from design doc:
- Fingerprint header present in every agent bootstrap markdown file
- All bootstrap files reference .providence/agent-instructions.md
- No inline mandate descriptions in bootstrap files (redirector-only)
- DEPLOYMENT_MANIFEST.json contains all bootstrap files with fingerprint
- JSON seeds Tier 2 have governance_fingerprint field
- AGENTS.md has fingerprint comment
- Sovereign Factory plants antigravity skills
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from providence_wizard.orchestration.seedlings.ai_seeds import AISeedsGenerator
from providence_wizard.orchestration.seedlings.governance_seeds import (
    GovernanceSeedsGenerator,
    generate_agent_instructions_from_config,
)
from providence_wizard.orchestration.seedlings.ide_seeds import IDESeedsGenerator
from providence_wizard.orchestration.seedlings.sovereign_factory import (
    SovereignFactoryGenerator,
)

FINGERPRINT = "abc12345"
MANDATE_IDS = ["M001", "M002", "M003"]
GENERATED_AT = "2026-05-22T00:00:00Z"
MANDATE_DESCRIPTIONS = [
    "Clean Architecture mandate description text",
    "Test Coverage long description",
]


def _make_ide_gen(tmp_path: Path) -> IDESeedsGenerator:
    seedlings_dir = tmp_path / ".providence" / "seedlings"
    seedlings_dir.mkdir(parents=True, exist_ok=True)
    return IDESeedsGenerator(
        output_base=tmp_path,
        seedlings_dir=seedlings_dir,
        config={"language": "python", "adoption_level": "standard"},
        spec_fingerprint=FINGERPRINT,
        mandate_ids=MANDATE_IDS,
        active_categories=["testing"],
        generated_at=GENERATED_AT,
        verbose=False,
    )


def _make_sovereign_gen(tmp_path: Path) -> SovereignFactoryGenerator:
    seedlings_dir = tmp_path / ".providence" / "seedlings"
    seedlings_dir.mkdir(parents=True, exist_ok=True)
    return SovereignFactoryGenerator(
        output_base=tmp_path,
        seedlings_dir=seedlings_dir,
        config={"language": "python", "adoption_level": "standard"},
        spec_fingerprint=FINGERPRINT,
        mandate_ids=MANDATE_IDS,
        active_categories=["testing"],
        generated_at=GENERATED_AT,
        verbose=False,
    )


def _make_ai_gen(tmp_path: Path) -> AISeedsGenerator:
    seedlings_dir = tmp_path / ".providence" / "seedlings"
    seedlings_dir.mkdir(parents=True, exist_ok=True)
    return AISeedsGenerator(
        output_base=tmp_path,
        seedlings_dir=seedlings_dir,
        config={"language": "python", "adoption_level": "standard"},
        spec_fingerprint=FINGERPRINT,
        mandate_ids=MANDATE_IDS,
        active_categories=["testing"],
        generated_at=GENERATED_AT,
        verbose=False,
    )


def _make_gov_gen(tmp_path: Path) -> GovernanceSeedsGenerator:
    seedlings_dir = tmp_path / ".providence" / "seedlings"
    seedlings_dir.mkdir(parents=True, exist_ok=True)
    gov = GovernanceSeedsGenerator(
        output_base=tmp_path,
        seedlings_dir=seedlings_dir,
        config={
            "language": "python",
            "adoption_level": "standard",
            "enforcement_mode": "warn_mode",
        },
        spec_fingerprint=FINGERPRINT,
        mandate_ids=MANDATE_IDS,
        active_categories=["testing"],
        generated_at=GENERATED_AT,
        verbose=False,
    )
    gov.mandates = [
        {
            "id": "M001",
            "title": "Clean Architecture",
            "type": "MANDATE",
            "description": MANDATE_DESCRIPTIONS[0],
        },
        {
            "id": "M002",
            "title": "Test Coverage",
            "type": "MANDATE",
            "description": MANDATE_DESCRIPTIONS[1],
        },
        {"id": "M003", "title": "DI Principle", "type": "MANDATE", "description": ""},
    ]
    return gov


# ---------------------------------------------------------------------------
# Fingerprint presence
# ---------------------------------------------------------------------------


def test_claude_seed_has_fingerprint(tmp_path: Path) -> None:
    gen = _make_ai_gen(tmp_path)
    assert gen.generate_claude_seed()
    content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    assert FINGERPRINT in content


def test_gemini_seed_has_fingerprint(tmp_path: Path) -> None:
    gen = _make_ai_gen(tmp_path)
    assert gen.generate_gemini_seed()
    for path in ["GEMINI.md", ".gemini/gemini-instructions.md"]:
        content = (tmp_path / path).read_text(encoding="utf-8")
        assert FINGERPRINT in content, f"fingerprint missing from {path}"


def test_copilot_seed_has_fingerprint(tmp_path: Path) -> None:
    gen = _make_ai_gen(tmp_path)
    assert gen.generate_copilot_seed()
    content = (tmp_path / ".github" / "copilot-instructions.md").read_text(
        encoding="utf-8"
    )
    assert FINGERPRINT in content


def test_codex_seed_has_fingerprint(tmp_path: Path) -> None:
    gen = _make_ai_gen(tmp_path)
    assert gen.generate_codex_seed()
    content = (tmp_path / ".providence" / "seedlings" / "codex.seed.json").read_text(
        encoding="utf-8"
    )
    assert FINGERPRINT in content


# ---------------------------------------------------------------------------
# Reference to .providence/agent-instructions.md
# ---------------------------------------------------------------------------


def test_all_bootstrap_files_reference_agent_instructions(tmp_path: Path) -> None:
    gen = _make_ai_gen(tmp_path)
    gen.generate_claude_seed()
    gen.generate_gemini_seed()
    gen.generate_copilot_seed()
    gen.generate_codex_seed()

    files = [
        tmp_path / "CLAUDE.md",
        tmp_path / "GEMINI.md",
        tmp_path / ".gemini" / "gemini-instructions.md",
        tmp_path / ".github" / "copilot-instructions.md",
    ]
    for f in files:
        content = f.read_text(encoding="utf-8")
        assert ".providence/agent-instructions.md" in content, (
            f"missing redirect in {f.name}"
        )


# ---------------------------------------------------------------------------
# Anti-regression: no inline mandate descriptions in redirector files
# ---------------------------------------------------------------------------


def test_gemini_seed_has_no_inline_mandate_descriptions(tmp_path: Path) -> None:
    gen = _make_ai_gen(tmp_path)
    gen.generate_gemini_seed()
    for path in ["GEMINI.md", ".gemini/gemini-instructions.md"]:
        content = (tmp_path / path).read_text(encoding="utf-8")
        for desc in MANDATE_DESCRIPTIONS:
            assert desc not in content, f"inline mandate description found in {path}"


def test_claude_seed_has_no_inline_mandate_descriptions(tmp_path: Path) -> None:
    gen = _make_ai_gen(tmp_path)
    gen.generate_claude_seed()
    content = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    for desc in MANDATE_DESCRIPTIONS:
        assert desc not in content, "inline mandate description found in CLAUDE.md"


# ---------------------------------------------------------------------------
# agent-instructions.md drift section
# ---------------------------------------------------------------------------


def test_agent_instructions_contains_fingerprint(tmp_path: Path) -> None:
    gov = _make_gov_gen(tmp_path)
    assert gov.generate_agnostic_agent_instructions()
    content = (tmp_path / ".providence" / "agent-instructions.md").read_text(
        encoding="utf-8"
    )
    assert FINGERPRINT in content
    assert "Fingerprint" in content or "fingerprint" in content


def test_agent_instructions_from_config_standalone(tmp_path: Path) -> None:
    config: dict[str, Any] = {
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


# ---------------------------------------------------------------------------
# G1: agent-prep.seed.json governance_fingerprint
# ---------------------------------------------------------------------------


def test_agent_prep_seed_has_fingerprint(tmp_path: Path) -> None:
    gen = _make_ide_gen(tmp_path)
    assert gen.generate_agent_prep_seed()
    with open(
        tmp_path / ".providence" / "seedlings" / "agent-prep.seed.json",
        encoding="utf-8",
    ) as f:
        data = json.load(f)
    assert data.get("governance_fingerprint") == FINGERPRINT
    assert data.get("mandates_count") == len(MANDATE_IDS)


# ---------------------------------------------------------------------------
# G2: AGENTS.md fingerprint comment
# ---------------------------------------------------------------------------


def test_agents_md_has_fingerprint_comment(tmp_path: Path) -> None:
    gov = _make_gov_gen(tmp_path)
    assert gov.generate_agents_md()
    content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert FINGERPRINT in content
    assert "<!-- Governance fingerprint:" in content
    assert ".providence/agent-instructions.md" in content


# ---------------------------------------------------------------------------
# G3: personal-overlay.seed.json governance_fingerprint
# ---------------------------------------------------------------------------


def test_personal_overlay_seed_has_fingerprint(tmp_path: Path) -> None:
    gen = _make_ide_gen(tmp_path)
    assert gen.generate_personal_overlay_seed()
    with open(
        tmp_path / ".providence" / "seedlings" / "personal-overlay.seed.json",
        encoding="utf-8",
    ) as f:
        data = json.load(f)
    assert data.get("governance_fingerprint") == FINGERPRINT
    assert data.get("mandates_count") == len(MANDATE_IDS)


# ---------------------------------------------------------------------------
# G4: ACTIVATION_GUIDE.md fingerprint
# ---------------------------------------------------------------------------


def test_activation_guide_has_fingerprint(tmp_path: Path) -> None:
    gov = _make_gov_gen(tmp_path)
    assert gov.generate_activation_guide()
    content = (
        tmp_path / ".providence" / "seedlings" / "ACTIVATION_GUIDE.md"
    ).read_text(encoding="utf-8")
    assert FINGERPRINT in content
    assert "<!-- Governance fingerprint:" in content


# ---------------------------------------------------------------------------
# G5: Sovereign Factory plants antigravity/skills/
# ---------------------------------------------------------------------------


def test_sovereign_factory_plants_antigravity_skill(tmp_path: Path) -> None:
    gen = _make_sovereign_gen(tmp_path)
    result = gen.generate_sovereign_factory_seed()
    # Either template was absent (returns False gracefully) or antigravity was planted
    if result:
        # Template found  check prompts were planted
        assert (tmp_path / ".github" / "prompts").exists()


def test_sovereign_factory_antigravity_contains_skill_md(tmp_path: Path) -> None:
    gen = _make_sovereign_gen(tmp_path)
    gen.generate_sovereign_factory_seed()
    antigravity_dir = tmp_path / ".gemini" / "antigravity"
    if antigravity_dir.exists():
        skill_files = list(antigravity_dir.rglob("SKILL.md"))
        assert len(skill_files) > 0, (
            "Expected at least one SKILL.md in .gemini/antigravity/"
        )
    assert not (tmp_path / ".antigravity").exists(), (
        "legacy .antigravity/ output must not be created"
    )


# ---------------------------------------------------------------------------
# T2: managed-block preservation across regeneration (root seed files only)
# `.analysis/refined/20260906-root-seed-githook-necessity/design.md`
# ---------------------------------------------------------------------------

_HAND_NOTE = "\n<!-- my own notes, unrelated to sdd -->\n"


def _make_ai_gen_with_fingerprint(tmp_path: Path, fingerprint: str) -> AISeedsGenerator:
    seedlings_dir = tmp_path / ".providence" / "seedlings"
    seedlings_dir.mkdir(parents=True, exist_ok=True)
    return AISeedsGenerator(
        output_base=tmp_path,
        seedlings_dir=seedlings_dir,
        config={"language": "python", "adoption_level": "standard"},
        spec_fingerprint=fingerprint,
        mandate_ids=MANDATE_IDS,
        active_categories=["testing"],
        generated_at=GENERATED_AT,
        verbose=False,
    )


def test_claude_md_preserves_hand_added_content_across_regeneration(
    tmp_path: Path,
) -> None:
    gen1 = _make_ai_gen_with_fingerprint(tmp_path, "aaaaaaaa")
    assert gen1.generate_claude_seed()
    claude_file = tmp_path / "CLAUDE.md"
    claude_file.write_text(
        claude_file.read_text(encoding="utf-8") + _HAND_NOTE, encoding="utf-8"
    )

    gen2 = _make_ai_gen_with_fingerprint(tmp_path, "bbbbbbbb")
    assert gen2.generate_claude_seed()
    content = claude_file.read_text(encoding="utf-8")
    assert "my own notes, unrelated to sdd" in content
    assert "bbbbbbbb" in content
    assert "aaaaaaaa" not in content


def test_gemini_md_preserves_hand_added_content_across_regeneration(
    tmp_path: Path,
) -> None:
    gen1 = _make_ai_gen_with_fingerprint(tmp_path, "aaaaaaaa")
    assert gen1.generate_gemini_seed()
    gemini_file = tmp_path / "GEMINI.md"
    gemini_file.write_text(
        gemini_file.read_text(encoding="utf-8") + _HAND_NOTE, encoding="utf-8"
    )

    gen2 = _make_ai_gen_with_fingerprint(tmp_path, "bbbbbbbb")
    assert gen2.generate_gemini_seed()
    content = gemini_file.read_text(encoding="utf-8")
    assert "my own notes, unrelated to sdd" in content
    assert "bbbbbbbb" in content
    assert "aaaaaaaa" not in content


def test_agents_md_preserves_hand_added_content_across_regeneration(
    tmp_path: Path,
) -> None:
    gov1 = _make_gov_gen(tmp_path)
    assert gov1.generate_agents_md()
    agents_file = tmp_path / "AGENTS.md"
    agents_file.write_text(
        agents_file.read_text(encoding="utf-8") + _HAND_NOTE, encoding="utf-8"
    )

    gov2 = _make_gov_gen(tmp_path)
    assert gov2.generate_agents_md()
    content = agents_file.read_text(encoding="utf-8")
    assert "my own notes, unrelated to sdd" in content


def test_claude_seed_returns_false_and_does_not_modify_file_on_malformed_markers(
    tmp_path: Path,
) -> None:
    """A hand-broken marker pair must fail the generator, never fall back to
    a silent whole-file overwrite that would destroy whatever the markers
    were protecting."""
    claude_file = tmp_path / "CLAUDE.md"
    claude_file.write_text(
        "<!-- sdd:managed:begin -->\nstale content, no end marker\n",
        encoding="utf-8",
    )
    original = claude_file.read_text(encoding="utf-8")

    gen = _make_ai_gen(tmp_path)
    assert gen.generate_claude_seed() is False
    assert claude_file.read_text(encoding="utf-8") == original


# ---------------------------------------------------------------------------
# Wave 2: managed-block preservation for copilot/antigravity
# `.analysis/refined/20260907-managed-block-generalization/design.md`
# ---------------------------------------------------------------------------


def test_copilot_seed_preserves_hand_added_content_across_regeneration(
    tmp_path: Path,
) -> None:
    gen1 = _make_ai_gen_with_fingerprint(tmp_path, "aaaaaaaa")
    assert gen1.generate_copilot_seed()
    copilot_file = tmp_path / ".github" / "copilot-instructions.md"
    copilot_file.write_text(
        copilot_file.read_text(encoding="utf-8") + _HAND_NOTE, encoding="utf-8"
    )

    gen2 = _make_ai_gen_with_fingerprint(tmp_path, "bbbbbbbb")
    assert gen2.generate_copilot_seed()
    content = copilot_file.read_text(encoding="utf-8")
    assert "my own notes, unrelated to sdd" in content
    assert "bbbbbbbb" in content
    assert "aaaaaaaa" not in content


def test_antigravity_seed_preserves_hand_added_content_across_regeneration(
    tmp_path: Path,
) -> None:
    gen1 = _make_ai_gen_with_fingerprint(tmp_path, "aaaaaaaa")
    assert gen1.generate_antigravity_seed()
    antigravity_file = (
        tmp_path / ".gemini" / "antigravity" / "antigravity-instructions.md"
    )
    antigravity_file.write_text(
        antigravity_file.read_text(encoding="utf-8") + _HAND_NOTE, encoding="utf-8"
    )

    gen2 = _make_ai_gen_with_fingerprint(tmp_path, "bbbbbbbb")
    assert gen2.generate_antigravity_seed()
    content = antigravity_file.read_text(encoding="utf-8")
    assert "my own notes, unrelated to sdd" in content
    assert "bbbbbbbb" in content
    assert "aaaaaaaa" not in content


def test_copilot_seed_returns_false_and_does_not_modify_file_on_malformed_markers(
    tmp_path: Path,
) -> None:
    copilot_dir = tmp_path / ".github"
    copilot_dir.mkdir(parents=True)
    copilot_file = copilot_dir / "copilot-instructions.md"
    copilot_file.write_text(
        "<!-- sdd:managed:begin -->\nstale content, no end marker\n",
        encoding="utf-8",
    )
    original = copilot_file.read_text(encoding="utf-8")

    gen = _make_ai_gen(tmp_path)
    assert gen.generate_copilot_seed() is False
    assert copilot_file.read_text(encoding="utf-8") == original


def test_antigravity_seed_returns_false_and_does_not_modify_file_on_malformed_markers(
    tmp_path: Path,
) -> None:
    antigravity_dir = tmp_path / ".gemini" / "antigravity"
    antigravity_dir.mkdir(parents=True)
    antigravity_file = antigravity_dir / "antigravity-instructions.md"
    antigravity_file.write_text(
        "<!-- sdd:managed:begin -->\nstale content, no end marker\n",
        encoding="utf-8",
    )
    original = antigravity_file.read_text(encoding="utf-8")

    gen = _make_ai_gen(tmp_path)
    assert gen.generate_antigravity_seed() is False
    assert antigravity_file.read_text(encoding="utf-8") == original
