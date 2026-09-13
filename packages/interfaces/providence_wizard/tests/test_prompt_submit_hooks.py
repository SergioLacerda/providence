"""Tests for prompt-submit governance hook generation."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import tomllib

from providence_wizard.orchestration.prompt_submit_hooks import (
    CENTRAL_PROMPT_SUBMIT_COMMAND,
    CENTRAL_PROMPT_SUBMIT_HOOK,
    PromptSubmitHookGenerator,
    central_prompt_submit_command,
    resolve_prompt_submit_hook_agents,
)

# Faking a bare `providence` command that Windows will actually spawn requires a
# real .exe: `CreateProcess` only auto-appends the .exe suffix when
# resolving an extensionless command, never .bat/.cmd, so a shebenv script
# on PATH there is silently skipped in favor of any real `providence` install.
# These tests only cover subprocess plumbing already proven correct on
# Linux CI, so skip the unreliable simulation on Windows rather than fight
# process-launch semantics in the fixture.
_SKIP_FAKE_SDD_REASON = (
    "Windows CreateProcess doesn't resolve bare commands to .bat/.cmd, so a "
    "fake `providence` on PATH can't be simulated reliably here; covered on Linux CI."
)


def _write_fake_sdd(bin_dir: Path, body_lines: list[str]) -> None:
    """Write a fake `providence` command on PATH that a subprocess can invoke."""
    script = "\n".join(["#!/usr/bin/env python3", *body_lines]) + "\n"
    fake_providence = bin_dir / "providence"
    fake_providence.write_text(script, encoding="utf-8")
    fake_providence.chmod(0o755)


def test_resolve_prompt_submit_hook_agents_defaults_to_all_supported() -> None:
    assert resolve_prompt_submit_hook_agents(None) == {"claude", "codex", "gemini"}


def test_resolve_prompt_submit_hook_agents_filters_selection() -> None:
    selected = {"governance", "claude", "verify"}

    assert resolve_prompt_submit_hook_agents(selected) == {"claude"}


def test_prompt_submit_hook_generator_writes_central_hook_and_selected_adapter(
    tmp_path: Path,
) -> None:
    generator = PromptSubmitHookGenerator(tmp_path, {"codex"})

    assert generator.generate() is True

    central_hook = tmp_path / CENTRAL_PROMPT_SUBMIT_HOOK
    assert central_hook.exists()
    central_hook_text = central_hook.read_text(encoding="utf-8")
    assert ".providence/runtime/hook-disabled" in central_hook_text
    assert "PROVIDENCE GOVERNANCE ACTIVE" in central_hook_text
    assert "prompt-submit-hook" in central_hook_text
    codex_config = tmp_path / ".codex" / "config.toml"
    codex_config_text = codex_config.read_text(encoding="utf-8")
    codex_toml = tomllib.loads(codex_config_text)
    assert codex_toml["hooks"]["UserPromptSubmit"][0]["hooks"][0][
        "command"
    ] == central_prompt_submit_command(tmp_path)
    assert CENTRAL_PROMPT_SUBMIT_COMMAND not in codex_config_text
    assert not (tmp_path / ".claude" / "settings.json").exists()
    assert not (tmp_path / ".gemini" / "settings.json").exists()


@pytest.mark.skipif(sys.platform == "win32", reason="launcher uses POSIX sh")
def test_prompt_submit_launcher_exits_zero_when_central_hook_is_missing(
    tmp_path: Path,
) -> None:
    command = central_prompt_submit_command(tmp_path)

    result = subprocess.run(
        command,
        input=json.dumps({"prompt": "implement C"}),
        cwd=tmp_path,
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_prompt_submit_hook_generator_merges_gemini_settings(tmp_path: Path) -> None:
    settings_path = tmp_path / ".gemini" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text('{"contextFileName": "GEMINI.md"}', encoding="utf-8")
    generator = PromptSubmitHookGenerator(tmp_path, {"gemini"})

    assert generator.generate() is True

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert settings["contextFileName"] == "GEMINI.md"
    assert settings["hooks"]["BeforeAgent"][0]["hooks"][0][
        "command"
    ] == central_prompt_submit_command(tmp_path)


def test_prompt_submit_hook_generator_merges_claude_settings(tmp_path: Path) -> None:
    """The UserPromptSubmit adapter must not clobber a pre-existing PreToolUse
    hook — e.g. one `ai_seeds.generate_claude_seed()` already wrote. See
    `.analysis/refined/20260913-providence-seeds-entrypoint-brand-refinement/design.md` § 4."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "PreToolUse": [
                        {
                            "matcher": ".*",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": ".claude/providence-bootstrap.sh",
                                }
                            ],
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )
    generator = PromptSubmitHookGenerator(tmp_path, {"claude"})

    assert generator.generate() is True

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == (
        ".claude/providence-bootstrap.sh"
    )
    assert settings["hooks"]["UserPromptSubmit"][0]["hooks"][0][
        "command"
    ] == central_prompt_submit_command(tmp_path)


