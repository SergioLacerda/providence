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

from providence_wizard.orchestration.prompt_submit_hook_script import (
    PROMPT_SUBMIT_HOOK_SCRIPT,
)
from providence_wizard.orchestration.prompt_submit_hooks import (
    CENTRAL_PROMPT_SUBMIT_COMMAND,
    CENTRAL_PROMPT_SUBMIT_HOOK,
    HOOK_INTERNAL_TIMEOUT_SECONDS,
    PLATFORM_HOOK_TIMEOUT_SECONDS,
    HookGenerationError,
    PromptSubmitHookGenerator,
    central_prompt_submit_command,
    launcher_command,
    resolve_prompt_submit_hook_agents,
)

pytestmark = pytest.mark.usefixtures("hermetic_env")

_FAKE_CLI_BASENAME = "providence_fake_cli"
_FAKE_FINGERPRINT = "58a087b3c9fb9ce2"
_FAKE_METADATA = json.dumps({"fingerprints": {"combined": _FAKE_FINGERPRINT}})


def _write_fake_sdd(
    bin_dir: Path,
    body_lines: list[str],
    *,
    version: str = "1.0.99",
    version_log: Path | None = None,
    echo_entrypoint: bool = True,
    fingerprint: str | None = _FAKE_FINGERPRINT,
) -> None:
    """Write a fake `providence` command a subprocess can resolve via PATH.

    Like the real CLI it reports the entrypoint marker it was given and the
    workspace fingerprint, so the hook can verify the contract;
    `echo_entrypoint=False` models a CLI that does neither.

    On POSIX it is an executable script.  On Windows `CreateProcess` only runs
    real executables for a bare name, but `shutil.which` (used by the hook)
    resolves `providence.cmd` through PATHEXT to a full path that
    `subprocess.run` can launch, so a `.cmd` shim around a Python file works.
    """
    # The hook probes `providence --version` before trusting the CLI.
    guard = [
        "import sys",
        "if sys.argv[1:] == ['--version']:",
        *(
            [f"    open({str(version_log)!r}, 'a').write('probe\\n')"]
            if version_log is not None
            else []
        ),
        f"    print({version!r})",
        "    raise SystemExit(0)",
    ]
    echo = (
        [
            "import os",
            "print('entrypoint        : ' + "
            "os.environ.get('PROVIDENCE_ASK_ENTRYPOINT', 'explicit_command'))",
            *(
                [f"print('governance=fake fingerprint={fingerprint}')"]
                if fingerprint
                else []
            ),
        ]
        if echo_entrypoint and body_lines
        else []
    )
    body = "\n".join([*guard, *echo, *body_lines]) + "\n"
    if sys.platform == "win32":
        (bin_dir / f"{_FAKE_CLI_BASENAME}.py").write_text(body, encoding="utf-8")
        (bin_dir / "providence.cmd").write_text(
            f'@"{sys.executable}" "%~dp0{_FAKE_CLI_BASENAME}.py" %*\r\n',
            encoding="utf-8",
        )
        return
    fake_providence = bin_dir / "providence"
    fake_providence.write_text("#!/usr/bin/env python3\n" + body, encoding="utf-8")
    fake_providence.chmod(0o755)


def _governed(root: Path) -> Path:
    """Make `root` a governed project: `.git` boundary + workspace marker."""
    (root / ".git").mkdir(parents=True, exist_ok=True)
    (root / ".providence").mkdir(parents=True, exist_ok=True)
    (root / ".providence" / "metadata.json").write_text(
        _FAKE_METADATA, encoding="utf-8"
    )
    return root


def _empty_path_env(tmp_path: Path) -> dict[str, str]:
    """Environment whose PATH holds no `providence`, whatever the host has."""
    empty = tmp_path / "empty-bin"
    empty.mkdir(exist_ok=True)
    env = dict(os.environ)
    env["PATH"] = str(empty)
    return env


