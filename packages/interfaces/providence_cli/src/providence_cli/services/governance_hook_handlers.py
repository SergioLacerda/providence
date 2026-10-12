"""Handlers for `providence governance hook status|disable|enable`.

Deliberately dependency-light: only stdlib + `providence_core.utils.environment`
(the generator template is imported lazily and its absence is reported, not
hidden). This command must keep working to disable the prompt-submit governance
hook even when the rest of the CLI (governance loading, msgpack compilation) is
what's broken — that's the exact scenario it exists to rescue.

`hook status` judges every adapter by the path it really runs and by the
content digest of the deployed hook, and reports an unhealthy state through its
return value so the command can exit non-zero.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from rich.console import Console

HOOK_SENTINEL_RELATIVE = Path(".providence") / "runtime" / "hook-disabled"
CENTRAL_HOOK_RELATIVE = Path(".providence") / "runtime" / "hooks" / "prompt-submit.py"

_PLATFORM_ADAPTER_FILES = {
    "claude": Path(".claude") / "settings.json",
    "codex": Path(".codex") / "config.toml",
    "gemini": Path(".gemini") / "settings.json",
    "copilot": Path(".github") / "hooks" / "providence-prompt-submit.json",
    "devin": Path(".devin") / "hooks.v1.json",
}

_CENTRAL_HOOK_REFERENCE = ".providence/runtime/hooks/prompt-submit.py"

# Retired inputs are recognised only to be rejected with a diagnostic; they are
# never accepted as a configured adapter.
_RETIRED_HOOK_REFERENCES = ("sdd-governance-inject.py",)
# `sh -c 'hook=$1; ...' sh <absolute path>`: emitted by providence-cli 1.0.14
# to 1.0.16, whose target path is baked in at generation time.
_RETIRED_SHAPE = re.compile(r"hook=\$1")

_ABSOLUTE_TARGET = re.compile(
    r"""(?:(?<![\w.~-])/|\b[A-Za-z]:[\\/])[^\s'"`;|&<>]*prompt-submit\.py"""
)

_REGENERATE_HINT = "run 'providence governance generate'"


def _resolve_root() -> Path:
    from providence_core.utils.environment import find_workspace_root

    return find_workspace_root() or Path.cwd()


def run_governance_hook_disable(*, console: Console) -> None:
    """Create the hook-disabled sentinel, stopping the prompt-submit hook."""
    sentinel = _resolve_root() / HOOK_SENTINEL_RELATIVE
    sentinel.parent.mkdir(parents=True, exist_ok=True)
    sentinel.write_text("", encoding="utf-8")
    console.print("[yellow]Governance prompt-submit hook disabled.[/yellow]")
    console.print(f"  sentinel: {sentinel}")
    console.print("  run 'providence governance hook enable' to restore it")


def run_governance_hook_enable(*, console: Console) -> None:
    """Remove the hook-disabled sentinel, restoring the prompt-submit hook."""
    sentinel = _resolve_root() / HOOK_SENTINEL_RELATIVE
    sentinel.unlink(missing_ok=True)
    console.print("[green]Governance prompt-submit hook enabled.[/green]")


def run_governance_hook_status(*, console: Console) -> bool:
    """Report hook state per platform; return False when any adapter is unhealthy.

    A broken, stale or legacy adapter is unhealthy. "disabled" and
    "not configured" are intentional states and stay healthy.
    """
    root = _resolve_root()
    sentinel = root / HOOK_SENTINEL_RELATIVE
    if sentinel.exists():
        console.print("[yellow]Governance prompt-submit hook: disabled[/yellow]")
    else:
        console.print("[green]Governance prompt-submit hook: enabled[/green]")

    template = _current_template()
    notices = _platform_notices()
    central_hook = root / CENTRAL_HOOK_RELATIVE
    central_present = central_hook.is_file()
    central_stale = central_present and _hook_is_stale(central_hook, template)
    healthy = True

    if central_present and template is None:
        console.print(
            "  [yellow]central hook: staleness not verified "
            "(generator template unavailable)[/yellow]"
        )
    if central_stale:
        console.print(
            "  [yellow]central hook: configured but stale "
            "(differs from the current template; "
            f"{_REGENERATE_HINT} to refresh)[/yellow]"
        )
    states = {
        platform: _platform_hook_state(
            root, relative_path, central_present, central_stale, template
        )
        for platform, relative_path in _PLATFORM_ADAPTER_FILES.items()
    }
    states["devin"] = _devin_state(root, states["devin"], states["claude"])
    for platform, state in states.items():
        console.print(f"  {platform}: {state}")
        if state.startswith("configured") and platform in notices:
            console.print(f"  [dim]{platform} note: {notices[platform]}[/dim]")
        if state.startswith(("legacy", "broken")) or state in {
            "configured (stale)",
            "configured (broken: missing central hook)",
        }:
            healthy = False
    return healthy


