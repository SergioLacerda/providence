"""A stale `final-template` build must never be deployed.

The dead hook adapters of this workspace were deployed from a `final-template`
built by an outdated generator and nothing noticed. Deployment now verifies the
hook artifacts it is about to ship against the current generator template.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from providence_wizard.orchestration.prompt_submit_hook_script import (
    PROMPT_SUBMIT_HOOK_SCRIPT,
)
from providence_wizard.orchestration.wizard._direct_root_deploy import (
    StaleFinalTemplateError,
    deploy_to_root,
)

_HOOK = Path(".providence") / "runtime" / "hooks" / "prompt-submit.py"


def _template(root: Path, hook_text: str | None = PROMPT_SUBMIT_HOOK_SCRIPT) -> Path:
    final = root / "final-template"
    (final / ".providence").mkdir(parents=True)
    (final / ".providence" / "metadata.json").write_text(
        json.dumps({"governance_fingerprint": "abc"}), encoding="utf-8"
    )
    (final / "README.md").write_text("readme", encoding="utf-8")
    if hook_text is not None:
        hook = final / _HOOK
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_text(hook_text, encoding="utf-8")
    return final


def test_current_final_template_deploys(tmp_path: Path) -> None:
    final = _template(tmp_path)
    target = tmp_path / "project"
    target.mkdir()

    result = deploy_to_root(target_root=target, final_template_dir=final)

    assert (target / _HOOK).read_text(encoding="utf-8") == PROMPT_SUBMIT_HOOK_SCRIPT
    assert "README.md" in result.created


def test_template_without_hook_artifacts_still_deploys(tmp_path: Path) -> None:
    final = _template(tmp_path, hook_text=None)
    target = tmp_path / "project"
    target.mkdir()

    result = deploy_to_root(target_root=target, final_template_dir=final)

    assert "README.md" in result.created


def test_stale_hook_is_refused_and_nothing_is_written(tmp_path: Path) -> None:
    final = _template(tmp_path, hook_text="#!/usr/bin/env python3\n# old hook\n")
    target = tmp_path / "project"
    target.mkdir()

    with pytest.raises(StaleFinalTemplateError) as excinfo:
        deploy_to_root(target_root=target, final_template_dir=final)

    assert "prompt-submit.py" in str(excinfo.value)
    assert list(target.iterdir()) == []


@pytest.mark.parametrize(
    ("relative", "content"),
    [
        (
            ".claude/settings.json",
            '{"hooks": {"UserPromptSubmit": [{"hooks": [{"command": '
            "\"sh -c 'hook=$1; exec python3 $hook' sh /x/prompt-submit.py\"}]}]}}",
        ),
        (".codex/config.toml", 'command = "python3 sdd-governance-inject.py"\n'),
    ],
)
def test_adapter_with_a_retired_shape_is_refused(
    tmp_path: Path, relative: str, content: str
) -> None:
    final = _template(tmp_path)
    adapter = final / relative
    adapter.parent.mkdir(parents=True, exist_ok=True)
    adapter.write_text(content, encoding="utf-8")
    target = tmp_path / "project"
    target.mkdir()

    with pytest.raises(StaleFinalTemplateError) as excinfo:
        deploy_to_root(target_root=target, final_template_dir=final)

    assert relative in str(excinfo.value)
    assert list(target.iterdir()) == []
