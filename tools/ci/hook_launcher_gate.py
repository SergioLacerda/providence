#!/usr/bin/env python3
"""CI gate: the generated hook adapters run under this runner's real shells.

Unit tests run the launcher through `sh` only. This gate generates the adapters
with the source-tree generator into scratch workspaces and runs every command
through each shell the runner has (`sh` or `cmd.exe`, Windows PowerShell 5.1,
PowerShell 7) using `tools/testing/hook_launcher_probe.py`.

What is judged
--------------
* Inside a governed workspace (and from one of its subdirectories) a command
  must reach the central hook: the outcome is `injected`, `degraded:*` or
  `skipped:*`. `silent`, `error` and `timeout` fail: they are the dead-adapter
  symptom this work exists to prevent.
* From a project that is not governed, the launcher must stay `silent`.
* Devin's file is the exception to the last rule: Devin tells the launcher the
  project through `DEVIN_PROJECT_DIR`, so it reaches the hook from anywhere.
* Copilot's file carries one command per shell family. Only the native pairing is
  enforced (`bash` under `sh`, `powershell` under PowerShell, `command` under
  `sh`); the other pairings are reported, not judged, because the file is
  shared by both operating systems.

The runner's own `providence` may be on `PATH`; a degraded or injected outcome
proves the chain either way, so the result does not depend on it.

Usage:
    python tools/ci/hook_launcher_gate.py --json-out out.json --md-out out.md
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
for _entry in (
    REPO_ROOT,
    REPO_ROOT / "packages" / "core" / "providence_core" / "src",
    REPO_ROOT / "packages" / "interfaces" / "providence_wizard" / "src",
):
    if str(_entry) not in sys.path:
        sys.path.insert(0, str(_entry))

from providence_core.utils.text_io import write_text_utf8  # noqa: E402
from providence_wizard.orchestration.prompt_submit_hooks import (  # noqa: E402
    PromptSubmitHookGenerator,
)
from tools.testing import hook_launcher_probe as probe  # noqa: E402

CHAIN_PROVEN = ("injected", "degraded", "skipped")
_COPILOT_FILE = ".github/hooks/providence-prompt-submit.json"
_COPILOT_NATIVE_SHELLS = {
    "bash": {"sh"},
    "powershell": {"powershell", "pwsh"},
    "command": {"sh"},
}
_FINGERPRINT = "0123456789abcdef"


def build_workspace(root: Path, agents: set[str]) -> Path:
    """Create a governed scratch project and generate `agents` into it."""
    (root / ".git").mkdir(parents=True)
    (root / ".providence").mkdir()
    write_text_utf8(
        root / ".providence" / "metadata.json",
        json.dumps({"fingerprints": {"combined": _FINGERPRINT}}),
    )
    PromptSubmitHookGenerator(root, agents).generate()
    return root


def is_enforced(row: dict[str, object]) -> bool:
    """Whether a (command, shell) pairing is one a product really uses."""
    source = str(row["source"])
    if not source.startswith(_COPILOT_FILE):
        return True
    key = source.rsplit(":", 1)[-1]
    return str(row["shell"]) in _COPILOT_NATIVE_SHELLS.get(key, set())


def expected(row: dict[str, object], *, governed: bool) -> str:
    """Describe the outcome a row must have."""
    devin = str(row["source"]).startswith(".devin/")
    return "chain" if governed or devin else "silent"


def judge(row: dict[str, object], *, governed: bool) -> bool:
    """Return whether `row` satisfies its expectation."""
    outcome = str(row["outcome"])
    if expected(row, governed=governed) == "silent":
        return outcome == "silent"
    return outcome.split(":", 1)[0] in CHAIN_PROVEN


def run_gate(scratch: Path) -> list[dict[str, object]]:
    """Run the three scenarios and return every row with its verdict."""
    adapters = build_workspace(
        scratch / "adapters", {"claude", "codex", "gemini", "copilot"}
    )
    devin = build_workspace(scratch / "devin", {"devin"})
    (adapters / "sub").mkdir()
    outside = scratch / "outside"
    (outside / ".git").mkdir(parents=True)

    scenarios = (
        ("governed", adapters, None, True),
        ("subdirectory", adapters, adapters / "sub", True),
        ("ungoverned", adapters, outside, False),
        ("devin governed", devin, None, True),
        ("devin ungoverned", devin, outside, False),
    )
    rows: list[dict[str, object]] = []
    for name, workspace, cwd, governed in scenarios:
        for row in probe.probe(workspace, "implement C", cwd):
            enforced = is_enforced(row)
            rows.append(
                {
                    **row,
                    "scenario": name,
                    "enforced": enforced,
                    "ok": (not enforced) or judge(row, governed=governed),
                }
            )
    return rows


def render_markdown(rows: list[dict[str, object]], platform: str) -> str:
    failed = [row for row in rows if not row["ok"]]
    lines = [
        f"### Hook launcher gate ({platform})",
        "",
        f"{len(rows)} runs, {len(failed)} failed "
        f"({sum(1 for r in rows if not r['enforced'])} reported only).",
        "",
        "| Scenario | Source | Shell | Outcome | Judged | Result |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        verdict = "ok" if row["ok"] else "**FAIL**"
        judged = "yes" if row["enforced"] else "no"
        lines.append(
            f"| {row['scenario']} | `{row['source']}` | {row['shell']} "
            f"| {row['outcome']} | {judged} | {verdict} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--md-out", type=Path, default=None)
    args = parser.parse_args(argv)

    with tempfile.TemporaryDirectory() as tmp:
        rows = run_gate(Path(tmp).resolve())

    report = {"platform": sys.platform, "python": sys.version.split()[0], "rows": rows}
    markdown = render_markdown(rows, sys.platform)
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        write_text_utf8(args.json_out, json.dumps(report, indent=2) + "\n")
    if args.md_out is not None:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        write_text_utf8(args.md_out, markdown)
    sys.stdout.write(markdown)

    failed = [row for row in rows if not row["ok"]]
    if not rows:
        sys.stderr.write("hook launcher gate: no adapter command was found\n")
        return 1
    if failed:
        sys.stderr.write(f"hook launcher gate: {len(failed)} run(s) failed\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
