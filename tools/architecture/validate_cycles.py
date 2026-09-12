#!/usr/bin/env python3
"""
Detect import cycles between first-party Providence modules.

Usage:
    python tools/architecture/validate_cycles.py [--root <path>] [--json]
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

PROVIDENCE_PREFIXES = (
    "providence_core",
    "providence_telemetry",
    "providence_integration",
    "providence_cli",
    "providence_wizard",
    "providence_runtime",
)

SKIP_MARKERS = ("site-packages", ".venv", "__pycache__", ".egg", "tests")


def _is_repo_root(path: Path) -> bool:
    return (path / "pyproject.toml").exists() and (path / "packages").exists()


def _detect_root(explicit_root: Path | None) -> Path:
    if explicit_root is not None:
        return explicit_root.resolve()
    here = Path(__file__).resolve()
    for candidate in (here.parent, *here.parents):
        if _is_repo_root(candidate):
            return candidate
    raise RuntimeError("Could not detect repo root. Use --root.")


def _module_name(file: Path, root: Path) -> str | None:
    try:
        rel = file.relative_to(root / "packages")
    except ValueError:
        return None
    parts = rel.parts
    if len(parts) < 4 or parts[2] != "src":
        return None
    mod_parts: list[str] = list(parts[3:])
    if not mod_parts[-1].endswith(".py"):
        return None
    if mod_parts[-1] == "__init__.py":
        mod_parts = mod_parts[:-1]
    else:
        mod_parts = list(mod_parts[:-1]) + [mod_parts[-1][:-3]]
    if not mod_parts:
        return None
    return ".".join(mod_parts)


def _is_first_party(module: str) -> bool:
    return any(module == p or module.startswith(f"{p}.") for p in PROVIDENCE_PREFIXES)


def _resolve_relative(base_module: str, level: int, imported: str | None) -> str | None:
    base_parts = base_module.split(".")
    if level > len(base_parts):
        return None
    prefix = base_parts[:-level]
    if imported:
        return ".".join(prefix + imported.split("."))
    return ".".join(prefix)


def _build_parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


def _is_type_checking_guard(test: ast.AST) -> bool:
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    if isinstance(test, ast.Attribute) and isinstance(test.value, ast.Name):
        return test.value.id == "typing" and test.attr == "TYPE_CHECKING"
    return False


def _under_type_checking(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
    cur = node
    while cur in parents:
        cur = parents[cur]
        if isinstance(cur, ast.If) and _is_type_checking_guard(cur.test):
            return True
    return False


def _resolve_importfrom_targets(
    node: ast.ImportFrom, module_name: str, known_modules: set[str]
) -> set[str]:
    if node.level and node.level > 0:
        base = _resolve_relative(module_name, node.level, node.module)
    else:
        base = node.module
    if not base:
        return set()

    targets = {base}
    for alias in node.names:
        candidate = f"{base}.{alias.name}"
        if candidate in known_modules:
            targets.add(candidate)
    return targets


def _add_import_dependencies(
    deps: set[str], node: ast.Import, known_modules: set[str]
) -> None:
    for alias in node.names:
        imported = alias.name
        if _is_first_party(imported) and imported in known_modules:
            deps.add(imported)


def _add_importfrom_dependency(
    deps: set[str],
    node: ast.ImportFrom,
    module_name: str,
    known_modules: set[str],
) -> None:
    for target in _resolve_importfrom_targets(node, module_name, known_modules):
        if _is_first_party(target) and target in known_modules:
            deps.add(target)


def _extract_module_dependencies(
    *,
    tree: ast.AST,
    module_name: str,
    known_modules: set[str],
) -> set[str]:
    parents = _build_parent_map(tree)
    deps: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if _under_type_checking(node, parents):
                continue
            _add_import_dependencies(deps, node, known_modules)
        elif isinstance(node, ast.ImportFrom):
            if _under_type_checking(node, parents):
                continue
            _add_importfrom_dependency(deps, node, module_name, known_modules)
    return deps


def _collect_first_party_modules(root: Path) -> dict[str, Path]:
    module_to_file: dict[str, Path] = {}
    for file in (root / "packages").rglob("*.py"):
        if any(marker in str(file) for marker in SKIP_MARKERS):
            continue
        mod = _module_name(file, root)
        if mod and _is_first_party(mod):
            module_to_file[mod] = file
    return module_to_file


def _build_graph(root: Path) -> tuple[dict[str, set[str]], list[str]]:
    module_to_file = _collect_first_party_modules(root)
    known_modules = set(module_to_file.keys())
    graph: dict[str, set[str]] = {mod: set() for mod in known_modules}
    parse_errors: list[str] = []

    for module_name, file in module_to_file.items():
        try:
            tree = ast.parse(file.read_text(encoding="utf-8"), filename=str(file))
        except SyntaxError:
            parse_errors.append(str(file.relative_to(root)))
            continue
        graph[module_name] = _extract_module_dependencies(
            tree=tree, module_name=module_name, known_modules=known_modules
        )

    return graph, parse_errors


def _tarjan_scc(graph: dict[str, set[str]]) -> list[list[str]]:
    index = 0
    indices: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    sccs: list[list[str]] = []

    def strongconnect(v: str) -> None:
        nonlocal index
        indices[v] = index
        low[v] = index
        index += 1
        stack.append(v)
        on_stack.add(v)

        for w in graph.get(v, ()):
            if w not in indices:
                strongconnect(w)
                low[v] = min(low[v], low[w])
            elif w in on_stack:
                low[v] = min(low[v], indices[w])

        if low[v] == indices[v]:
            component: list[str] = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                component.append(w)
                if w == v:
                    break
            sccs.append(sorted(component))

    for node in sorted(graph):
        if node not in indices:
            strongconnect(node)
    return sccs


def _print_text_report(
    *, cycles: list[list[str]], parse_errors: list[str], modules_scanned: int
) -> None:
    if cycles:
        print(f"ERROR: {len(cycles)} import cycle(s) detected:\n")
        for i, cycle in enumerate(cycles, start=1):
            print(f"  {i}. {' -> '.join(cycle)}")
        if parse_errors:
            print("\nERROR: parse errors in files:")
            for err in parse_errors:
                print(f"  - {err}")
        return
    if parse_errors:
        print(f"ERROR: {len(parse_errors)} file(s) skipped due to parse errors:")
        for err in parse_errors:
            print(f"  - {err}")
        print("\nFix syntax errors before running cycle validation.")
        return
    print(f"Import graph OK: no cycles found across {modules_scanned} modules.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect import cycles in first-party modules"
    )
    parser.add_argument("--root", type=Path, default=None, help="Repo root")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    try:
        root = _detect_root(args.root)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    graph, parse_errors = _build_graph(root)
    sccs = _tarjan_scc(graph)
    cycles: list[list[str]] = []
    for comp in sccs:
        if len(comp) > 1 or len(comp) == 1 and comp[0] in graph.get(comp[0], set()):
            cycles.append(comp)

    payload = {
        "ok": len(cycles) == 0,
        "cycle_count": len(cycles),
        "cycles": cycles,
        "parse_errors": parse_errors,
        "modules_scanned": len(graph),
    }

    if parse_errors:
        payload["ok"] = False

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        _print_text_report(
            cycles=cycles, parse_errors=parse_errors, modules_scanned=len(graph)
        )

    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
