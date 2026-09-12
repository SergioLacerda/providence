#!/usr/bin/env python3
"""Audit capability drift across CLI, runtime registries, templates, and docs."""

from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_SLASH_BACKTICK_RE = re.compile(r"`(/sdd-[a-z0-9-]+)`")
_SLASH_BARE_RE = re.compile(r"(?<![A-Za-z0-9_-])(/sdd-[a-z0-9-]+)(?![A-Za-z0-9_/-])")


@dataclass
class AuditResult:
    ok: bool
    summary: dict[str, Any]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def _keys_from_dict_node(node: ast.Dict) -> set[str]:
    out: set[str] = set()
    for key_node in node.keys:
        if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
            out.add(key_node.value)
    return out


def _command_specs_dict_from_stmt(stmt: ast.stmt) -> ast.Dict | None:
    if isinstance(stmt, ast.Assign):
        for target in stmt.targets:
            if (
                isinstance(target, ast.Name)
                and target.id == "COMMAND_SPECS"
                and isinstance(stmt.value, ast.Dict)
            ):
                return stmt.value
        return None
    if (
        isinstance(stmt, ast.AnnAssign)
        and isinstance(stmt.target, ast.Name)
        and stmt.target.id == "COMMAND_SPECS"
        and isinstance(stmt.value, ast.Dict)
    ):
        return stmt.value
    return None


def _extract_cli_commands(repo_root: Path) -> set[str]:
    """Extract CLI command keys from COMMAND_SPECS via static AST parsing."""
    main_py = (
        repo_root / "packages/interfaces/providence_cli/src/providence_cli/main.py"
    )
    if not main_py.exists():
        return set()

    tree = ast.parse(main_py.read_text(encoding="utf-8"))
    for stmt in tree.body:
        cmd_dict = _command_specs_dict_from_stmt(stmt)
        if cmd_dict is not None:
            return _keys_from_dict_node(cmd_dict)
    return set()


def _extract_runtime_commands(
    repo_root: Path,
) -> tuple[set[str], dict[str, dict[str, Any]]]:
    reg = _load_json(repo_root / ".providence/commands/registry.json")
    entries = reg.get("commands", []) if isinstance(reg, dict) else []
    by_slash: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        slash = str(entry.get("slash", "")).strip()
        if slash:
            by_slash[slash] = entry
    return set(by_slash.keys()), by_slash


def _extract_runtime_skills(repo_root: Path) -> set[str]:
    reg = _load_json(repo_root / ".providence/skills/registry.json")
    entries = reg.get("skills", []) if isinstance(reg, dict) else []
    out: set[str] = set()
    for entry in entries:
        if isinstance(entry, dict) and entry.get("name"):
            out.add(str(entry["name"]))
    return out


def _extract_template_slashes(repo_root: Path) -> tuple[set[str], set[str]]:
    template_ai = (
        repo_root
        / "packages/interfaces/providence_wizard/src/providence_wizard/templates/governance/sovereign-factory/agent-instructions.md"
    )
    template_prompts_dir = (
        repo_root
        / "packages/interfaces/providence_wizard/src/providence_wizard/templates/governance/sovereign-factory/prompts"
    )

    ai_slashes: set[str] = set()
    if template_ai.exists():
        ai_slashes = _extract_slashes_from_text(template_ai.read_text(encoding="utf-8"))

    prompt_slashes: set[str] = set()
    if template_prompts_dir.exists():
        for p in template_prompts_dir.glob("sdd-*.prompt.md"):
            prompt_slashes.add("/" + p.name.replace(".prompt.md", ""))

    return ai_slashes, prompt_slashes


def _extract_docs_slashes(repo_root: Path) -> set[str]:
    roots = [repo_root / "README.md", repo_root / "docs"]
    out: set[str] = set()
    for root in roots:
        if root.is_file():
            out.update(
                _SLASH_BACKTICK_RE.findall(
                    root.read_text(encoding="utf-8", errors="ignore")
                )
            )
            continue
        if root.is_dir():
            for md in root.rglob("*.md"):
                out.update(
                    _SLASH_BACKTICK_RE.findall(
                        md.read_text(encoding="utf-8", errors="ignore")
                    )
                )
    return out


def _extract_slashes_from_text(text: str) -> set[str]:
    """Extract slash commands from markdown-like text with reduced false positives."""
    out = set(_SLASH_BACKTICK_RE.findall(text))
    out.update(_SLASH_BARE_RE.findall(text))
    return out


