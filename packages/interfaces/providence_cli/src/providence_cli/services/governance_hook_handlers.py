"""Handlers for `providence governance hook status|disable|enable`.

Deliberately dependency-light: only stdlib + `providence_core.utils.environment`.
This command must keep working to disable the prompt-submit governance hook
even when the rest of the `sdd` CLI (governance loading, msgpack compilation)
is what's broken  that's the exact scenario it exists to rescue.
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console

HOOK_SENTINEL_RELATIVE = Path(".providence") / "runtime" / "hook-disabled"
CENTRAL_HOOK_RELATIVE = Path(".providence") / "runtime" / "hooks" / "prompt-submit.py"

_PLATFORM_ADAPTER_FILES = {
    "claude": Path(".claude") / "settings.json",
    "codex": Path(".codex") / "config.toml",
    "gemini": Path(".gemini") / "settings.json",
}

_HOOK_REFERENCES = (
    "sdd-governance-inject.py",
    ".providence/runtime/hooks/prompt-submit.py",
)

# Behavior markers that must be present in the central hook for it to match
# the current source template (packages/interfaces/providence_wizard/.../prompt_submit_hooks.py).
# A hook missing these still passes adapter-reference checks but is stale:
# it was generated before this behavior was added to the template.
_CENTRAL_HOOK_CURRENT_MARKERS = (
    "PROVIDENCE GOVERNANCE ACTIVE",
    "_render_activation_header",
    '"hookEventName"',
)


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


def run_governance_hook_status(*, console: Console) -> None:
    """Report sentinel state and, best-effort, per-platform hook file presence."""
    root = _resolve_root()
    sentinel = root / HOOK_SENTINEL_RELATIVE
    if sentinel.exists():
        console.print("[yellow]Governance prompt-submit hook: disabled[/yellow]")
    else:
        console.print("[green]Governance prompt-submit hook: enabled[/green]")

    central_hook_present = (root / CENTRAL_HOOK_RELATIVE).exists()
    central_hook_stale = central_hook_present and _central_hook_is_stale(root)
    if central_hook_stale:
        console.print(
            "  [yellow]central hook: configured but stale "
            "(missing activation-header behavior; "
            "run 'providence governance generate' to refresh)[/yellow]"
        )
    for platform, relative_path in _PLATFORM_ADAPTER_FILES.items():
        state = _platform_hook_state(
            root, relative_path, central_hook_present, central_hook_stale
        )
        console.print(f"  {platform}: {state}")


def _central_hook_is_stale(root: Path) -> bool:
    """Return True when the central hook lacks the current template's markers.

    Adapter files only reference the central hook path, so `status` used to
    report "configured" even when the central hook itself was generated from
    an older template version (missing the activation-header instructions).
    """
    hook_path = root / CENTRAL_HOOK_RELATIVE
    try:
        content = hook_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    return not all(marker in content for marker in _CENTRAL_HOOK_CURRENT_MARKERS)


def _platform_hook_state(
    root: Path,
    relative_path: Path,
    central_hook_present: bool,
    central_hook_stale: bool,
) -> str:
    adapter_path = root / relative_path
    if not central_hook_present or not adapter_path.exists():
        return "not configured"
    try:
        content = adapter_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return "unknown"
    if any(reference in content for reference in _HOOK_REFERENCES):
        return "configured (stale)" if central_hook_stale else "configured"
    return "not configured"
