#!/usr/bin/env python3
"""Run Python mutation testing (mutmut) against a critical module.

`mutmut` (3.7.0) only recognizes `.`/`src`/`source` as the source-root
convention for both its `sys.path` injection and its mutant-identity key
computation (`path.relative_to(Path(".").absolute())` — relative to the real
CWD at run time, not to its own `source_paths` config). This repo's
`packages/<name>/src/<name>` layout only works if `mutmut` is invoked with
CWD set to the target package's own `src/` directory.

That, in turn, needs the package's `src/` to reach the repo-root `tests/` and
`docs/` directories (for shared test helpers and the governance-compile
bootstrap other tests need) — `mutmut`'s `also_copy` mechanism only copies
paths that are forward-relative to CWD, so this script creates temporary
workspace links for the duration of the run and always removes them afterward
(this repo bans tracked git symlinks — see
`tests/unit/ci/test_repo_portability.py` — so these must never be committed).

Usage:
    make mutation-python                                  # run all registered targets
    uv run python tools/testing/run_mutation_python.py     # same, direct invocation
    uv run python tools/testing/run_mutation_python.py --target providence_runtime_gate_evaluation
"""

from __future__ import annotations

import argparse
import shutil
import subprocess  # nosec B404
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

REPO_ROOT = Path(__file__).resolve().parents[2]

# The mutmut version this script's setup was validated against is pinned in
# pyproject.toml's `mutation` dependency group (`mutmut>=3.7.0`), not
# duplicated here — that's the single enforcement point (no @latest, same
# policy already applied to govulncheck).


@dataclass(frozen=True)
class MutationTarget:
    """One package + file scoped for mutation testing.

    `package_dir` is repo-root-relative (e.g. "packages/core/providence_runtime").
    `only_mutate` entries are relative to that package's own `src/`.
    `ignore_test_files` lists test files, relative to the package's own
    `tests/` dir, to exclude from this run — reserve this for files that
    genuinely misbehave under
    mutmut's multi-phase re-invocation (e.g. real `@given`/Hypothesis
    property tests), not as a blanket exclusion. Excluding a file that
    happens to be the *only* coverage for the mutated code silently produces
    a false "no test covers this mutant" result — verify with
    `grep -n "@given\\|^from hypothesis"` before adding an entry here.
    """

    name: str
    package_dir: str
    only_mutate: list[str]
    ignore_test_files: list[str] = field(default_factory=list)
    extra_deselect: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WorkspaceLink:
    path: Path
    kind: Literal["symlink", "junction"]

    def remove(self) -> None:
        if self.kind == "symlink":
            if self.path.is_symlink():
                self.path.unlink()
            return
        if self.path.exists():
            self.path.rmdir()


TARGETS: dict[str, MutationTarget] = {
    "providence_runtime_gate_evaluation": MutationTarget(
        name="providence_runtime_gate_evaluation",
        package_dir="packages/core/providence_runtime",
        only_mutate=["providence_runtime/_skill_executor/_gate_rules/_evaluation.py"],
        ignore_test_files=["test_properties.py"],
        extra_deselect=[
            "test_skills_runtime_does_not_fallback_to_subprocess_run",
        ],
    ),
    "providence_core_process_authorization": MutationTarget(
        name="providence_core_process_authorization",
        package_dir="packages/core/providence_core",
        only_mutate=["providence_core/utils/_process_auth.py"],
        # Both genuinely misbehave under mutmut's mutants/ cwd, unrelated to
        # _process_auth.py — not a blanket exclusion, see each reason below.
        ignore_test_files=[
            # Hardcodes a repo-root-relative GENERATOR_PATH that resolves to
            # a nonexistent nested path under mutmut's mutants/ cwd.
            "test_generate_specializations.py",
            # Asserts a built wheel exposes a native asset (the compiled Go
            # binary) — never present in mutmut's Python-only mutants/ copy.
            "test_package_data.py",
        ],
    ),
    "providence_wizard_selector_dsl_parsing": MutationTarget(
        name="providence_wizard_selector_dsl_parsing",
        package_dir="packages/interfaces/providence_wizard",
        # NOTE: selector_compiler.py itself (the original candidate for this
        # target) is a @dataclass-decorated class — confirmed by direct
        # inspection that mutmut 3.7.0 does not inject trampolines into any
        # of its methods (0 `_mutmut_N` markers in the generated mutants
        # copy, vs. a non-dataclass class in the same run that mutated
        # normally). This is a tool limitation, not a config/test gap;
        # targeting the plain-function parsing module it delegates to
        # instead, which covers the same "source selection" doc-04 category
        # without hitting the dataclass limitation.
        only_mutate=["providence_wizard/orchestration/wizard/_selector_dsl_parsing.py"],
        # Both unrelated to this target, deselected by name rather than by
        # file (each file has dozens of other, unaffected tests):
        extra_deselect=[
            # Reads repo-root-relative Path("README.md"), absent under
            # mutmut's src/ cwd.
            "test_readme_contains_agent_onboarding_commands",
            # isinstance() checks against a class constructed *indirectly*
            # (via make_prompter()/_wrap_prompter(), inside prompter.py
            # itself) fail under mutmut's dual sys.path setup — the
            # function's own module-level class reference and the test's
            # direct import resolve to two distinct class objects with the
            # same name. Tests that instantiate the class directly (e.g.
            # test_plain_prompter_is_prompter) don't hit this and are left
            # active.
            "test_make_prompter_non_tty_returns_plain",
            "test_make_prompter_tty_returns_rich_when_questionary_available",
            "test_non_callable_non_prompter_returns_make_prompter",
        ],
    ),
    "providence_runtime_signatures_validate": MutationTarget(
        name="providence_runtime_signatures_validate",
        package_dir="packages/core/providence_runtime",
        only_mutate=["providence_runtime/signatures/_validate.py"],
        # Same package as providence_runtime_gate_evaluation above, so the same two
        # package-wide (not module-specific) pitfalls apply here too:
        ignore_test_files=["test_properties.py"],
        extra_deselect=[
            "test_skills_runtime_does_not_fallback_to_subprocess_run",
        ],
    ),
}