def run_audit(repo_root: Path) -> AuditResult:
    cli_commands = _extract_cli_commands(repo_root)
    runtime_slashes, runtime_by_slash = _extract_runtime_commands(repo_root)
    runtime_skills = _extract_runtime_skills(repo_root)
    template_ai_slashes, template_prompt_slashes = _extract_template_slashes(repo_root)
    docs_slashes = _extract_docs_slashes(repo_root)

    template_union = template_ai_slashes | template_prompt_slashes

    template_not_runtime = sorted(template_union - runtime_slashes)
    runtime_not_template = sorted(runtime_slashes - template_union)
    docs_not_runtime = sorted(docs_slashes - runtime_slashes)

    invalid_cli_routes: list[dict[str, str]] = []
    invalid_skill_routes: list[dict[str, str]] = []
    for slash, entry in runtime_by_slash.items():
        route = entry.get("routes_to", {}) if isinstance(entry, dict) else {}
        if not isinstance(route, dict):
            continue
        rtype = route.get("type")
        if rtype == "cli":
            command_str = str(route.get("command", "")).strip()
            # "providence ask" -> command key "ask"
            cmd_key = (
                command_str.split(" ", 1)[1]
                if command_str.startswith("sdd ")
                else command_str
            )
            if cmd_key and cmd_key not in cli_commands:
                invalid_cli_routes.append({"slash": slash, "route": command_str})
        elif rtype == "skill":
            skill_id = str(route.get("id", "")).strip()
            if skill_id and skill_id not in runtime_skills:
                invalid_skill_routes.append({"slash": slash, "skill": skill_id})

    summary = {
        "authority": {
            "cli": "packages/interfaces/providence_cli",
            "skills_runtime_registry": ".providence/skills/registry.json",
            "commands_runtime_registry": ".providence/commands/registry.json",
            "templates": "packages/interfaces/providence_wizard/.../sovereign-factory",
            "docs_scope": ["README.md", "docs/"],
        },
        "counts": {
            "cli_commands": len(cli_commands),
            "runtime_slash_commands": len(runtime_slashes),
            "runtime_skills": len(runtime_skills),
            "template_slashes": len(template_union),
            "docs_slashes": len(docs_slashes),
        },
        "drift": {
            "template_not_in_runtime": template_not_runtime,
            "runtime_not_in_template": runtime_not_template,
            "docs_not_in_runtime": docs_not_runtime,
            "invalid_cli_routes": invalid_cli_routes,
            "invalid_skill_routes": invalid_skill_routes,
        },
    }

    has_drift = any(
        [
            template_not_runtime,
            runtime_not_template,
            docs_not_runtime,
            invalid_cli_routes,
            invalid_skill_routes,
        ]
    )
    return AuditResult(ok=not has_drift, summary=summary)


def _print_human(result: AuditResult) -> None:
    s = result.summary
    counts = s["counts"]
    drift = s["drift"]

    print("Capability Sync Audit")
    print("=====================")
    print(f"CLI commands:           {counts['cli_commands']}")
    print(f"Runtime slash commands: {counts['runtime_slash_commands']}")
    print(f"Runtime skills:         {counts['runtime_skills']}")
    print(f"Template slashes:       {counts['template_slashes']}")
    print(f"Docs slashes:           {counts['docs_slashes']}")

    def section(name: str, items: list[Any]) -> None:
        print(f"\n{name}: {len(items)}")
        for item in items[:50]:
            print(f"  - {item}")

    section("template_not_in_runtime", drift["template_not_in_runtime"])
    section("runtime_not_in_template", drift["runtime_not_in_template"])
    section("docs_not_in_runtime", drift["docs_not_in_runtime"])
    section("invalid_cli_routes", drift["invalid_cli_routes"])
    section("invalid_skill_routes", drift["invalid_skill_routes"])

    print("\nSTATUS:", "OK" if result.ok else "DRIFT_DETECTED")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit capability sync drift")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    parser.add_argument(
        "--strict",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Exit non-zero when drift is detected (default: true)",
    )
    args = parser.parse_args(argv)

    repo_root = _repo_root()
    result = run_audit(repo_root)

    if args.json:
        print(json.dumps(result.summary, indent=2))
    else:
        _print_human(result)

    if args.strict and not result.ok:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
