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

pytestmark = pytest.mark.usefixtures("hermetic_env")

_FAKE_CLI_BASENAME = "providence_fake_cli"


def _write_fake_sdd(bin_dir: Path, body_lines: list[str]) -> None:
    """Write a fake `providence` command a subprocess can resolve via PATH.

    On POSIX it is an executable script.  On Windows `CreateProcess` only runs
    real executables for a bare name, but `shutil.which` (used by the hook)
    resolves `providence.cmd` through PATHEXT to a full path that
    `subprocess.run` can launch, so a `.cmd` shim around a Python file works.
    """
    body = "\n".join(body_lines) + "\n"
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
    (root / ".providence" / "metadata.json").write_text("{}", encoding="utf-8")
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
    assert codex_toml["hooks"]["UserPromptSubmit"][0]["hooks"][0][
        "command"
    ] == central_prompt_submit_command(tmp_path)
    assert CENTRAL_PROMPT_SUBMIT_COMMAND not in codex_config_text
    assert not (tmp_path / ".claude" / "settings.json").exists()
    assert not (tmp_path / ".gemini" / "settings.json").exists()


def test_prompt_submit_launcher_exits_zero_when_central_hook_is_missing(
    tmp_path: Path,
) -> None:
    (tmp_path / ".git").mkdir()
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


def test_prompt_submit_launcher_is_shell_agnostic() -> None:
    """The launcher must not depend on `sh` (absent from cmd.exe / PowerShell)
    nor use characters special to cmd.exe or PowerShell."""
    command = central_prompt_submit_command(Path("."))

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
        central_prompt_submit_command(tmp_path),
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
            central_prompt_submit_command(tmp_path),
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
    assert settings["hooks"]["UserPromptSubmit"][0][
        "command"
    ] == central_prompt_submit_command(tmp_path)


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
    path exactly as before, with SDD_ASK_ENTRYPOINT=hook set so the CLI can
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


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="the Windows fallback is `providence.exe`, which cannot be faked; "
    "covered by test_resolve_providence_cli_finds_windows_venv_scripts",
)
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
    _governed(tmp_path)

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
    assert result.stdout == ""


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

    assert stale_command == central_prompt_submit_command(staging)
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
        central_prompt_submit_command(cwd),
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


def test_central_hook_is_silent_without_workspace_metadata(tmp_path: Path) -> None:
    hook = _generate_hook(tmp_path)
    (tmp_path / ".providence" / "metadata.json").unlink()

    result = _run_hook(hook, json.dumps({"prompt": "/sdd-ask x"}))

    assert result.returncode == 0
    assert result.stdout == b""


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


def test_central_hook_is_silent_when_cli_prints_nothing(tmp_path: Path) -> None:
    hook = _generate_hook(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_sdd(bin_dir, ["import sys", "sys.exit(3)"])
    env = dict(os.environ)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"

    result = _run_hook(hook, json.dumps({"prompt": "implement C"}), env=env)

    assert result.returncode == 0
    assert result.stdout == b""


def test_resolve_providence_cli_prefers_path_then_venv_layouts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_hook_module(_generate_hook(tmp_path))
    monkeypatch.setattr(module.shutil, "which", lambda _name: None)
    assert module._resolve_providence_cli(tmp_path) is None

    posix = tmp_path / ".venv" / "bin" / "providence"
    windows = tmp_path / ".venv" / "Scripts" / "providence.exe"
    windows.parent.mkdir(parents=True)
    windows.write_text("", encoding="utf-8")
    assert module._resolve_providence_cli(tmp_path) == str(windows)

    posix.parent.mkdir(parents=True)
    posix.write_text("", encoding="utf-8")
    assert module._resolve_providence_cli(tmp_path) == str(posix)

    monkeypatch.setattr(module.shutil, "which", lambda _name: "/global/providence")
    assert module._resolve_providence_cli(tmp_path) == "/global/providence"


def test_resolve_providence_cli_finds_windows_venv_scripts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = _load_hook_module(_generate_hook(tmp_path))
    monkeypatch.setattr(module.shutil, "which", lambda _name: None)
    alt = tmp_path / "venv" / "Scripts" / "providence.exe"
    alt.parent.mkdir(parents=True)
    alt.write_text("", encoding="utf-8")

    assert module._resolve_providence_cli(tmp_path) == str(alt)


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
        central_prompt_submit_command(tmp_path),
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
    assert commands == [central_prompt_submit_command(tmp_path), "my-before-agent.sh"]


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


def test_codex_adapter_replaces_legacy_bare_hook_file(tmp_path: Path) -> None:
    """Files written by older generators held only the hook block."""
    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        "[[hooks.UserPromptSubmit]]\n\n[[hooks.UserPromptSubmit.hooks]]\n"
        'type = "command"\n'
        f"command = {json.dumps(_LEGACY_SH_LAUNCHER)}\ntimeout = 10\n",
        encoding="utf-8",
    )

    PromptSubmitHookGenerator(tmp_path, {"codex"}).generate()

    parsed = tomllib.loads(config_path.read_text(encoding="utf-8"))
    hooks = parsed["hooks"]["UserPromptSubmit"]
    assert len(hooks) == 1
    assert hooks[0]["hooks"][0]["command"] == central_prompt_submit_command(tmp_path)


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