def _run(cmd: list[str], *, cwd: Path) -> int:
    print(f"$ {' '.join(cmd)}  (cwd={cwd})")
    result = subprocess.run(cmd, cwd=cwd)  # nosec B603 — fixed argv, no shell
    return result.returncode


def _is_windows_symlink_privilege_error(exc: OSError) -> bool:
    return sys.platform == "win32" and getattr(exc, "winerror", None) == 1314


def _create_workspace_link(link: Path, target: Path) -> WorkspaceLink:
    try:
        link.symlink_to(target, target_is_directory=True)
        return WorkspaceLink(path=link, kind="symlink")
    except OSError as exc:
        if not _is_windows_symlink_privilege_error(exc):
            raise

    result = subprocess.run(  # nosec B603 - fixed argv, cmd built-in, no shell
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        cwd=link.parent,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise OSError(
            f"failed to create Windows junction {link} -> {target}: {details}"
        )
    return WorkspaceLink(path=link, kind="junction")


def _write_mutmut_config(src_dir: Path, target: MutationTarget) -> Path:
    config_path = src_dir / "pyproject.toml"
    if config_path.exists():
        raise FileExistsError(
            f"{config_path} already exists — refusing to overwrite. "
            "Remove it manually if a previous run left it behind."
        )
    # Absolute, not relative: mutmut's own working directory differs between
    # its "collect stats" phase (runs from src_dir) and its per-mutant test
    # phase (runs from src_dir/mutants, one level deeper) — a relative path
    # here would need to mean two different things depending on which phase
    # is active. package_dir/tests is the package's own test suite, e.g.
    # packages/core/providence_runtime/tests/, not the repo-root tests/ directory
    # (which the src/tests and src/docs symlinks below exist to make
    # importable, not collectible).
    test_selection = str(src_dir.parent / "tests")
    deselect_expr = " and ".join(f"not {name}" for name in target.extra_deselect)
    lines = [
        "[tool.mutmut]",
        'source_paths = ["."]',
        f"only_mutate = {target.only_mutate!r}",
        f'pytest_add_cli_args_test_selection = ["{test_selection}"]',
    ]
    args_list = []
    if deselect_expr:
        args_list += ["-k", deselect_expr]
    for ignored in target.ignore_test_files:
        args_list.append(f"--ignore={src_dir.parent / 'tests' / ignored}")
    if args_list:
        lines.append(f"pytest_add_cli_args = {args_list!r}")
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return config_path


def run_target(target: MutationTarget) -> int:
    package_dir = REPO_ROOT / target.package_dir
    src_dir = package_dir / "src"
    if not src_dir.is_dir():
        print(f"ERROR: {src_dir} is not a directory", file=sys.stderr)
        return 1

    tests_link = src_dir / "tests"
    docs_link = src_dir / "docs"
    workspace_links: list[WorkspaceLink] = []
    config_path: Path | None = None
    mutants_dir = src_dir / "mutants"

    try:
        if tests_link.exists() or tests_link.is_symlink():
            raise FileExistsError(f"{tests_link} already exists — aborting")
        if docs_link.exists() or docs_link.is_symlink():
            raise FileExistsError(f"{docs_link} already exists — aborting")

        workspace_links.append(_create_workspace_link(tests_link, REPO_ROOT / "tests"))
        workspace_links.append(_create_workspace_link(docs_link, REPO_ROOT / "docs"))
        config_path = _write_mutmut_config(src_dir, target)

        return _run(
            [
                "uv",
                "run",
                "--project",
                str(REPO_ROOT),
                "mutmut",
                "run",
            ],
            cwd=src_dir,
        )
    finally:
        for link in reversed(workspace_links):
            link.remove()
        if config_path is not None and config_path.exists():
            config_path.unlink()
        if mutants_dir.exists():
            shutil.rmtree(mutants_dir, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        choices=sorted(TARGETS),
        help="Run only this target (default: run all registered targets).",
    )
    args = parser.parse_args(argv)

    selected = [TARGETS[args.target]] if args.target else list(TARGETS.values())
    worst_rc = 0
    for target in selected:
        print(f"=== mutation-python: {target.name} ===")
        rc = run_target(target)
        worst_rc = max(worst_rc, rc)
    return worst_rc


if __name__ == "__main__":
    raise SystemExit(main())