def _devin_state(root: Path, own: str, claude: str) -> str:
    """Judge Devin's registration, which may arrive through Claude's file.

    Devin loads `.claude/settings.json` by default, so a configured Claude
    adapter already reaches it. The generator writes exactly one registration;
    two are reported because how Devin merges them is undocumented.
    """
    claude_configured = claude.startswith("configured")
    own_configured = own.startswith("configured")
    if own_configured and claude_configured:
        return (
            "broken (registered twice: .claude/settings.json and "
            f".devin/hooks.v1.json; {_REGENERATE_HINT})"
        )
    if own_configured or own.startswith(("legacy", "broken")):
        try:
            payload = json.loads(
                (root / _PLATFORM_ADAPTER_FILES["devin"]).read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            payload = None
        if isinstance(payload, dict) and "hooks" in payload:
            return (
                "broken (a 'hooks' wrapper key is not valid in "
                f".devin/hooks.v1.json; {_REGENERATE_HINT})"
            )
        return own
    if own == "not configured" and claude_configured:
        return f"{claude}, via .claude/settings.json (Devin loads it by default)"
    return own


def _current_template() -> str | None:
    """Return the generator's hook template, or None when it cannot be imported."""
    try:
        from providence_wizard.orchestration.prompt_submit_hook_script import (
            PROMPT_SUBMIT_HOOK_SCRIPT,
        )
    except Exception:  # noqa: BLE001  # rescue command must survive a broken wizard
        return None
    return PROMPT_SUBMIT_HOOK_SCRIPT


def _platform_notices() -> dict[str, str]:
    """Return the verified per-platform limits, or none when the wizard is absent."""
    try:
        from providence_wizard.orchestration.prompt_submit_hooks import (
            PLATFORM_NOTICES,
        )
    except Exception:  # noqa: BLE001  # rescue command must survive a broken wizard
        return {}
    return dict(PLATFORM_NOTICES)


def _digest(text: str) -> str:
    normalized = text.replace("\r\n", "\n").encode("utf-8")
    return hashlib.sha256(normalized).hexdigest()


def _hook_is_stale(hook_path: Path, template: str | None) -> bool:
    """Return True when the deployed hook's digest differs from the template.

    Substring markers cannot prove currency: a hook may keep every marker and
    still diverge. When the template is unavailable the hook is not claimed
    stale; the caller reports that staleness was not verified.
    """
    if template is None:
        return False
    try:
        content = hook_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    return _digest(content) != _digest(template)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except (OSError, ValueError):
        return False
    return True


def _platform_hook_state(
    root: Path,
    relative_path: Path,
    central_present: bool,
    central_stale: bool,
    template: str | None = None,
) -> str:
    adapter_path = root / relative_path
    if not adapter_path.exists():
        return "not configured"
    try:
        content = adapter_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return "unknown"

    absolute = _ABSOLUTE_TARGET.search(content)
    references_hook = _CENTRAL_HOOK_REFERENCE in content or absolute is not None
    retired = any(marker in content for marker in _RETIRED_HOOK_REFERENCES)
    if not references_hook and not retired:
        return "not configured"
    if retired or _RETIRED_SHAPE.search(content):
        return f"legacy (rejected: retired command shape; {_REGENERATE_HINT})"

    if absolute is not None:
        target = Path(absolute.group(0))
        if not target.is_file():
            return f"broken (target missing: {target.as_posix()})"
        if not _is_within(target, root):
            return f"broken (target outside workspace: {target.as_posix()})"
        stale = _hook_is_stale(target, template)
        return "configured (stale)" if stale else "configured"

    if not central_present:
        return "configured (broken: missing central hook)"
    return "configured (stale)" if central_stale else "configured"
