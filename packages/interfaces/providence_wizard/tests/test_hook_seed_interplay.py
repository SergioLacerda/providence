"""Seeds and prompt-submit hook adapters write the same agent config files.

`.claude/settings.json` (PreToolUse seed + UserPromptSubmit hook) and
`.gemini/settings.json` (contextFileName seed + BeforeAgent hook) are shared, so
the final content must not depend on which generator ran first, nor on how
often they run.  Hermetic: everything is generated under `tmp_path`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from providence_wizard.orchestration.prompt_submit_hooks import (
    PromptSubmitHookGenerator,
    central_prompt_submit_command,
)
from providence_wizard.orchestration.seedlings.ai_seeds import AISeedsGenerator

pytestmark = pytest.mark.usefixtures("hermetic_env")

_FINGERPRINT = "3c92a54d04d29611"
_MANDATES = ["M001", "M002", "M003"]


def _seeds(root: Path) -> AISeedsGenerator:
    seedlings_dir = root / ".providence" / "seedlings"
    seedlings_dir.mkdir(parents=True, exist_ok=True)
    return AISeedsGenerator(
        output_base=root,
        seedlings_dir=seedlings_dir,
        config={"language": "python", "adoption_level": "standard"},
        spec_fingerprint=_FINGERPRINT,
        mandate_ids=_MANDATES,
        active_categories=["testing"],
        generated_at="2026-09-20T00:00:00Z",
        verbose=False,
    )


def _hooks(root: Path) -> PromptSubmitHookGenerator:
    return PromptSubmitHookGenerator(root, {"claude", "codex", "gemini", "copilot"})


def _read(root: Path, relative: str) -> dict[str, object]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _assert_claude(root: Path) -> None:
    settings = _read(root, ".claude/settings.json")
    hooks = settings["hooks"]
    assert hooks["PreToolUse"][0]["hooks"][0]["command"] == (
        ".claude/providence-bootstrap.sh"
    )
    prompt_hooks = hooks["UserPromptSubmit"]
    assert len(prompt_hooks) == 1
    assert prompt_hooks[0]["hooks"][0]["command"] == central_prompt_submit_command(root)


def _assert_gemini(root: Path) -> None:
    settings = _read(root, ".gemini/settings.json")
    assert settings["contextFileName"] == "GEMINI.md"
    before_agent = settings["hooks"]["BeforeAgent"]
    assert len(before_agent) == 1
    assert before_agent[0]["hooks"][0]["command"] == central_prompt_submit_command(root)


@pytest.mark.parametrize(
    "seeds_first", [True, False], ids=["seeds-first", "hooks-first"]
)
def test_claude_and_gemini_config_is_independent_of_generator_order(
    tmp_path: Path, seeds_first: bool
) -> None:
    def seeds() -> None:
        assert _seeds(tmp_path).generate_claude_seed()
        assert _seeds(tmp_path).generate_gemini_seed()

    if seeds_first:
        seeds()
        assert _hooks(tmp_path).generate()
    else:
        assert _hooks(tmp_path).generate()
        seeds()

    _assert_claude(tmp_path)
    _assert_gemini(tmp_path)


def test_repeated_generation_keeps_a_single_hook_entry(tmp_path: Path) -> None:
    for _ in range(3):
        _seeds(tmp_path).generate_claude_seed()
        _seeds(tmp_path).generate_gemini_seed()
        _hooks(tmp_path).generate()

    _assert_claude(tmp_path)
    _assert_gemini(tmp_path)


def test_gemini_seed_keeps_user_settings_outside_its_own_key(tmp_path: Path) -> None:
    settings_path = tmp_path / ".gemini" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps({"theme": "dark", "contextFileName": "OLD.md"}), encoding="utf-8"
    )

    assert _seeds(tmp_path).generate_gemini_seed()

    settings = _read(tmp_path, ".gemini/settings.json")
    assert settings == {"theme": "dark", "contextFileName": "GEMINI.md"}


def test_copilot_seed_and_hook_files_do_not_overlap(tmp_path: Path) -> None:
    """Copilot instructions live in `.github/copilot-instructions.md`; the hook
    adapter owns `.github/hooks/`. Neither generator may remove the other."""
    assert _seeds(tmp_path).generate_copilot_seed()
    assert _hooks(tmp_path).generate()
    assert _seeds(tmp_path).generate_copilot_seed()

    assert (tmp_path / ".github" / "copilot-instructions.md").exists()
    assert (tmp_path / ".github" / "hooks" / "providence-prompt-submit.json").exists()


def test_antigravity_seed_does_not_touch_gemini_hook_settings(tmp_path: Path) -> None:
    """Antigravity reads the Gemini config; its seed lives under
    `.gemini/antigravity/` and must leave `.gemini/settings.json` alone."""
    assert _hooks(tmp_path).generate()
    before = (tmp_path / ".gemini" / "settings.json").read_bytes()

    assert _seeds(tmp_path).generate_antigravity_seed()

    assert (tmp_path / ".gemini" / "settings.json").read_bytes() == before
    assert (
        tmp_path / ".gemini" / "antigravity" / "antigravity-instructions.md"
    ).exists()
