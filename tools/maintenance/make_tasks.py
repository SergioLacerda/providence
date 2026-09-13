#!/usr/bin/env python3
"""Makefile task wrappers with governed process execution."""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import re
import shlex
import shutil
import sys
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    # Windows consoles default to the legacy codepage (e.g. cp1252), which
    # can't encode the emoji/symbols used in status output below.
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    if isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[2]
PROVIDENCE_CORE_SRC = REPO_ROOT / "packages" / "core" / "providence_core" / "src"
if str(PROVIDENCE_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(PROVIDENCE_CORE_SRC))

# Fallback used only if pyproject.toml is missing or has no parseable typer pin.
_FALLBACK_MIN_TYPER_VERSION = (0, 26, 8)
_MAKE_HELP_RE = re.compile(r"^([A-Za-z0-9_.-]+):.*##(.*)$")


def _version_tuple(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for piece in version.split("."):
        num = ""
        for ch in piece:
            if ch.isdigit():
                num += ch
            else:
                break
        parts.append(int(num) if num else 0)
    return tuple(parts)


def _load_pyproject() -> dict[str, Any] | None:
    pyproject = REPO_ROOT / "pyproject.toml"
    if not pyproject.exists():
        return None
    try:
        import tomllib  # py311+
    except ImportError:  # pragma: no cover
        import tomli as tomllib

    data: dict[str, Any] = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return data


def _min_typer_version() -> tuple[int, ...]:
    """Read the minimum typer version from the `typer>=X.Y.Z` pin in pyproject.toml.

    pyproject.toml is the single source of truth for this constraint; keeping a
    second hardcoded copy here risks silently drifting from the real dependency pin.
    """
    data = _load_pyproject()
    if data is None:
        return _FALLBACK_MIN_TYPER_VERSION
    deps = data.get("project", {}).get("dependencies", [])
    for dep in deps:
        if dep.startswith("typer>="):
            return _version_tuple(dep.split(">=", 1)[1])
    return _FALLBACK_MIN_TYPER_VERSION


def _venv_python_path() -> Path:
    candidates = [
        REPO_ROOT / ".venv" / "bin" / "python",
        REPO_ROOT / ".venv" / "Scripts" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _fail_venv(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    print("Run `make install` to (re)create the project virtualenv.", file=sys.stderr)
    raise SystemExit(1)


def _check_venv() -> Path:
    from providence_core.utils.process import SafeProcessRunner

    venv_python = _venv_python_path()
    if not venv_python.exists():
        _fail_venv(f".venv not found (expected {venv_python}).")

    probe = Path(__file__).resolve().parent / "_typer_version_probe.py"
    result = SafeProcessRunner().run(
        [str(venv_python), str(probe)], capture_output=True
    )
    if result.returncode != 0:
        _fail_venv("typer is not importable in .venv.")

    installed = result.stdout.strip()
    min_version = _min_typer_version()
    if _version_tuple(installed) < min_version:
        min_str = ".".join(str(p) for p in min_version)
        _fail_venv(f"typer {installed} in .venv is older than required {min_str}.")

    return venv_python


def _python_cmd() -> list[str]:
    return [str(_check_venv())]


def _run(
    cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None
) -> int:
    from providence_core.utils.process import SafeProcessRunner

    result = SafeProcessRunner().run(
        cmd, cwd=cwd or REPO_ROOT, env=env, capture_output=False
    )
    return result.returncode


def _run_optional_tool(
    cmd: list[str], *, missing_message: str, cwd: Path | None = None
) -> int:
    if shutil.which(cmd[0]) is None:
        print(missing_message)
        return 0
    return _run(cmd, cwd=cwd)


def _read_project_version() -> str:
    data = _load_pyproject()
    if data is None:
        return "(missing pyproject.toml)"
    return str(data.get("project", {}).get("version", "(dynamic via VCS)"))


def _semver_key(tag: str) -> tuple[int, ...]:
    if tag.startswith("v"):
        tag = tag[1:]
    parts: list[int] = []
    for piece in tag.split("."):
        num = ""
        for ch in piece:
            if ch.isdigit():
                num += ch
            else:
                break
        parts.append(int(num) if num else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def run_check_venv() -> int:
    """Validate .venv/typer and print the resolved interpreter path.

    Used by git hooks (pre-push, post-merge) so they share the exact same
    guard as the Makefile instead of maintaining their own fallback logic.
    """
    print(str(_check_venv()))
    return 0


def run_help() -> int:
    """Print Make target help without awk/shell dependencies."""
    print("Providence Architecture Development")
    print("====================================")
    for path in [REPO_ROOT / "Makefile", *sorted((REPO_ROOT / "mk").glob("*.mk"))]:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if line.startswith("##@"):
                print(f"\n{line[3:].strip()}")
                continue
            if line.startswith("#"):
                continue
            match = _MAKE_HELP_RE.match(line)
            if match is None:
                continue
            target, description = match.groups()
            print(f"  {target:<28} {description.strip()}")
    print()
    print("Most targets above also have a namespaced alias in their group,")
    print(
        "e.g. 'make test.fast' == 'make test-fast', "
        "'make docker.build' == 'make docker-build'."
    )
    return 0


def run_check() -> int:
    """Python portion of the `check` target (golden-status stays a Make prerequisite).

    Golden-policy runs in `--mode warn` here intentionally: drift is already
    enforced as blocking elsewhere in CI (reusable-test.yml's `--mode block`,
    release.yml/release-dry-run.yml's `--mode strict`). `check` stays a fast local
    signal rather than a second blocking gate for the same policy.
    """
    rc = _run(_python_cmd() + ["tools/ci/check_golden_policy.py", "--mode", "warn"])
    if rc != 0:
        return rc
    return _run(
        _python_cmd()
        + [
            "-m",
            "pytest",
            "tests",
            "packages",
            "-m",
            "not perf",
            "--cov=packages",
            "--cov-report=term-missing:skip-covered",
        ]
    )


def run_golden_status() -> int:
    """Print golden fixture git status without relying on shell syntax."""
    from providence_core.utils.process import SafeProcessRunner

    print("Checking golden file status...")
    result = SafeProcessRunner().run(
        ["git", "status", "--porcelain", "--", "tests/contract/fixtures/*.golden.json"],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    if result.returncode != 0:
        # Informational only (see module docstring above `golden-status` in
        # mk/python.mk): drift is enforced elsewhere in CI, so an environment
        # where `git status` itself fails (e.g. a non-git checkout) must not
        # fail this target and abort the pipeline.
        print("WARN: could not check golden file status.", file=sys.stderr)
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
        return 0

    status = result.stdout.strip()
    if status:
        print("Golden files have uncommitted changes:")
        print(status)
        print()
        print("If intentional, commit them with: git add tests/contract/fixtures/")
        print("If accidental, restore them before running check.")
    else:
        print("Golden files are in sync with git")
    return 0


def run_test_unit() -> int:
    """`unit` is an exclusion, not a required marker on every file.

    Most of the suite (packages/*/tests/) is unmarked but genuinely
    unit-level — retagging thousands of files was not needed to isolate this
    family cheaply. `integration`/`contract`/`golden` are the three families
    with their own marker (see pyproject.toml `markers`); anything not tagged
    with one of those, and not `perf`, is unit by elimination.
    """
    return _run(
        _python_cmd()
        + [
            "-m",
            "pytest",
            "tests",
            "packages",
            "-m",
            "not integration and not contract and not golden and not perf",
        ]
    )


def run_test_integration() -> int:
    return _run(
        _python_cmd()
        + ["-m", "pytest", "tests", "packages", "-m", "integration and not perf"]
    )


def run_test_contract() -> int:
    return _run(
        _python_cmd()
        + ["-m", "pytest", "tests", "packages", "-m", "contract and not perf"]
    )


def run_test_golden() -> int:
    return _run(
        _python_cmd()
        + ["-m", "pytest", "tests", "packages", "-m", "golden and not perf"]
    )


def run_lint(*, fix: bool) -> int:
    cmd = _python_cmd() + ["tools/maintenance/lint_all.py"]
    if fix:
        cmd.append("--fix")
    return _run(cmd)


def run_lint_go(*, fix: bool) -> int:
    cmd = ["golangci-lint", "run"]
    if fix:
        cmd.append("--fix")
    cmd.append("./tools/sdd-compile/...")
    action = "Go lint-fix" if fix else "Go lint"
    return _run_optional_tool(
        cmd,
        missing_message=f"golangci-lint not installed; skipping {action}",
    )


def run_lint_fix_web() -> int:
    print("lint-fix-web: apps/landing's 'lint' script is 'astro check', a")
    print("type/diagnostics checker with no autofix mode — run 'make lint-web'")
    print(
        "to see astro diagnostics. Auto-fixing markdown style now (markdownlint-cli2)."
    )
    return run_npm_script("lint-fix")


def _npm_cmd() -> str:
    return "npm.cmd" if sys.platform == "win32" else "npm"


def run_npm_script(script: str) -> int:
    return _run([_npm_cmd(), "--prefix", "apps/landing", "run", script])


def run_npm_script_advisory(script: str, *, label: str) -> None:
    """Run an npm script whose findings are advisory-only.

    Mirrors docs.yml's `continue-on-error: true` markdownlint-cli2 step:
    output is printed, but a non-zero exit never propagates to the caller's
    own return code — this must never turn `make lint-web` red on its own.
    A missing `npm` binary is the same "not blocking" case, not a harder
    failure — skip with a message instead of letting the spawn error escape,
    matching `_run_optional_tool`'s pattern for other optional CLI tools.
    """
    if shutil.which(_npm_cmd()) is None:
        print(f"{label}: npm not found on PATH; skipping (advisory only).")
        return
    if _run([_npm_cmd(), "--prefix", "apps/landing", "run", script]) != 0:
        print(f"{label}: advisory findings reported above; not blocking.")


def run_npm_audit_fix() -> int:
    """Best-effort dependency vulnerability fix; never blocks lint-web.

    `npm audit fix` exits non-zero when vulnerabilities remain that need
    `--force` (a breaking major bump) to resolve. Those need a deliberate,
    manual call rather than an automatic lint-time upgrade, so a non-zero
    exit here is logged and swallowed instead of failing lint-web.
    """
    returncode = _run([_npm_cmd(), "--prefix", "apps/landing", "audit", "fix"])
    if returncode != 0:
        print(
            "lint-web: npm audit fix left unresolved vulnerabilities "
            "(likely requiring --force / a breaking upgrade); continuing."
        )
    return 0


def run_lint_web() -> int:
    run_npm_audit_fix()
    result = run_npm_script("lint")
    run_npm_script_advisory("lint:md", label="lint-web (markdown style)")
    return result


def run_install_web() -> int:
    return _run([_npm_cmd(), "--prefix", "apps/landing", "ci"])


def run_build_compiler() -> int:
    goexe = ""
    from providence_core.utils.process import SafeProcessRunner

    result = SafeProcessRunner().run(["go", "env", "GOEXE"], capture_output=True)
    if result.returncode != 0:
        if result.stderr.strip():
            print(result.stderr.strip(), file=sys.stderr)
        return result.returncode
    goexe = result.stdout.strip()
    return _run(
        [
            "go",
            "build",
            "-C",
            "tools/sdd-compile",
            "-o",
            f"bin/sdd-compile{goexe}",
            ".",
        ]
    )


def run_test_compiler_go() -> int:
    return _run(["go", "test", "-C", "tools/sdd-compile", "./tests/", "-count=1"])


def run_mutation_go() -> int:
    for package in ("./internal/signing", "./internal/parser"):
        rc = _run(
            [
                "go",
                "run",
                "github.com/go-gremlins/gremlins/cmd/gremlins@v0.6.0",
                "unleash",
                package,
            ],
            cwd=REPO_ROOT / "tools" / "sdd-compile",
        )
        if rc != 0:
            return rc
    return 0


def run_test(extra_args: list[str]) -> int:
    return _run(_python_cmd() + ["tools/testing/run-all-tests.py", *extra_args])


def run_test_fast() -> int:
    return _run(_python_cmd() + ["-m", "pytest", "-x", "--ff", "packages/", "tests/"])


def run_test_perf() -> int:
    rc = _run(_python_cmd() + ["-m", "pytest", "-m", "perf", "-q", "packages", "tests"])
    if rc != 0:
        return rc
    return _run(_python_cmd() + ["tests/perf/benchmark_wizard_pipeline.py"])


def run_coverage() -> int:
    rc = _run(
        _python_cmd()
        + [
            "-m",
            "pytest",
            "tests",
            "packages",
            "--cov=packages",
            "--cov-report=html",
            "--cov-report=term-missing:skip-covered",
        ]
    )
    print("HTML report: build/coverage/html/index.html")
    return rc


def run_coverage_strict() -> int:
    layers = [
        ("core packages", "packages/core", 90),
        ("feature packages", "packages/features", 70),
        ("interface packages", "packages/interfaces", 70),
    ]
    for label, path, threshold in layers:
        print(f"=== {label} (threshold: {threshold}%) ===")
        rc = _run(
            _python_cmd()
            + [
                "-m",
                "pytest",
                path,
                f"--cov={path}",
                f"--cov-fail-under={threshold}",
                "-q",
                "--tb=short",
            ]
        )
        if rc != 0:
            return rc
    return 0


def run_ci_pr() -> int:
    rc = _run(
        _python_cmd()
        + [
            "-m",
            "pytest",
            "-q",
            "tests/contract/test_governance_schema.py::TestGovernanceCoreGoldenFile::test_structure_matches_golden",
        ]
    )
    if rc != 0:
        return rc
    rc = _run(_python_cmd() + ["tools/ci/check_golden_policy.py", "--mode", "block"])
    if rc != 0:
        return rc
    return _run(
        _python_cmd()
        + ["tools/ci/check_core_compiler_runtime_contract.py", "--mode", "enforce"]
    )


def run_golden_policy_check(*, strict: bool) -> int:
    mode = "strict" if strict else "block"
    return _run(_python_cmd() + ["tools/ci/check_golden_policy.py", "--mode", mode])


def run_enforcement_ladder_consistency() -> int:
    return _run(_python_cmd() + ["tools/ci/check_enforcement_ladder_consistency.py"])


def run_enforcement_ladder_digest() -> int:
    return _run(
        _python_cmd()
        + [
            "tools/ci/enforcement_ladder_digest.py",
            "--json-out",
            ".artifacts/enforcement_ladder_digest.json",
            "--md-out",
            ".artifacts/enforcement_ladder_digest.md",
        ]
    )


def run_enforcement_threshold_signoff() -> int:
    return _run(_python_cmd() + ["tools/ci/check_enforcement_threshold_signoff.py"])


def run_signoff_draft() -> int:
    return _run(_python_cmd() + ["tools/ci/generate_signoff_draft.py"])


def run_core_compiler_runtime_contract() -> int:
    return _run(
        _python_cmd()
        + ["tools/ci/check_core_compiler_runtime_contract.py", "--mode", "enforce"]
    )


def run_observability_contract_check() -> int:
    return _run(_python_cmd() + ["tools/ci/check_observability_contract.py"])


def run_release_readiness_v1_check() -> int:
    return _run(_python_cmd() + ["tools/ci/check_release_readiness_v1.py"])


def run_runbook_hardening_check() -> int:
    return _run(_python_cmd() + ["tools/ci/check_runbook_hardening_protocol.py"])


def run_update_golden_snapshots() -> int:
    return _run(_python_cmd() + ["tools/testing/update-golden-snapshots.py"])


def run_generate_schemas() -> int:
    return _run(_python_cmd() + ["tools/testing/generate-schemas.py"])


def _workspace_pythonpath_env() -> dict[str, str]:
    paths = [
        "packages/core/providence_core/src",
        "packages/core/providence_runtime/src",
        "packages/core/providence_telemetry/src",
        "packages/features/providence_integration/src",
        "packages/features/providence_adapters/src",
        "packages/features/providence_skills/src",
        "packages/features/providence_pages/src",
        "packages/interfaces/providence_wizard/src",
        "packages/interfaces/providence_cli/src",
    ]
    env = os.environ.copy()
    existing = env.get("PYTHONPATH")
    joined = os.pathsep.join(paths)
    env["PYTHONPATH"] = f"{joined}{os.pathsep}{existing}" if existing else joined
    return env


def run_docs_build() -> int:
    rc = _run(_python_cmd() + ["-m", "mkdocs", "build", "--strict"])
    if rc != 0:
        return rc
    return _run(
        _python_cmd()
        + [
            "-m",
            "providence_wizard.orchestration.wizard.selector_compiler_cli",
            "--output-dir",
            "build/site/selector",
        ],
        env=_workspace_pythonpath_env(),
    )


def _replace_dir_link(link: Path, target: Path) -> None:
    if link.is_symlink():
        link.unlink()
    elif link.exists():
        if link.is_dir():
            shutil.rmtree(link)
        else:
            link.unlink()
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        link.symlink_to(target, target_is_directory=True)
        return
    except OSError as exc:
        if sys.platform != "win32" or getattr(exc, "winerror", None) != 1314:
            raise

    from providence_core.utils.process import SafeProcessRunner

    result = SafeProcessRunner().run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        cwd=link.parent,
        capture_output=True,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise OSError(f"failed to create Windows junction {link}: {details}")


def run_docs_serve() -> int:
    selector = REPO_ROOT / "build" / "site" / "selector" / "index.html"
    if not selector.is_file():
        print(
            "ERROR: build/site/selector/index.html missing; "
            "selector compiler did not run. Run 'make docs-build' first.",
            file=sys.stderr,
        )
        return 1
    _replace_dir_link(
        REPO_ROOT / "build" / "serve-root" / "providence",
        REPO_ROOT / "build" / "site",
    )
    print("Serving at http://localhost:8000/providence/")
    return _run(
        _python_cmd() + ["-m", "http.server", "8000", "--directory", "build/serve-root"]
    )


def run_docker_build(flags_text: str = "") -> int:
    dockerignore = REPO_ROOT / ".dockerignore"
    shutil.copyfile(
        REPO_ROOT / "infrastructure" / "docker" / ".dockerignore", dockerignore
    )
    env = os.environ.copy()
    env["DOCKER_BUILDKIT"] = "1"
    flags = shlex.split(flags_text)
    try:
        return _run(
            [
                "docker",
                "buildx",
                "build",
                "--load",
                *flags,
                "-t",
                "providence",
                "-f",
                "infrastructure/docker/Dockerfile",
                ".",
            ],
            env=env,
        )
    finally:
        with contextlib.suppress(FileNotFoundError):
            dockerignore.unlink()


def run_governance_bootstrap() -> int:
    # Session lane: --full-bootstrap issues a fresh M015 challenge and
    # completes it against the resolved workspace root, invalidating any
    # handshake response from a prior agent session in this workspace. That
    # is intentional bootstrap behavior, not a validation-only command.
    return _run(
        _python_cmd()
        + ["-m", "providence_cli", "governance", "generate", "--full-bootstrap"]
    )


def run_docs_link_check() -> int:
    return _run(_python_cmd() + ["tools/docs/check_links.py", "--mode", "ci"])


def run_docs_link_fix() -> int:
    return _run(_python_cmd() + ["tools/docs/check_links.py", "--mode", "fix"])


def run_hooks_install() -> int:
    if shutil.which("bash") is None:
        print("ERROR: bash is required to install local git hooks.", file=sys.stderr)
        return 1
    return _run(["bash", ".github/setup-precommit-hook.sh"])


def run_release_prepare(version: str) -> int:
    return _run(
        _python_cmd() + ["-m", "tools.release.prepare_release", "--version", version]
    )


def run_release_dry_run() -> int:
    print("=== Version check ===")
    print(f"root: {_read_project_version()}")

    print("=== Git tags (semver) ===")
    from providence_core.utils.process import SafeProcessRunner

    tags_rc = SafeProcessRunner().run(
        ["git", "tag", "--list", "v[0-9]*"], cwd=REPO_ROOT, capture_output=True
    )
    if tags_rc.returncode == 0:
        tags = [t.strip() for t in tags_rc.stdout.splitlines() if t.strip()]
        for tag in sorted(tags, key=_semver_key)[-5:]:
            print(tag)
    else:
        print("(unable to list tags)")

    print("=== CHANGELOG.md present ===")
    if (REPO_ROOT / "CHANGELOG.md").exists():
        print("✓ CHANGELOG.md found")
    else:
        print("✗ CHANGELOG.md missing")

    print("=== README sync check ===")
    for rel in ["README.md"]:
        if (REPO_ROOT / rel).exists():
            print(f"✓ {rel} present")
        else:
            print(f"✗ {rel} missing")

    print("=== Tests pass (no coverage gate) ===")
    return run_test(["--no-coverage"])


def run_clean() -> int:
    for p in REPO_ROOT.rglob("__pycache__"):
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
    for p in REPO_ROOT.rglob("*.pyc"):
        with contextlib.suppress(FileNotFoundError):
            p.unlink()
    shutil.rmtree(REPO_ROOT / "build", ignore_errors=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Governed wrappers for Makefile tasks")
    sub = parser.add_subparsers(dest="task", required=True)

    sub.add_parser("check-venv")
    sub.add_parser("help")
    sub.add_parser("check")
    sub.add_parser("lint")
    sub.add_parser("lint-fix")
    sub.add_parser("lint-go")
    sub.add_parser("lint-fix-go")
    sub.add_parser("lint-web")
    sub.add_parser("lint-fix-web")
    sub.add_parser("install-web")
    sub.add_parser("build-web")
    sub.add_parser("test-web")
    sub.add_parser("cover-web")
    sub.add_parser("build-compiler")
    sub.add_parser("test-compiler-go")
    sub.add_parser("mutation-go")
    test_p = sub.add_parser("test")
    test_p.add_argument("args", nargs="*")
    sub.add_parser("test-fast")
    sub.add_parser("test-perf")
    sub.add_parser("test-unit")
    sub.add_parser("test-integration")
    sub.add_parser("test-contract")
    sub.add_parser("test-golden")
    sub.add_parser("coverage")
    sub.add_parser("coverage-strict")
    sub.add_parser("release-dry-run")
    release_prepare_p = sub.add_parser("release-prepare")
    release_prepare_p.add_argument("--version", required=True)
    sub.add_parser("clean")
    sub.add_parser("ci-pr")
    sub.add_parser("golden-status")
    sub.add_parser("golden-policy-check")
    sub.add_parser("golden-policy-check-strict")
    sub.add_parser("enforcement-ladder-consistency")
    sub.add_parser("enforcement-ladder-digest")
    sub.add_parser("enforcement-threshold-signoff")
    sub.add_parser("signoff-draft")
    sub.add_parser("core-compiler-runtime-contract")
    sub.add_parser("observability-contract-check")
    sub.add_parser("release-readiness-v1-check")
    sub.add_parser("runbook-hardening-check")
    sub.add_parser("update-golden-snapshots")
    sub.add_parser("generate-schemas")
    sub.add_parser("governance-bootstrap")
    sub.add_parser("docs-build")
    sub.add_parser("docs-serve")
    sub.add_parser("docs-link-check")
    sub.add_parser("docs-link-fix")
    docker_build_p = sub.add_parser("docker-build")
    docker_build_p.add_argument("--flags", default="")
    sub.add_parser("hooks-install")

    args = parser.parse_args(argv)
    if args.task == "test":
        return run_test(args.args)
    if args.task == "release-prepare":
        return run_release_prepare(args.version)
    if args.task == "docker-build":
        return run_docker_build(args.flags)

    dispatch: dict[str, Any] = {
        "check-venv": run_check_venv,
        "help": run_help,
        "check": run_check,
        "lint": lambda: run_lint(fix=False),
        "lint-fix": lambda: run_lint(fix=True),
        "lint-go": lambda: run_lint_go(fix=False),
        "lint-fix-go": lambda: run_lint_go(fix=True),
        "lint-web": run_lint_web,
        "lint-fix-web": run_lint_fix_web,
        "install-web": run_install_web,
        "build-web": lambda: run_npm_script("build"),
        "test-web": lambda: run_npm_script("test"),
        "cover-web": lambda: run_npm_script("cover"),
        "build-compiler": run_build_compiler,
        "test-compiler-go": run_test_compiler_go,
        "mutation-go": run_mutation_go,
        "test-fast": run_test_fast,
        "test-perf": run_test_perf,
        "test-unit": run_test_unit,
        "test-integration": run_test_integration,
        "test-contract": run_test_contract,
        "test-golden": run_test_golden,
        "coverage": run_coverage,
        "coverage-strict": run_coverage_strict,
        "release-dry-run": run_release_dry_run,
        "clean": run_clean,
        "ci-pr": run_ci_pr,
        "golden-status": run_golden_status,
        "golden-policy-check": lambda: run_golden_policy_check(strict=False),
        "golden-policy-check-strict": lambda: run_golden_policy_check(strict=True),
        "enforcement-ladder-consistency": run_enforcement_ladder_consistency,
        "enforcement-ladder-digest": run_enforcement_ladder_digest,
        "enforcement-threshold-signoff": run_enforcement_threshold_signoff,
        "signoff-draft": run_signoff_draft,
        "core-compiler-runtime-contract": run_core_compiler_runtime_contract,
        "observability-contract-check": run_observability_contract_check,
        "release-readiness-v1-check": run_release_readiness_v1_check,
        "runbook-hardening-check": run_runbook_hardening_check,
        "update-golden-snapshots": run_update_golden_snapshots,
        "generate-schemas": run_generate_schemas,
        "governance-bootstrap": run_governance_bootstrap,
        "docs-build": run_docs_build,
        "docs-serve": run_docs_serve,
        "docs-link-check": run_docs_link_check,
        "docs-link-fix": run_docs_link_fix,
        "hooks-install": run_hooks_install,
    }
    handler = dispatch.get(args.task)
    return handler() if handler is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