def test_prompt_submit_hook_generator_writes_claude_settings(tmp_path: Path) -> None:
    """Regression (SQ-001): Claude adapter generation, not previously covered here."""
    generator = PromptSubmitHookGenerator(tmp_path, {"claude"})

    assert generator.generate() is True

    claude_settings = tmp_path / ".claude" / "settings.json"
    assert claude_settings.exists()
    settings = json.loads(claude_settings.read_text(encoding="utf-8"))
    assert settings["hooks"]["UserPromptSubmit"][0]["hooks"][0][
        "command"
    ] == central_prompt_submit_command(tmp_path)
    assert not (tmp_path / ".codex" / "config.toml").exists()
    assert not (tmp_path / ".gemini" / "settings.json").exists()


def test_prompt_submit_hook_generator_all_three_agents_together(
    tmp_path: Path,
) -> None:
    """Regression (SQ-001): default (no restriction) generates all three adapters."""
    generator = PromptSubmitHookGenerator(
        tmp_path, resolve_prompt_submit_hook_agents(None)
    )

    assert generator.generate() is True

    claude_settings = json.loads(
        (tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8")
    )
    assert claude_settings["hooks"]["UserPromptSubmit"][0]["hooks"][0][
        "command"
    ] == central_prompt_submit_command(tmp_path)
    codex_toml = tomllib.loads(
        (tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8")
    )
    assert codex_toml["hooks"]["UserPromptSubmit"][0]["hooks"][0][
        "command"
    ] == central_prompt_submit_command(tmp_path)
    gemini_settings = json.loads(
        (tmp_path / ".gemini" / "settings.json").read_text(encoding="utf-8")
    )
    assert gemini_settings["hooks"]["BeforeAgent"][0]["hooks"][0][
        "command"
    ] == central_prompt_submit_command(tmp_path)


def test_phase6_output_validator_imports_stay_in_sync_with_prompt_submit_hooks() -> (
    None
):
    """Regression (SQ-001): guards the hidden cross-module coupling Ranger found
    phase6_output_validator.py imports these three names directly from
    prompt_submit_hooks.py; if they were ever renamed here without updating that
    import, this test fails loudly instead of the coupling breaking silently."""
    from providence_wizard.orchestration import phase6_output_validator as validator_mod
    from providence_wizard.orchestration import prompt_submit_hooks as hooks_mod

    assert (
        validator_mod.CENTRAL_PROMPT_SUBMIT_COMMAND
        is hooks_mod.CENTRAL_PROMPT_SUBMIT_COMMAND
    )
    assert (
        validator_mod.CENTRAL_PROMPT_SUBMIT_HOOK is hooks_mod.CENTRAL_PROMPT_SUBMIT_HOOK
    )
    assert (
        validator_mod.SUPPORTED_PROMPT_HOOK_AGENTS
        is hooks_mod.SUPPORTED_PROMPT_HOOK_AGENTS
    )


@pytest.mark.skipif(sys.platform == "win32", reason=_SKIP_FAKE_SDD_REASON)
def test_prompt_submit_hook_injects_governance_activation_header(
    tmp_path: Path,
) -> None:
    generator = PromptSubmitHookGenerator(tmp_path, {"codex"})
    generator.generate()
    (tmp_path / ".providence" / "metadata.json").write_text("{}", encoding="utf-8")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_sdd(
        bin_dir,
        [
            "print('governance=active fingerprint=58a087b3c9fb9ce2 mandates=16')",
            "print('intake_mode=none governance_mode=hard execution_gate=allowed')",
            "print('PROVIDENCE GOVERNANCE: drift=none | governance=ok | profile=default')",
        ],
    )

    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        [sys.executable, str(tmp_path / CENTRAL_PROMPT_SUBMIT_HOOK)],
        input=json.dumps({"prompt": "implement C"}),
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    context = payload["hookSpecificOutput"]["additionalContext"]
    assert context.startswith("PROVIDENCE GOVERNANCE ACTIVE")
    assert "source=prompt-submit-hook" in context
    assert "execution_gate=allowed" in context
    assert "fingerprint=58a087b3" in context
    assert "context injection only" in context
    assert "no provider delegation or implementation was executed" in context
    assert (
        "start your response with one short Providence governance status line"
        in context
    )
    assert "PROVIDENCE GOVERNANCE: drift=none" in context
    assert (
        "end your response with this compact footer: "
        "PROVIDENCE GOVERNANCE: drift=none | governance=ok | profile=default"
    ) in context


@pytest.mark.skipif(sys.platform == "win32", reason=_SKIP_FAKE_SDD_REASON)
def test_prompt_submit_hook_resolves_workspace_when_called_from_subdir(
    tmp_path: Path,
) -> None:
    generator = PromptSubmitHookGenerator(tmp_path, {"codex"})
    generator.generate()
    (tmp_path / ".providence" / "metadata.json").write_text("{}", encoding="utf-8")
    subdir = tmp_path / "apps" / "landing"
    subdir.mkdir(parents=True)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    marker_path = tmp_path / "cwd.marker"
    _write_fake_sdd(
        bin_dir,
        [
            "import os",
            f"open(r'{marker_path}', 'w').write(os.getcwd())",
            "print('governance=active fingerprint=58a087b3c9fb9ce2 mandates=16')",
            "print('execution_gate=allowed')",
        ],
    )

    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        [sys.executable, str(tmp_path / CENTRAL_PROMPT_SUBMIT_HOOK)],
        input=json.dumps({"prompt": "diagnose M015"}),
        cwd=subdir,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert json.loads(result.stdout)["hookSpecificOutput"]["hookEventName"] == (
        "UserPromptSubmit"
    )
    assert marker_path.read_text(encoding="utf-8") == str(tmp_path)


def test_prompt_submit_hook_skips_full_sdd_ask_for_explicit_slash_command(
    tmp_path: Path,
) -> None:
    """Spike follow-up (20260714-sdd-ask-single-entrypoint-spike, R-001
    preferred strategy): when the raw prompt starts with /sdd-ask, the hook
    must not run a full `providence ask` subprocess  the slash-command adapter
    performs the single full invocation for that turn instead."""
    generator = PromptSubmitHookGenerator(tmp_path, {"codex"})
    generator.generate()
    (tmp_path / ".providence" / "metadata.json").write_text("{}", encoding="utf-8")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    marker_path = tmp_path / "sdd-invoked.marker"
    _write_fake_sdd(
        bin_dir,
        [
            f"open(r'{marker_path}', 'w').close()",
            "print('governance=active fingerprint=58a087b3c9fb9ce2 mandates=16')",
            "print('execution_gate=allowed')",
        ],
    )

    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        [sys.executable, str(tmp_path / CENTRAL_PROMPT_SUBMIT_HOOK)],
        input=json.dumps({"prompt": "/sdd-ask implementar X"}),
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert not marker_path.exists(), (
        "hook must not invoke `providence ask` a second time"
    )
    payload = json.loads(result.stdout)
    context = payload["hookSpecificOutput"]["additionalContext"]
    assert "entrypoint=explicit_command" in context
    assert "explicit_command=sdd-ask" in context
    assert "context injection only" in context
    assert "no provider delegation or implementation was executed" in context


@pytest.mark.skipif(sys.platform == "win32", reason=_SKIP_FAKE_SDD_REASON)
def test_prompt_submit_hook_runs_full_path_for_non_slash_prompt(
    tmp_path: Path,
) -> None:
    """A plain prompt (no /sdd-ask prefix) must still run the full `providence ask`
    path exactly as before, with SDD_ASK_ENTRYPOINT=hook set so the CLI can
    report `entrypoint: hook` in its structured output."""
    generator = PromptSubmitHookGenerator(tmp_path, {"codex"})
    generator.generate()
    (tmp_path / ".providence" / "metadata.json").write_text("{}", encoding="utf-8")

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    env_marker_path = tmp_path / "entrypoint-env.marker"
    _write_fake_sdd(
        bin_dir,
        [
            "import os",
            f"open(r'{env_marker_path}', 'w').write(os.environ.get('SDD_ASK_ENTRYPOINT', ''))",
            "print('governance=active fingerprint=58a087b3c9fb9ce2 mandates=16')",
            "print('execution_gate=allowed')",
        ],
    )

    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        [sys.executable, str(tmp_path / CENTRAL_PROMPT_SUBMIT_HOOK)],
        input=json.dumps({"prompt": "implementar X"}),
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert env_marker_path.exists(), (
        "hook must still invoke `providence ask` for non-slash prompts"
    )
    assert env_marker_path.read_text(encoding="utf-8") == "hook"
    payload = json.loads(result.stdout)
    context = payload["hookSpecificOutput"]["additionalContext"]
    assert context.startswith("PROVIDENCE GOVERNANCE ACTIVE")


def test_prompt_submit_hook_explicit_command_includes_footer_instruction(
    tmp_path: Path,
) -> None:
    """Regression (20260913-governance-hooks-dogfood, F008): the explicit
    /sdd-ask branch must carry the same footer contract as the normal path,
    even though it defers its own `providence ask` call to the slash-command
    adapter for this turn (see .codex/skills/sdd-ask.prompt.md's own
    `PROVIDENCE GOVERNANCE` footer template, which this instruction mirrors)."""
    generator = PromptSubmitHookGenerator(tmp_path, {"codex"})
    generator.generate()
    (tmp_path / ".providence" / "metadata.json").write_text("{}", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(tmp_path / CENTRAL_PROMPT_SUBMIT_HOOK)],
        input=json.dumps({"prompt": "/sdd-ask verificar governance"}),
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "end your response with this compact footer" in context
    assert (
        "PROVIDENCE GOVERNANCE: drift=${status} | governance=${status} | "
        "profile=sdd-ask"
    ) in context


@pytest.mark.skipif(sys.platform == "win32", reason=_SKIP_FAKE_SDD_REASON)
def test_prompt_submit_hook_falls_back_to_workspace_venv_when_providence_not_on_path(
    tmp_path: Path,
) -> None:
    """Regression (20260913-governance-hooks-dogfood, F006): a bare `providence`
    lookup on PATH is not the only supported runtime shape. This repository's
    own dogfooded deployment only has `providence` installed under its
    `.venv/bin/`, not on PATH, so the hook must also try
    `<workspace_root>/.venv/bin/providence` before giving up."""
    generator = PromptSubmitHookGenerator(tmp_path, {"codex"})
    generator.generate()
    (tmp_path / ".providence" / "metadata.json").write_text("{}", encoding="utf-8")

    venv_bin = tmp_path / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    _write_fake_sdd(
        venv_bin,
        [
            "print('governance=active fingerprint=58a087b3c9fb9ce2 mandates=16')",
            "print('execution_gate=allowed')",
        ],
    )

    # Restrict PATH to simulate `providence` not being installed on it, but
    # keep the running interpreter's own directory reachable: the fake
    # `providence` script's `#!/usr/bin/env python3` shebang needs *some*
    # `python3` on PATH to exec, and on CI images that interpreter doesn't
    # necessarily live under /usr/bin or /bin (e.g. a pyenv/uv install).
    env = {key: value for key, value in os.environ.items() if key != "PATH"}
    env["PATH"] = os.pathsep.join(
        ("/usr/bin", "/bin", str(Path(sys.executable).parent))
    )
    result = subprocess.run(
        [sys.executable, str(tmp_path / CENTRAL_PROMPT_SUBMIT_HOOK)],
        input=json.dumps({"prompt": "implement C"}),
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    context = payload["hookSpecificOutput"]["additionalContext"]
    assert context.startswith("PROVIDENCE GOVERNANCE ACTIVE")


def test_prompt_submit_hook_silently_exits_when_providence_unavailable_anywhere(
    tmp_path: Path,
) -> None:
    """The hook must stay non-blocking when neither a PATH `providence` nor a
    `<workspace_root>/.venv/bin/providence` exists (e.g. a fresh clone before
    dependencies are installed)."""
    generator = PromptSubmitHookGenerator(tmp_path, {"codex"})
    generator.generate()
    (tmp_path / ".providence" / "metadata.json").write_text("{}", encoding="utf-8")

    env = {key: value for key, value in os.environ.items() if key != "PATH"}
    env["PATH"] = os.pathsep.join(("/usr/bin", "/bin"))
    result = subprocess.run(
        [sys.executable, str(tmp_path / CENTRAL_PROMPT_SUBMIT_HOOK)],
        input=json.dumps({"prompt": "implement C"}),
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout == ""


def test_relocating_generated_output_requires_regeneration_to_avoid_stale_command(
    tmp_path: Path,
) -> None:
    """Regression (20260913-governance-hooks-dogfood, F002/F010/F011): copying
    a generator's output tree to a new location  as the wizard's
    final-template consolidation (move) and direct-root deployment (copy)
    both do  does NOT rewrite the absolute command path baked in at
    generation time. This is the exact mechanism that left this repository's
    own deployed adapters pointing at a nonexistent `generated/client/compiled`
    path. Anything that relocates generated output MUST re-run
    `PromptSubmitHookGenerator` against the final destination."""
    staging = tmp_path / "staging"
    final = tmp_path / "final"
    PromptSubmitHookGenerator(staging, {"codex"}).generate()

    shutil.copytree(staging, final)
    stale_command = tomllib.loads(
        (final / ".codex" / "config.toml").read_text(encoding="utf-8")
    )["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]

    assert stale_command == central_prompt_submit_command(staging)
    assert str(staging) in stale_command
    assert str(final) not in stale_command

    PromptSubmitHookGenerator(final, {"codex"}).generate()
    fixed_command = tomllib.loads(
        (final / ".codex" / "config.toml").read_text(encoding="utf-8")
    )["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]

    assert fixed_command == central_prompt_submit_command(final)
    assert str(final) in fixed_command