def test_resolve_prompt_submit_hook_agents_defaults_to_all_supported() -> None:
    assert resolve_prompt_submit_hook_agents(None) == {
        "claude",
        "codex",
        "gemini",
        "copilot",
        "devin",
    }


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
    assert (
        codex_toml["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        == central_prompt_submit_command()
    )
    assert CENTRAL_PROMPT_SUBMIT_COMMAND not in codex_config_text
    assert not (tmp_path / ".claude" / "settings.json").exists()
    assert not (tmp_path / ".gemini" / "settings.json").exists()


def test_prompt_submit_launcher_is_silent_in_an_ungoverned_project(
    tmp_path: Path,
) -> None:
    (tmp_path / ".git").mkdir()
    command = central_prompt_submit_command()

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


def test_prompt_submit_launcher_names_a_missing_central_hook(
    tmp_path: Path,
) -> None:
    """A governed workspace whose hook file is gone is a broken deployment, not
    an ungoverned project: the launcher says so on stderr and exits 0."""
    _governed(tmp_path)
    command = central_prompt_submit_command()

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
    assert "reason=hook_missing" in result.stderr


def test_prompt_submit_launcher_is_shell_agnostic() -> None:
    """The launcher must not depend on `sh` (absent from cmd.exe / PowerShell)
    nor use characters special to cmd.exe or PowerShell."""
    command = central_prompt_submit_command()

    assert not command.startswith("sh ")
    assert command.startswith(("python -c ", "python3 -c "))
    for special in ("$", "%", "`", "&", "|", "^"):
        assert special not in command
    assert CENTRAL_PROMPT_SUBMIT_HOOK.as_posix() in command


def test_prompt_submit_launcher_runs_hook_from_subdirectory(tmp_path: Path) -> None:
    hook = tmp_path / CENTRAL_PROMPT_SUBMIT_HOOK
    hook.parent.mkdir(parents=True)
    hook.write_text("import sys\nprint('ran:' + sys.stdin.read())\n", encoding="utf-8")
    _governed(tmp_path)
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    env = {k: v for k, v in os.environ.items() if k != "PROVIDENCE_WORKSPACE_ROOT"}

    result = subprocess.run(
        central_prompt_submit_command(),
        input="payload",
        cwd=nested,
        env=env,
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "ran:payload"


def test_prompt_submit_launcher_does_not_inherit_parent_governance(
    tmp_path: Path,
) -> None:
    """A project (has `.git`) without its own `.providence/` must stay
    ungoverned even when a parent directory is a governed workspace."""
    hook = tmp_path / CENTRAL_PROMPT_SUBMIT_HOOK
    hook.parent.mkdir(parents=True)
    hook.write_text("print('ran')\n", encoding="utf-8")
    _governed(tmp_path)
    project = tmp_path / "project"
    (project / ".git").mkdir(parents=True)
    env = {k: v for k, v in os.environ.items() if k != "PROVIDENCE_WORKSPACE_ROOT"}

    def run(cwd: Path) -> str:
        return subprocess.run(
            central_prompt_submit_command(),
            input="{}",
            cwd=cwd,
            env=env,
            shell=True,
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()

    assert run(project) == ""
    assert run(tmp_path) == "ran"


def test_prompt_submit_hook_generator_writes_copilot_adapter(tmp_path: Path) -> None:
    generator = PromptSubmitHookGenerator(tmp_path, {"copilot"})

    assert generator.generate() is True

    hook_file = tmp_path / ".github" / "hooks" / "providence-prompt-submit.json"
    settings = json.loads(hook_file.read_text(encoding="utf-8"))
    entry = settings["hooks"]["UserPromptSubmit"][0]
    # The tracked file must not depend on the OS that generated it: both
    # documented per-shell keys are always written, `command` is the POSIX one.
    assert entry["bash"].startswith("python3 -c ")
    assert entry["powershell"].startswith("python -c ")
    assert entry["command"] == entry["bash"]
    for special in ("$", "%", "`", "&", "|", "^"):
        assert special not in entry["bash"]
        assert special not in entry["powershell"]


def test_central_hook_echoes_platform_event_name_and_reads_utf8(
    tmp_path: Path,
) -> None:
    """Gemini sends BeforeAgent; the hook must echo it, and a non-ASCII prompt
    must survive stdin decoding regardless of the Windows console codepage."""
    PromptSubmitHookGenerator(tmp_path, {"gemini"}).generate()
    _governed(tmp_path)
    hook = tmp_path / CENTRAL_PROMPT_SUBMIT_HOOK

    result = subprocess.run(
        [sys.executable, str(hook)],
        input=json.dumps(
            {"prompt": "/sdd-ask avaliação", "hook_event_name": "BeforeAgent"}
        ).encode("utf-8"),
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    output = json.loads(result.stdout.decode("utf-8"))
    assert output["hookSpecificOutput"]["hookEventName"] == "BeforeAgent"


def test_prompt_submit_hook_generator_merges_gemini_settings(tmp_path: Path) -> None:
    settings_path = tmp_path / ".gemini" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text('{"contextFileName": "GEMINI.md"}', encoding="utf-8")
    generator = PromptSubmitHookGenerator(tmp_path, {"gemini"})

    assert generator.generate() is True

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert settings["contextFileName"] == "GEMINI.md"
    assert (
        settings["hooks"]["BeforeAgent"][0]["hooks"][0]["command"]
        == central_prompt_submit_command()
    )


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
    assert (
        settings["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        == central_prompt_submit_command()
    )


def test_prompt_submit_hook_generator_writes_claude_settings(tmp_path: Path) -> None:
    """Regression (SQ-001): Claude adapter generation, not previously covered here."""
    generator = PromptSubmitHookGenerator(tmp_path, {"claude"})

    assert generator.generate() is True

    claude_settings = tmp_path / ".claude" / "settings.json"
    assert claude_settings.exists()
    settings = json.loads(claude_settings.read_text(encoding="utf-8"))
    assert (
        settings["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        == central_prompt_submit_command()
    )
    assert not (tmp_path / ".codex" / "config.toml").exists()
    assert not (tmp_path / ".gemini" / "settings.json").exists()


def test_prompt_submit_hook_generator_all_agents_together(
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
    assert (
        claude_settings["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        == central_prompt_submit_command()
    )
    codex_toml = tomllib.loads(
        (tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8")
    )
    assert (
        codex_toml["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        == central_prompt_submit_command()
    )
    gemini_settings = json.loads(
        (tmp_path / ".gemini" / "settings.json").read_text(encoding="utf-8")
    )
    assert (
        gemini_settings["hooks"]["BeforeAgent"][0]["hooks"][0]["command"]
        == central_prompt_submit_command()
    )


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


def test_prompt_submit_hook_injects_governance_activation_header(
    tmp_path: Path,
) -> None:
    generator = PromptSubmitHookGenerator(tmp_path, {"codex"})
    generator.generate()
    _governed(tmp_path)

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


def test_prompt_submit_hook_resolves_workspace_when_called_from_subdir(
    tmp_path: Path,
) -> None:
    generator = PromptSubmitHookGenerator(tmp_path, {"codex"})
    generator.generate()
    _governed(tmp_path)
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
    _governed(tmp_path)

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


def test_prompt_submit_hook_runs_full_path_for_non_slash_prompt(
    tmp_path: Path,
) -> None:
    """A plain prompt (no /sdd-ask prefix) must still run the full `providence ask`
    path exactly as before, with PROVIDENCE_ASK_ENTRYPOINT=hook set so the CLI can
    report `entrypoint: hook` in its structured output."""
    generator = PromptSubmitHookGenerator(tmp_path, {"codex"})
    generator.generate()
    _governed(tmp_path)

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    env_marker_path = tmp_path / "entrypoint-env.marker"
    _write_fake_sdd(
        bin_dir,
        [
            "import os",
            f"open(r'{env_marker_path}', 'w').write(os.environ.get('PROVIDENCE_ASK_ENTRYPOINT', ''))",
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
    _governed(tmp_path)

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


def test_central_hook_does_not_fall_back_to_the_workspace_venv(
    tmp_path: Path,
) -> None:
    """One resolution rule: `providence` on PATH. A copy under the workspace's
    own `.venv` is not tried, so the executable that runs is never ambiguous;
    its absence is reported instead."""
    hook = _generate_hook(tmp_path)
    venv_bin = tmp_path / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    _write_fake_sdd(venv_bin, ["print('CTX')"])

    result = _run_hook(
        hook, json.dumps({"prompt": "implement C"}), env=_empty_path_env(tmp_path)
    )

    assert result.returncode == 0
    assert b"reason=cli_not_found" in result.stderr
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert context.startswith("PROVIDENCE GOVERNANCE DEGRADED")


def test_prompt_submit_hook_reports_degraded_when_providence_unavailable_anywhere(
    tmp_path: Path,
) -> None:
    """The hook must stay non-blocking when neither a PATH `providence` nor a
    `<workspace_root>/.venv/bin/providence` exists (e.g. a fresh clone before
    dependencies are installed), but it must say so instead of going silent."""
    generator = PromptSubmitHookGenerator(tmp_path, {"codex"})
    generator.generate()
    _governed(tmp_path)

    env = _empty_path_env(tmp_path)
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
    assert "reason=cli_not_found" in result.stderr
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert context.startswith("PROVIDENCE GOVERNANCE DEGRADED")
    assert "reason=cli_not_found" in context


def test_relocating_generated_output_keeps_hook_command_functional(
    tmp_path: Path,
) -> None:
    """The generated adapter remains valid when the template is relocated.

    This is intentionally a hermetic client simulation: it does not read or
    execute any real `.codex`, `.claude`, `.gemini`, or project runtime files.
    """
    staging = tmp_path / "staging"
    final = tmp_path / "final"
    PromptSubmitHookGenerator(staging, {"codex"}).generate()

    shutil.copytree(staging, final)
    stale_command = tomllib.loads(
        (final / ".codex" / "config.toml").read_text(encoding="utf-8")
    )["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]

    assert stale_command == central_prompt_submit_command()
    assert str(staging) not in stale_command
    assert str(final) not in stale_command

    _governed(final)
    bin_dir = final / "bin"
    bin_dir.mkdir()
    _write_fake_sdd(
        bin_dir,
        [
            "print('governance=active fingerprint=58a087b3c9fb9ce2 mandates=16')",
            "print('execution_gate=allowed')",
            "print('PROVIDENCE GOVERNANCE: drift=none | governance=ok | profile=client')",
        ],
    )
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    env["PROVIDENCE_WORKSPACE_ROOT"] = str(final)
    result = subprocess.run(
        stale_command,
        input=json.dumps({"prompt": "verify relocated hook"}),
        cwd=final,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        shell=True,
    )

    assert result.returncode == 0
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert context.startswith("PROVIDENCE GOVERNANCE ACTIVE")
    assert "PROVIDENCE GOVERNANCE: drift=none" in context


# ---------------------------------------------------------------------------
# Hermetic coverage: central hook behavior, adapter merge/idempotency, launcher
# boundaries. Every test builds its own project under tmp_path and never reads
# the real checkout's `.providence/`, `.claude/`, `.gemini/`, `.codex/`, ...
# ---------------------------------------------------------------------------

_LEGACY_SH_LAUNCHER = (
    "sh -c 'root=${PROVIDENCE_WORKSPACE_ROOT:-$PWD}; "
    'hook="$root/.providence/runtime/hooks/prompt-submit.py"; '
    'if [ -f "$hook" ]; then exec python3 "$hook"; fi; exit 0\' sh'
)


def _generate_hook(root: Path, agents: set[str] | None = None) -> Path:
    """Generate the central hook (and adapters) into a governed tmp project."""
    _governed(root)
    PromptSubmitHookGenerator(root, agents or {"codex"}).generate()
    return root / CENTRAL_PROMPT_SUBMIT_HOOK


def _run_hook(
    hook: Path,
    payload: bytes | str,
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    data = payload.encode("utf-8") if isinstance(payload, str) else payload
    return subprocess.run(
        [sys.executable, str(hook)],
        input=data,
        cwd=cwd or hook.parents[3],
        env=env if env is not None else dict(os.environ),
        capture_output=True,
        check=False,
    )


def _load_hook_module(hook: Path):  # noqa: ANN202
    import importlib.util

    spec = importlib.util.spec_from_file_location("_hook_under_test", hook)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_launcher(cwd: Path, env: dict[str, str] | None = None) -> str:
    return subprocess.run(
        central_prompt_submit_command(),
        input="{}",
        cwd=cwd,
        env=env if env is not None else dict(os.environ),
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()


@pytest.mark.parametrize(
    "payload", ["", "not json", "[]", "null", '{"prompt": ""}', "{}"]
)
def test_central_hook_is_silent_for_unusable_payloads(
    tmp_path: Path, payload: str
) -> None:
    hook = _generate_hook(tmp_path)

    result = _run_hook(hook, payload, env=_empty_path_env(tmp_path))

    assert result.returncode == 0
    assert result.stdout == b""


def test_central_hook_is_silent_when_hook_disabled_sentinel_exists(
    tmp_path: Path,
) -> None:
    hook = _generate_hook(tmp_path)
    (tmp_path / ".providence" / "runtime" / "hook-disabled").write_text(
        "", encoding="utf-8"
    )

    result = _run_hook(hook, json.dumps({"prompt": "/sdd-ask x"}))

    assert result.returncode == 0
    assert result.stdout == b""


def test_central_hook_names_missing_workspace_metadata(tmp_path: Path) -> None:
    hook = _generate_hook(tmp_path)
    (tmp_path / ".providence" / "metadata.json").unlink()

    result = _run_hook(hook, json.dumps({"prompt": "implement C"}))

    assert result.returncode == 0
    assert b"reason=metadata_missing" in result.stderr
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "reason=metadata_missing" in context


def test_central_hook_reports_when_it_is_not_inside_a_workspace(
    tmp_path: Path,
) -> None:
    """A hook copied outside `.providence/runtime/hooks/` has no workspace to
    govern; it must not guess one from the cwd."""
    misplaced = tmp_path / "loose" / "prompt-submit.py"
    misplaced.parent.mkdir()
    misplaced.write_text(PROMPT_SUBMIT_HOOK_SCRIPT, encoding="utf-8")
    _governed(tmp_path)

    result = subprocess.run(
        [sys.executable, str(misplaced)],
        input=json.dumps({"prompt": "implement C"}).encode(),
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert b"reason=hook_misplaced" in result.stderr


def test_central_hook_accepts_utf8_bom_on_stdin(tmp_path: Path) -> None:
    """Some Windows hosts (e.g. .NET process wrappers) prepend a UTF-8 BOM."""
    hook = _generate_hook(tmp_path)
    payload = "﻿" + json.dumps({"prompt": "/sdd-ask ok"})

    result = _run_hook(hook, payload.encode("utf-8"))

    assert result.returncode == 0
    assert json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"prompt": "/sdd-ask x"}, "UserPromptSubmit"),
        ({"prompt": "/sdd-ask x", "hook_event_name": "BeforeAgent"}, "BeforeAgent"),
        ({"prompt": "/sdd-ask x", "hookEventName": "PromptSubmit"}, "PromptSubmit"),
        ({"prompt": "/sdd-ask x", "hook_event_name": 7}, "UserPromptSubmit"),
    ],
)
def test_central_hook_event_name_per_platform(
    tmp_path: Path, payload: dict[str, object], expected: str
) -> None:
    hook = _generate_hook(tmp_path)

    result = _run_hook(hook, json.dumps(payload))

    assert json.loads(result.stdout)["hookSpecificOutput"]["hookEventName"] == expected


def test_central_hook_overrides_inherited_workspace_root(tmp_path: Path) -> None:
    """An inherited PROVIDENCE_WORKSPACE_ROOT may name a different project; the
    hook resolved its own root from its location and must pass that on."""
    hook = _generate_hook(tmp_path / "proj")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    marker = tmp_path / "root.marker"
    _write_fake_sdd(
        bin_dir,
        [
            "import os",
            f"open(r'{marker}', 'w').write(os.environ['PROVIDENCE_WORKSPACE_ROOT'])",
            "print('governance=active fingerprint=58a087b3c9fb9ce2')",
        ],
    )
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    env["PROVIDENCE_WORKSPACE_ROOT"] = str(tmp_path / "some-other-project")

    result = _run_hook(hook, json.dumps({"prompt": "implement C"}), env=env)

    assert result.returncode == 0
    assert marker.read_text(encoding="utf-8") == str(tmp_path / "proj")


def test_central_hook_reports_degraded_when_cli_fails(tmp_path: Path) -> None:
    hook = _generate_hook(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_sdd(bin_dir, ["import sys", "sys.exit(3)"], echo_entrypoint=False)
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"

    result = _run_hook(hook, json.dumps({"prompt": "implement C"}), env=env)

    assert result.returncode == 0
    assert b"reason=subprocess_error" in result.stderr
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert context.startswith("PROVIDENCE GOVERNANCE DEGRADED")
    assert "reason=subprocess_error" in context


def test_central_hook_names_empty_output_on_stderr_only(tmp_path: Path) -> None:
    """A CLI that succeeds but prints nothing injects no context; the reason is
    visible on stderr and the model is not told anything."""
    hook = _generate_hook(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_sdd(bin_dir, ["import sys", "sys.exit(0)"], echo_entrypoint=False)
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"

    result = _run_hook(hook, json.dumps({"prompt": "implement C"}), env=env)

    assert result.returncode == 0
    assert result.stdout == b""
    assert b"reason=empty_output" in result.stderr


def test_central_hook_reports_degraded_on_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import io

    hook = _generate_hook(tmp_path)
    module = _load_hook_module(hook)
    fake_cli = tmp_path / "fake-providence"
    fake_cli.write_text("", encoding="utf-8")
    monkeypatch.setattr(module, "_resolve_providence_cli", lambda: str(fake_cli))

    def _timeout(command: list[str], **_kwargs: object) -> object:
        raise subprocess.TimeoutExpired(cmd="providence", timeout=10)

    monkeypatch.setattr(module.subprocess, "run", _timeout)
    stdin = io.TextIOWrapper(io.BytesIO(b'{"prompt": "implement C"}'))
    monkeypatch.setattr(module.sys, "stdin", stdin)
    monkeypatch.setattr(module, "_workspace_root", lambda: tmp_path)

    assert module.main() == 0

    captured = capsys.readouterr()
    assert "reason=timeout" in captured.err
    context = json.loads(captured.out)["hookSpecificOutput"]["additionalContext"]
    assert "reason=timeout" in context


def test_central_hook_stays_silent_for_intentional_skips(tmp_path: Path) -> None:
    """Disabled hook and ungoverned workspace are decisions, not failures."""
    hook = _generate_hook(tmp_path)
    (tmp_path / ".providence" / "runtime" / "hook-disabled").write_text(
        "", encoding="utf-8"
    )

    disabled = _run_hook(hook, json.dumps({"prompt": "x"}))

    assert disabled.returncode == 0
    assert disabled.stdout == b""
    assert disabled.stderr == b""


def test_resolve_providence_cli_uses_path_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_hook_module(_generate_hook(tmp_path))
    monkeypatch.setattr(module.shutil, "which", lambda _name: None)
    for layout in (
        Path(".venv/bin/providence"),
        Path(".venv/Scripts/providence.exe"),
        Path("venv/bin/providence"),
    ):
        candidate = tmp_path / layout
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_text("", encoding="utf-8")
    assert module._resolve_providence_cli() is None

    monkeypatch.setattr(module.shutil, "which", lambda _name: "/global/providence")
    assert module._resolve_providence_cli() == "/global/providence"


def test_launcher_honors_workspace_root_env_from_another_cwd(tmp_path: Path) -> None:
    hook = _generate_hook(tmp_path / "proj")
    hook.write_text("print('ran')\n", encoding="utf-8")
    elsewhere = tmp_path / "elsewhere"
    (elsewhere / ".git").mkdir(parents=True)
    env = dict(os.environ)
    env["PROVIDENCE_WORKSPACE_ROOT"] = str(tmp_path / "proj")

    assert _run_launcher(elsewhere, env) == "ran"


def test_launcher_finds_workspace_at_the_git_root_itself(tmp_path: Path) -> None:
    """`.git` and `.providence/` in the same directory is the normal layout."""
    hook = _generate_hook(tmp_path)
    hook.write_text("print('ran')\n", encoding="utf-8")

    assert _run_launcher(tmp_path) == "ran"


def test_launcher_ignores_global_home_runtime(hermetic_env) -> None:  # noqa: ANN001
    """`~/.providence/` is the global CLI, never a workspace, even with a hook."""
    home_hook = hermetic_env.home / CENTRAL_PROMPT_SUBMIT_HOOK
    home_hook.parent.mkdir(parents=True, exist_ok=True)
    home_hook.write_text("print('WRONG: global home hook ran')\n", encoding="utf-8")
    ungoverned = hermetic_env.projects / "scratch"
    ungoverned.mkdir()

    assert _run_launcher(ungoverned) == ""


def test_generator_is_idempotent_for_every_adapter(tmp_path: Path) -> None:
    agents = resolve_prompt_submit_hook_agents(None)
    PromptSubmitHookGenerator(tmp_path, agents).generate()
    files = [
        tmp_path / ".claude" / "settings.json",
        tmp_path / ".codex" / "config.toml",
        tmp_path / ".gemini" / "settings.json",
        tmp_path / ".github" / "hooks" / "providence-prompt-submit.json",
        tmp_path / CENTRAL_PROMPT_SUBMIT_HOOK,
    ]
    first = {f: f.read_bytes() for f in files}

    PromptSubmitHookGenerator(tmp_path, agents).generate()

    assert {f: f.read_bytes() for f in files} == first


def test_claude_adapter_keeps_user_hooks_and_replaces_stale_ours(
    tmp_path: Path,
) -> None:
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    user_entry = {"hooks": [{"type": "command", "command": "my-own-hook.sh"}]}
    stale_entry = {"hooks": [{"type": "command", "command": _LEGACY_SH_LAUNCHER}]}
    settings_path.write_text(
        json.dumps(
            {
                "model": "opus",
                "hooks": {"UserPromptSubmit": [user_entry, stale_entry]},
            }
        ),
        encoding="utf-8",
    )

    PromptSubmitHookGenerator(tmp_path, {"claude"}).generate()

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    entries = settings["hooks"]["UserPromptSubmit"]
    assert settings["model"] == "opus"
    assert [e["hooks"][0]["command"] for e in entries] == [
        central_prompt_submit_command(),
        "my-own-hook.sh",
    ]


def test_gemini_adapter_keeps_other_events_and_user_before_agent_hooks(
    tmp_path: Path,
) -> None:
    settings_path = tmp_path / ".gemini" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    user_hook = {"hooks": [{"type": "command", "command": "my-before-agent.sh"}]}
    settings_path.write_text(
        json.dumps(
            {
                "contextFileName": "GEMINI.md",
                "hooks": {
                    "AfterTool": [{"hooks": [{"type": "command", "command": "x"}]}],
                    "BeforeAgent": [user_hook],
                },
            }
        ),
        encoding="utf-8",
    )

    generator = PromptSubmitHookGenerator(tmp_path, {"gemini"})
    generator.generate()
    generator.generate()

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    assert settings["contextFileName"] == "GEMINI.md"
    assert settings["hooks"]["AfterTool"][0]["hooks"][0]["command"] == "x"
    commands = [e["hooks"][0]["command"] for e in settings["hooks"]["BeforeAgent"]]
    assert commands == [central_prompt_submit_command(), "my-before-agent.sh"]


def test_codex_adapter_preserves_user_config_and_is_idempotent(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        'model = "gpt-5"\n\n[profiles.fast]\neffort = "low"\n', encoding="utf-8"
    )

    generator = PromptSubmitHookGenerator(tmp_path, {"codex"})
    generator.generate()
    generator.generate()

    text = config_path.read_text(encoding="utf-8")
    parsed = tomllib.loads(text)
    assert parsed["model"] == "gpt-5"
    assert parsed["profiles"]["fast"]["effort"] == "low"
    assert len(parsed["hooks"]["UserPromptSubmit"]) == 1
    assert text.count("providence prompt-submit hook (managed)") == 1


def test_codex_adapter_rejects_legacy_bare_hook_file(tmp_path: Path) -> None:
    """A bare hook block written by an older generator is retired input: it is
    rejected with a diagnostic and left untouched, never interpreted."""
    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir(parents=True)
    legacy = (
        "[[hooks.UserPromptSubmit]]\n\n[[hooks.UserPromptSubmit.hooks]]\n"
        'type = "command"\n'
        f"command = {json.dumps(_LEGACY_SH_LAUNCHER)}\ntimeout = 10\n"
    )
    config_path.write_text(legacy, encoding="utf-8")

    with pytest.raises(HookGenerationError) as excinfo:
        PromptSubmitHookGenerator(tmp_path, {"codex"}).generate()

    assert str(config_path) in str(excinfo.value)
    assert config_path.read_text(encoding="utf-8") == legacy
    assert not (tmp_path / CENTRAL_PROMPT_SUBMIT_HOOK).exists()


def test_codex_adapter_refreshes_managed_block_in_place() -> None:
    from providence_wizard.orchestration.prompt_submit_hooks import merge_codex_config

    old = merge_codex_config('model = "x"\n', "python -c old")
    new = merge_codex_config(old + "\n[extra]\nkey = 1\n", "python -c new")

    parsed = tomllib.loads(new)
    assert parsed["model"] == "x"
    assert parsed["extra"]["key"] == 1
    assert parsed["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"] == (
        "python -c new"
    )
    assert "python -c old" not in new


@pytest.mark.parametrize(
    ("relative", "agent", "content"),
    [
        (".claude/settings.json", "claude", "{ not json"),
        (".gemini/settings.json", "gemini", '{"hooks": '),
        (".claude/settings.json", "claude", "[]"),
        (".gemini/settings.json", "gemini", "null"),
    ],
)
def test_generator_aborts_before_writing_when_settings_are_malformed(
    tmp_path: Path, relative: str, agent: str, content: str
) -> None:
    """A settings file the generator cannot parse is the user's: it is left
    byte-identical and nothing else is written."""
    settings = tmp_path / relative
    settings.parent.mkdir(parents=True)
    settings.write_text(content, encoding="utf-8")

    with pytest.raises(HookGenerationError) as excinfo:
        PromptSubmitHookGenerator(tmp_path, {agent}).generate()

    assert str(settings) in str(excinfo.value)
    assert settings.read_text(encoding="utf-8") == content
    assert not (tmp_path / CENTRAL_PROMPT_SUBMIT_HOOK).exists()


def test_generator_malformed_settings_do_not_leave_partial_output(
    tmp_path: Path,
) -> None:
    bad = tmp_path / ".gemini" / "settings.json"
    bad.parent.mkdir(parents=True)
    bad.write_text("{", encoding="utf-8")

    with pytest.raises(HookGenerationError):
        PromptSubmitHookGenerator(tmp_path, {"claude", "codex", "gemini"}).generate()

    assert not (tmp_path / CENTRAL_PROMPT_SUBMIT_HOOK).exists()
    assert not (tmp_path / ".claude" / "settings.json").exists()
    assert not (tmp_path / ".codex" / "config.toml").exists()


def test_generator_rejects_the_pre_rebrand_central_hook_in_json_settings(
    tmp_path: Path,
) -> None:
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    original = json.dumps(
        {
            "hooks": {
                "UserPromptSubmit": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "python3 .sdd/runtime/hooks/sdd-governance-inject.py",
                            }
                        ]
                    }
                ]
            }
        }
    )
    settings.write_text(original, encoding="utf-8")

    with pytest.raises(HookGenerationError) as excinfo:
        PromptSubmitHookGenerator(tmp_path, {"claude"}).generate()

    assert "sdd-governance-inject.py" in str(excinfo.value)
    assert settings.read_text(encoding="utf-8") == original


def test_generator_rejects_the_pre_rebrand_central_hook_in_codex_config(
    tmp_path: Path,
) -> None:
    config = tmp_path / ".codex" / "config.toml"
    config.parent.mkdir(parents=True)
    original = (
        'model = "x"\n\n[[hooks.UserPromptSubmit]]\n[[hooks.UserPromptSubmit.hooks]]\n'
        'type = "command"\ncommand = "python3 sdd-governance-inject.py"\n'
    )
    config.write_text(original, encoding="utf-8")

    with pytest.raises(HookGenerationError) as excinfo:
        PromptSubmitHookGenerator(tmp_path, {"codex"}).generate()

    assert "sdd-governance-inject.py" in str(excinfo.value)
    assert config.read_text(encoding="utf-8") == original


def test_platform_timeouts_exceed_the_hook_internal_timeout(tmp_path: Path) -> None:
    """If the platform kills the hook at the same instant its own subprocess
    times out, the degraded-mode diagnostic can never be delivered."""
    assert PLATFORM_HOOK_TIMEOUT_SECONDS > HOOK_INTERNAL_TIMEOUT_SECONDS
    assert f"timeout={HOOK_INTERNAL_TIMEOUT_SECONDS}," in PROMPT_SUBMIT_HOOK_SCRIPT

    PromptSubmitHookGenerator(tmp_path, {"codex", "gemini", "copilot"}).generate()

    codex = tomllib.loads(
        (tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8")
    )
    assert codex["hooks"]["UserPromptSubmit"][0]["hooks"][0]["timeout"] == (
        PLATFORM_HOOK_TIMEOUT_SECONDS
    )
    copilot = json.loads(
        (tmp_path / ".github" / "hooks" / "providence-prompt-submit.json").read_text(
            encoding="utf-8"
        )
    )
    assert copilot["hooks"]["UserPromptSubmit"][0]["timeout"] == (
        PLATFORM_HOOK_TIMEOUT_SECONDS
    )
    gemini = json.loads(
        (tmp_path / ".gemini" / "settings.json").read_text(encoding="utf-8")
    )
    # Gemini expresses hook timeouts in milliseconds.
    assert gemini["hooks"]["BeforeAgent"][0]["hooks"][0]["timeout"] == (
        PLATFORM_HOOK_TIMEOUT_SECONDS * 1000
    )


def test_phase456_reports_unusable_settings_instead_of_crashing(tmp_path: Path) -> None:
    """The wizard phase must turn a refused hook generation into a failed result
    with the diagnostic, not an exception, and must not touch the user's file."""
    from types import SimpleNamespace

    from providence_wizard.orchestration.phase_4_5_6_generator import (
        Phase456Generator,
    )

    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text("{ not json", encoding="utf-8")
    fake = SimpleNamespace(
        config={"handshake_mode": "hook"},
        selected_seedlings={"claude"},
        output_base=tmp_path,
        _emit=lambda _message: None,
    )
    result: dict[str, list[str]] = {"errors": []}

    ok = Phase456Generator._generate_prompt_submit_hooks(fake, result)  # type: ignore[arg-type]

    assert ok is False
    assert any(str(settings) in error for error in result["errors"])
    assert settings.read_text(encoding="utf-8") == "{ not json"


# Payload shapes copied from each platform's official hook reference (fetched
# 2026-10-11). They carry the extra fields real clients send, so the hook is
# proven to ignore what it does not need and to find `prompt` in every form.
_PLATFORM_PAYLOADS = {
    "gemini_before_agent": (
        {
            "session_id": "s-1",
            "transcript_path": "/home/u/.gemini/tmp/t.json",
            "cwd": "/work/proj",
            "hook_event_name": "BeforeAgent",
            "timestamp": "2026-10-11T12:00:00Z",
            "prompt": "explique o hook",
        },
        "BeforeAgent",
    ),
    "codex_user_prompt_submit": (
        {
            "session_id": "s-2",
            "transcript_path": "/home/u/.codex/sessions/t.jsonl",
            "cwd": "/work/proj",
            "hook_event_name": "UserPromptSubmit",
            "model": "gpt-5",
            "permission_mode": "default",
            "turn_id": "turn-7",
            "prompt": "explique o hook",
        },
        "UserPromptSubmit",
    ),
    "copilot_vscode_user_prompt_submit": (
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "s-3",
            "timestamp": "2026-10-11T12:00:00Z",
            "cwd": "/work/proj",
            "prompt": "explique o hook",
        },
        "UserPromptSubmit",
    ),
    # Copilot CLI camelCase form: no `hook_event_name` at all.
    "copilot_cli_user_prompt_submitted": (
        {
            "sessionId": "s-4",
            "timestamp": 1760000000000,
            "cwd": "/work/proj",
            "prompt": "explique o hook",
        },
        "UserPromptSubmit",
    ),
}


@pytest.mark.parametrize(
    ("payload", "expected_event"),
    list(_PLATFORM_PAYLOADS.values()),
    ids=list(_PLATFORM_PAYLOADS),
)
def test_central_hook_handles_each_documented_platform_payload(
    tmp_path: Path, payload: dict[str, object], expected_event: str
) -> None:
    hook = _generate_hook(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_sdd(
        bin_dir,
        [
            "import sys",
            "print('GOVERNANCE_FOR:' + sys.argv[2])",
        ],
    )
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"

    result = _run_hook(hook, json.dumps(payload), env=env)

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)["hookSpecificOutput"]
    assert output["hookEventName"] == expected_event
    assert "GOVERNANCE_FOR:explique o hook" in output["additionalContext"]


def test_generator_reports_platform_notices_for_codex_and_copilot(
    tmp_path: Path,
) -> None:
    generator = PromptSubmitHookGenerator(tmp_path, {"claude", "codex", "copilot"})

    assert generator.generate() is True

    joined = " ".join(generator.notices)
    assert "Codex" in joined
    assert "trust" in joined
    assert "Copilot CLI" in joined
    assert "not guaranteed" in joined
    assert not any("Claude" in notice for notice in generator.notices)


def test_copilot_adapter_file_is_identical_whichever_os_generated_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The file is tracked and shared by Linux and Windows machines: generating
    it with either host launcher must produce the same bytes."""
    from providence_wizard.orchestration import prompt_submit_hooks as module

    first = tmp_path / "posix"
    second = tmp_path / "windows"
    monkeypatch.setattr(
        module, "PROMPT_SUBMIT_LAUNCHER", module.launcher_command("python3")
    )
    PromptSubmitHookGenerator(first, {"copilot"}).generate()
    monkeypatch.setattr(
        module, "PROMPT_SUBMIT_LAUNCHER", module.launcher_command("python")
    )
    PromptSubmitHookGenerator(second, {"copilot"}).generate()

    relative = Path(".github") / "hooks" / "providence-prompt-submit.json"
    assert (first / relative).read_bytes() == (second / relative).read_bytes()


def test_central_hook_surfaces_the_cli_diagnostic_on_stderr(tmp_path: Path) -> None:
    """A CLI that refuses the environment (retired variable) must say why: the
    operator sees the CLI's own last line next to the skip reason."""
    hook = _generate_hook(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_sdd(
        bin_dir,
        [
            "import sys",
            "sys.stderr.write('ERROR: SDD_WORKSPACE_ROOT was retired; "
            "set PROVIDENCE_WORKSPACE_ROOT instead\\n')",
            "sys.exit(2)",
        ],
        echo_entrypoint=False,
    )
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"

    result = _run_hook(hook, json.dumps({"prompt": "implement C"}), env=env)

    assert result.returncode == 0
    assert b"reason=subprocess_error" in result.stderr
    assert b"set PROVIDENCE_WORKSPACE_ROOT instead" in result.stderr


def test_central_hook_exports_the_canonical_entrypoint_variable(
    tmp_path: Path,
) -> None:
    hook = _generate_hook(tmp_path)
    marker = tmp_path / "entrypoint.marker"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_sdd(
        bin_dir,
        [
            "import os",
            f"open(r'{marker}', 'w').write(os.environ.get('PROVIDENCE_ASK_ENTRYPOINT', ''))",
            "print('ctx')",
        ],
    )
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    env.pop("SDD_ASK_ENTRYPOINT", None)

    _run_hook(hook, json.dumps({"prompt": "implement C"}), env=env)

    assert marker.read_text(encoding="utf-8") == "hook"


def _cli_env(tmp_path: Path) -> dict[str, str]:
    bin_dir = tmp_path / "bin"
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    return env


def _hook_with_cli(
    tmp_path: Path,
    *,
    version: str = "1.0.99",
    body: list[str] | None = None,
    version_log: Path | None = None,
    fingerprint: str | None = _FAKE_FINGERPRINT,
) -> tuple[Path, dict[str, str]]:
    hook = _generate_hook(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    _write_fake_sdd(
        bin_dir,
        body if body is not None else ["print('CTX')"],
        version=version,
        version_log=version_log,
        fingerprint=fingerprint,
    )
    return hook, _cli_env(tmp_path)


def test_central_hook_accepts_a_version_that_is_not_refused(tmp_path: Path) -> None:
    hook, env = _hook_with_cli(tmp_path, version="1.0.18")

    result = _run_hook(hook, json.dumps({"prompt": "implement C"}), env=env)

    assert result.returncode == 0
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert context.startswith("PROVIDENCE GOVERNANCE ACTIVE")


def test_central_hook_refuses_a_cli_that_ignores_the_entrypoint_marker(
    tmp_path: Path,
) -> None:
    """The version number is not the contract: a CLI that does not echo the
    marker it was given is refused whatever it calls itself."""
    hook = _generate_hook(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_sdd(
        bin_dir,
        ["print('entrypoint        : explicit_command')", "print('CTX')"],
        version="9.9.9",
        echo_entrypoint=False,
    )

    result = _run_hook(
        hook, json.dumps({"prompt": "implement C"}), env=_cli_env(tmp_path)
    )

    assert result.returncode == 0
    assert b"reason=cli_contract_mismatch" in result.stderr
    assert b"entrypoint=explicit_command" in result.stderr
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert context.startswith("PROVIDENCE GOVERNANCE DEGRADED")
    assert "CTX" not in context


def test_central_hook_refuses_a_cli_that_reports_no_entrypoint(
    tmp_path: Path,
) -> None:
    hook = _generate_hook(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_sdd(bin_dir, ["print('CTX')"], echo_entrypoint=False)

    result = _run_hook(
        hook, json.dumps({"prompt": "implement C"}), env=_cli_env(tmp_path)
    )

    assert b"reason=cli_contract_mismatch" in result.stderr
    assert b"entrypoint=absent" in result.stderr


def _set_workspace_fingerprint(root: Path, fingerprint: str) -> None:
    (root / ".providence" / "metadata.json").write_text(
        json.dumps({"fingerprints": {"combined": fingerprint}}), encoding="utf-8"
    )


def test_central_hook_rejects_context_from_a_different_governance_fingerprint(
    tmp_path: Path,
) -> None:
    hook, env = _hook_with_cli(
        tmp_path,
        body=["print('governance=ok fingerprint=bbbbbbbb mandates=16')"],
        fingerprint=None,
    )
    _set_workspace_fingerprint(tmp_path, "aaaaaaaa11112222")

    result = _run_hook(hook, json.dumps({"prompt": "implement C"}), env=env)

    assert result.returncode == 0
    assert b"reason=cli_fingerprint_mismatch" in result.stderr
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert context.startswith("PROVIDENCE GOVERNANCE DEGRADED")
    assert "fingerprint=bbbbbbbb" not in context


def test_central_hook_accepts_a_matching_fingerprint_prefix(tmp_path: Path) -> None:
    hook, env = _hook_with_cli(
        tmp_path,
        body=["print('governance=ok fingerprint=aaaaaaaa mandates=16')"],
        fingerprint=None,
    )
    _set_workspace_fingerprint(tmp_path, "aaaaaaaa11112222")

    result = _run_hook(hook, json.dumps({"prompt": "implement C"}), env=env)

    assert result.returncode == 0
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert context.startswith("PROVIDENCE GOVERNANCE ACTIVE")


def test_central_hook_does_not_probe_or_judge_the_cli_version(
    tmp_path: Path,
) -> None:
    """The contract is behavior, not a number: a CLI that echoes the marker is
    accepted whatever version it reports, and `--version` is never run."""
    probes = tmp_path / "probes.log"
    hook, env = _hook_with_cli(tmp_path, version="1.0.17", version_log=probes)

    result = _run_hook(hook, json.dumps({"prompt": "implement C"}), env=env)

    assert result.returncode == 0
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert context.startswith("PROVIDENCE GOVERNANCE ACTIVE")
    assert not probes.exists()
    assert not (tmp_path / ".providence" / "runtime" / "hook-cli-version.json").exists()


def test_central_hook_rejects_context_without_a_fingerprint(tmp_path: Path) -> None:
    hook = _generate_hook(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_sdd(
        bin_dir,
        ["print('entrypoint        : hook')", "print('governance=ok')"],
        echo_entrypoint=False,
    )

    result = _run_hook(
        hook, json.dumps({"prompt": "implement C"}), env=_cli_env(tmp_path)
    )

    assert b"reason=cli_fingerprint_mismatch" in result.stderr
    assert b"cli=absent" in result.stderr


def test_central_hook_requires_a_workspace_fingerprint(tmp_path: Path) -> None:
    hook, env = _hook_with_cli(tmp_path)
    (tmp_path / ".providence" / "metadata.json").write_text("{}", encoding="utf-8")

    result = _run_hook(hook, json.dumps({"prompt": "implement C"}), env=env)

    assert b"reason=workspace_fingerprint_missing" in result.stderr
    context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
    assert context.startswith("PROVIDENCE GOVERNANCE DEGRADED")


# --- Devin CLI -----------------------------------------------------------------


def _devin_file(root: Path) -> Path:
    return root / ".devin" / "hooks.v1.json"


def test_devin_adapter_writes_top_level_events_without_a_wrapper(
    tmp_path: Path,
) -> None:
    generator = PromptSubmitHookGenerator(tmp_path, {"devin"})

    assert generator.generate() is True

    payload = json.loads(_devin_file(tmp_path).read_text(encoding="utf-8"))
    assert list(payload) == ["UserPromptSubmit"]
    hook = payload["UserPromptSubmit"][0]["hooks"][0]
    assert hook["type"] == "command"
    assert hook["timeout"] == PLATFORM_HOOK_TIMEOUT_SECONDS
    assert "DEVIN_PROJECT_DIR" in hook["command"]
    assert ".providence/runtime/hooks/prompt-submit.py" in hook["command"]
    assert not (tmp_path / ".claude").exists()
    assert any(n.startswith("devin:") for n in generator.notices)


def test_devin_adapter_keeps_other_events_and_user_entries_and_is_idempotent(
    tmp_path: Path,
) -> None:
    user_entry = {"hooks": [{"type": "command", "command": "echo mine"}]}
    _devin_file(tmp_path).parent.mkdir()
    _devin_file(tmp_path).write_text(
        json.dumps(
            {
                "SessionStart": [
                    {"hooks": [{"type": "command", "command": "echo hi"}]}
                ],
                "UserPromptSubmit": [user_entry],
            }
        ),
        encoding="utf-8",
    )

    PromptSubmitHookGenerator(tmp_path, {"devin"}).generate()
    first = _devin_file(tmp_path).read_bytes()
    PromptSubmitHookGenerator(tmp_path, {"devin"}).generate()

    assert _devin_file(tmp_path).read_bytes() == first
    payload = json.loads(first)
    assert payload["SessionStart"][0]["hooks"][0]["command"] == "echo hi"
    prompts = payload["UserPromptSubmit"]
    assert user_entry in prompts
    assert len(prompts) == 2


def test_devin_adapter_is_not_written_when_the_claude_adapter_carries_the_hook(
    tmp_path: Path,
) -> None:
    """Devin loads .claude/settings.json by default: one registration only."""
    generator = PromptSubmitHookGenerator(tmp_path, {"claude", "devin"})

    generator.generate()

    assert not _devin_file(tmp_path).exists()
    assert (tmp_path / ".claude" / "settings.json").is_file()
    assert any("loads .claude/settings.json by default" in n for n in generator.notices)


def test_devin_adapter_removes_a_managed_entry_when_claude_takes_over(
    tmp_path: Path,
) -> None:
    PromptSubmitHookGenerator(tmp_path, {"devin"}).generate()
    payload = json.loads(_devin_file(tmp_path).read_text(encoding="utf-8"))
    payload["SessionStart"] = [{"hooks": [{"type": "command", "command": "echo hi"}]}]
    _devin_file(tmp_path).write_text(json.dumps(payload), encoding="utf-8")

    PromptSubmitHookGenerator(tmp_path, {"claude", "devin"}).generate()

    remaining = json.loads(_devin_file(tmp_path).read_text(encoding="utf-8"))
    assert remaining == {
        "SessionStart": [{"hooks": [{"type": "command", "command": "echo hi"}]}]
    }


def test_devin_adapter_file_is_removed_when_only_the_managed_entry_was_in_it(
    tmp_path: Path,
) -> None:
    PromptSubmitHookGenerator(tmp_path, {"devin"}).generate()

    PromptSubmitHookGenerator(tmp_path, {"claude", "devin"}).generate()

    assert not _devin_file(tmp_path).exists()


@pytest.mark.parametrize(
    "content",
    ['{"hooks": {"UserPromptSubmit": []}}', "{not json", "[]"],
)
def test_devin_adapter_refuses_a_file_it_cannot_trust_and_writes_nothing(
    tmp_path: Path, content: str
) -> None:
    _devin_file(tmp_path).parent.mkdir()
    _devin_file(tmp_path).write_text(content, encoding="utf-8")

    with pytest.raises(HookGenerationError):
        PromptSubmitHookGenerator(tmp_path, {"devin", "codex"}).generate()

    assert _devin_file(tmp_path).read_text(encoding="utf-8") == content
    assert not (tmp_path / CENTRAL_PROMPT_SUBMIT_HOOK).exists()
    assert not (tmp_path / ".codex").exists()


def test_devin_launcher_anchors_on_the_documented_project_dir(
    tmp_path: Path,
) -> None:
    """Devin documents DEVIN_PROJECT_DIR but not the hook's cwd, so the
    launcher must find the workspace from the variable alone."""
    workspace = tmp_path / "proj"
    _governed(workspace)
    hook = _generate_hook(workspace)
    assert hook.is_file()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / ".git").mkdir()  # an unrelated project: cwd alone finds nothing
    env = {
        key: value
        for key, value in os.environ.items()
        if key != "PROVIDENCE_WORKSPACE_ROOT"
    }
    env["DEVIN_PROJECT_DIR"] = str(workspace)
    env["PATH"] = str(tmp_path / "empty")
    command = launcher_command(f'"{sys.executable}"', "DEVIN_PROJECT_DIR")

    result = subprocess.run(
        command,
        input=json.dumps({"prompt": "implement C"}),
        cwd=elsewhere,
        env=env,
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "reason=cli_not_found" in result.stderr  # the hook ran, in `workspace`
