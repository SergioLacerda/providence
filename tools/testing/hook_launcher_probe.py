#!/usr/bin/env python3
"""Run the generated prompt-submit adapter commands under the host's shells.

The adapters (`.claude/settings.json`, `.codex/config.toml`,
`.gemini/settings.json`, `.github/hooks/providence-prompt-submit.json`) carry a
one-line launcher that each agent product hands to a shell. Unit tests cannot
prove that line runs under `cmd.exe` or Windows PowerShell 5.1, so this probe
runs every command it finds the way a shell would and reports what happened.

Usage:
    python tools/testing/hook_launcher_probe.py                  # cwd workspace
    python tools/testing/hook_launcher_probe.py --workspace DIR  # another one
    python tools/testing/hook_launcher_probe.py --cwd docs       # run from a subdirectory
    python tools/testing/hook_launcher_probe.py --json           # machine output

It is a proxy for the products, not a replacement: the product's own quoting
and working directory are what the platform validation items observe.
Standard library only; exit status is 1 when any run errors or times out.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess  # nosec B404
import sys
from pathlib import Path

HOOK_MARKER = "prompt-submit.py"
COMMAND_KEYS = frozenset({"command", "bash", "powershell", "windows", "linux", "osx"})
ADAPTER_FILES = (
    Path(".claude") / "settings.json",
    Path(".gemini") / "settings.json",
    Path(".github") / "hooks" / "providence-prompt-submit.json",
    Path(".devin") / "hooks.v1.json",
    Path(".codex") / "config.toml",
)
RUN_TIMEOUT_SECONDS = 30
_TOML_COMMAND = re.compile(r'^\s*command\s*=\s*(".*")\s*$')
_SKIP = re.compile(r"providence-hook: skipped reason=(\w+)")


def _collect_json(node: object, source: str, found: list[tuple[str, str]]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, str) and key in COMMAND_KEYS and HOOK_MARKER in value:
                found.append((f"{source}:{key}", value))
            else:
                _collect_json(value, source, found)
    elif isinstance(node, list):
        for item in node:
            _collect_json(item, source, found)


def find_commands(workspace: Path) -> list[tuple[str, str]]:
    """Return (label, command) for each adapter command that names the hook."""
    found: list[tuple[str, str]] = []
    for relative in ADAPTER_FILES:
        path = workspace / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8-sig")
        if path.suffix == ".json":
            try:
                _collect_json(json.loads(text), relative.as_posix(), found)
            except ValueError:
                continue
            continue
        for line in text.splitlines():
            match = _TOML_COMMAND.match(line)
            if match and HOOK_MARKER in match.group(1):
                try:
                    found.append((relative.as_posix(), json.loads(match.group(1))))
                except ValueError:
                    continue
    return found


def available_shells() -> list[tuple[str, list[str] | None]]:
    """Shells to try; None means `subprocess` shell=True (sh or cmd.exe)."""
    shells: list[tuple[str, list[str] | None]] = [
        ("cmd" if os.name == "nt" else "sh", None)
    ]
    for name in ("powershell", "pwsh"):
        executable = shutil.which(name)
        if executable:
            shells.append(
                (name, [executable, "-NoProfile", "-NonInteractive", "-Command"])
            )
    return shells


def classify(returncode: int, stdout: str, stderr: str) -> str:
    """Name what a launcher run did: injected, degraded, skipped:*, silent, error."""
    if returncode != 0:
        return "error"
    text = stdout.strip()
    if not text:
        skipped = _SKIP.search(stderr)
        return f"skipped:{skipped.group(1)}" if skipped else "silent"
    try:
        context = json.loads(text)["hookSpecificOutput"]["additionalContext"]
    except (ValueError, KeyError, TypeError):
        return "error"
    if str(context).startswith("PROVIDENCE GOVERNANCE ACTIVE"):
        return "injected"
    if str(context).startswith("PROVIDENCE GOVERNANCE DEGRADED"):
        reason = re.search(r"reason=(\w+)", str(context))
        return f"degraded:{reason.group(1)}" if reason else "degraded"
    return "error"


def run_one(
    command: str,
    shell: list[str] | None,
    cwd: Path,
    payload: str,
    extra_env: dict[str, str] | None = None,
) -> dict[str, object]:
    env = dict(os.environ)
    env.pop("PROVIDENCE_WORKSPACE_ROOT", None)
    env.update(extra_env or {})
    try:
        if shell is None:
            # nosec B602 - the point is to run the adapter command through a shell,
            # exactly as the agent product does; it comes from the workspace's own
            # generated adapters, which the operator is validating.
            result = subprocess.run(  # nosec B602
                command,
                shell=True,
                input=payload,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=RUN_TIMEOUT_SECONDS,
                check=False,
            )
        else:
            result = subprocess.run(  # nosec B603
                [*shell, command],
                input=payload,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=RUN_TIMEOUT_SECONDS,
                check=False,
            )
    except subprocess.TimeoutExpired:
        return {"outcome": "timeout", "returncode": None, "stderr": ""}
    except OSError as exc:
        return {"outcome": "error", "returncode": None, "stderr": str(exc)}
    return {
        "outcome": classify(result.returncode, result.stdout, result.stderr),
        "returncode": result.returncode,
        "stderr": result.stderr.strip().splitlines()[-1][:200]
        if result.stderr.strip()
        else "",
    }


def probe(
    workspace: Path, prompt: str, cwd: Path | None = None
) -> list[dict[str, object]]:
    payload = json.dumps({"prompt": prompt, "hook_event_name": "UserPromptSubmit"})
    rows: list[dict[str, object]] = []
    for label, command in find_commands(workspace):
        for shell_name, shell in available_shells():
            # Devin sets DEVIN_PROJECT_DIR for its hooks; model that for its file.
            extra = (
                {"DEVIN_PROJECT_DIR": str(workspace)}
                if label.startswith(".devin/")
                else None
            )
            row = run_one(command, shell, cwd or workspace, payload, extra)
            rows.append({"source": label, "shell": shell_name, **row})
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument(
        "--cwd",
        type=Path,
        default=None,
        help="directory the commands run from (relative to --workspace); "
        "default: the workspace itself",
    )
    parser.add_argument("--prompt", default="implement C")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    workspace = args.workspace.resolve()
    cwd = None if args.cwd is None else (workspace / args.cwd).resolve()
    rows = probe(workspace, args.prompt, cwd)
    if args.as_json:
        print(
            json.dumps(
                {
                    "platform": sys.platform,
                    "python": sys.version.split()[0],
                    "workspace": str(workspace),
                    "results": rows,
                },
                indent=2,
            )
        )
    else:
        print(
            f"platform={sys.platform} python={sys.version.split()[0]} "
            f"workspace={workspace}"
        )
        if not rows:
            print("no adapter command found")
        for row in rows:
            print(
                f"{row['source']:<55} {row['shell']:<11} "
                f"{row['outcome']:<28} rc={row['returncode']} {row['stderr']}"
            )
    if not rows:
        return 1
    return 1 if any(r["outcome"] in {"error", "timeout"} for r in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
