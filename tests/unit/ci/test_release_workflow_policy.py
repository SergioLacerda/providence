from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
RELEASE_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release.yml"
RELEASE_DRY_RUN_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release-dry-run.yml"
# release.yml's `build` job no longer inlines its steps — it delegates to this
# reusable workflow (shared with release-dry-run.yml's build job), so any
# assertion about the actual build-step content must load this file instead.
REUSABLE_BUILD_WORKFLOW = (
    REPO_ROOT / ".github" / "workflows" / "reusable-release-build.yml"
)
REUSABLE_SECURITY_WORKFLOW = (
    REPO_ROOT / ".github" / "workflows" / "reusable-security.yml"
)
REUSABLE_TEST_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "reusable-test.yml"
DOCKERFILE = REPO_ROOT / "infrastructure" / "docker" / "Dockerfile"
DOCKERIGNORE = REPO_ROOT / "infrastructure" / "docker" / ".dockerignore"
MAKEFILE = REPO_ROOT / "Makefile"
MK_INCLUDES_DIR = REPO_ROOT / "mk"


def _makefile_content() -> str:
    # The root Makefile is a thin orchestrator that `include`s mk/*.mk, grouped
    # by affinity (see .analysis/refined/20260809-makefile-worldclass-refactor/
    # design.md) — policy assertions must cover the full effective Makefile,
    # not just the root file, or a recipe moved into mk/*.mk silently escapes them.
    parts = [MAKEFILE.read_text(encoding="utf-8")]
    parts.extend(
        path.read_text(encoding="utf-8")
        for path in sorted(MK_INCLUDES_DIR.glob("*.mk"))
    )
    return "\n".join(parts)


def _load_workflow(path: Path) -> dict:
    # YAML parses the bare `on:` workflow key as boolean True; force text keys.
    class _Loader(yaml.SafeLoader):
        pass

    _Loader.add_constructor(
        "tag:yaml.org,2002:bool",
        lambda loader, node: loader.construct_scalar(node),
    )
    return yaml.load(path.read_text(encoding="utf-8"), Loader=_Loader)


def _jobs(workflow: dict) -> dict:
    return workflow["jobs"]


def _step_run_block(steps: list[dict], name: str) -> str:
    step = next(step for step in steps if step.get("name") == name)
    return step.get("run", "")


def test_release_workflow_has_windows_install_smoke_lane() -> None:
    workflow = _load_workflow(RELEASE_WORKFLOW)
    jobs = _jobs(workflow)
    assert "release-install-smoke" in jobs

    smoke = jobs["release-install-smoke"]
    matrix_os = smoke["strategy"]["matrix"]["os"]
    assert "windows-latest" in matrix_os
    assert "ubuntu-latest" in matrix_os


def test_release_workflow_is_tag_driven_and_accepts_uppercase_v() -> None:
    workflow = _load_workflow(RELEASE_WORKFLOW)
    tags = workflow["on"]["push"]["tags"]
    assert "v*.*.*" in tags
    assert "V*.*.*" in tags

    validate_steps = "\n".join(
        step.get("run", "") for step in _jobs(workflow)["validate"]["steps"]
    )
    assert "^[vV][0-9]+" in validate_steps
    assert "setuptools_scm" not in validate_steps
    assert "tools.release.resolve_vcs_version" in validate_steps


def test_release_build_uses_dynamic_versioning_for_all_packages() -> None:
    """No package has a static `version = "..."` line to sync anymore — every
    workspace package resolves its version directly from the tag via
    hatch-vcs. The build workflow verifies this (fails fast if a package
    regresses to static versioning) instead of rewriting pyproject.toml
    files in place."""
    workflow = _load_workflow(REUSABLE_BUILD_WORKFLOW)
    build_steps = "\n".join(
        step.get("run", "") for step in _jobs(workflow)["build"]["steps"]
    )
    assert "sync_versions" not in build_steps
    assert "dynamic (VCS) versioning" in build_steps


def test_release_verify_step_checks_every_package_via_built_wheel() -> None:
    """Every package is dynamically versioned (hatch-vcs) and has no static
    `version = "..."` line to grep. The actual version of every built package
    is confirmed after the build, via its wheel filename — not just
    providence_cli's."""
    workflow = _load_workflow(REUSABLE_BUILD_WORKFLOW)
    build_steps = _jobs(workflow)["build"]["steps"]
    verify_step = _step_run_block(
        build_steps, "Verify built wheels match the tag version"
    )

    assert "does not match tag version" in verify_step
    assert "packages/core/*" in verify_step
    assert "packages/features/*" in verify_step
    assert "packages/interfaces/*" in verify_step


def test_release_build_verifies_wheel_bundles_native_binaries() -> None:
    """Staging assets happens before the wheel build, so only a post-build
    inspection of the wheel itself proves standalone clients get the bundled
    compiler binaries (the wheel is what they install)."""
    workflow = _load_workflow(REUSABLE_BUILD_WORKFLOW)
    build_steps = _jobs(workflow)["build"]["steps"]
    verify_step = _step_run_block(
        build_steps, "Verify providence-core wheel bundles native compiler binaries"
    )

    assert "tools.release.verify_wheel_native_assets" in verify_step


def test_release_build_injects_release_version_into_compiler_binaries() -> None:
    """The CLI<->binary version handshake needs the release version compiled
    into the Go binary; without the ldflags injection every release binary
    reports "dev" and the skew check never fires."""
    workflow = _load_workflow(REUSABLE_BUILD_WORKFLOW)
    build_steps = _jobs(workflow)["build"]["steps"]
    compile_step = _step_run_block(
        build_steps, "Cross-compile sdd-compile release binaries"
    )

    assert "-X sdd-compile/cmd.version=" in compile_step
    assert "-ldflags" in compile_step


def test_release_build_verifies_wheel_dependency_coupling() -> None:
    """Internal deps are bare `sdd-*` names; only a post-build METADATA check
    proves every released wheel's internal dependencies resolve to wheels of
    the same version in the same dist/ set."""
    workflow = _load_workflow(REUSABLE_BUILD_WORKFLOW)
    build_steps = _jobs(workflow)["build"]["steps"]
    verify_step = _step_run_block(
        build_steps, "Verify internal wheel dependencies are version-coupled"
    )

    assert "tools.release.verify_wheel_dependency_coupling" in verify_step


def _git_install_smoke_job(workflow_path: Path) -> dict:
    jobs = _jobs(_load_workflow(workflow_path))
    assert "release-git-install-smoke" in jobs, (
        f"{workflow_path.name} must smoke the documented git install channel"
    )
    return jobs["release-git-install-smoke"]


def test_release_workflows_smoke_the_git_install_channel_on_both_oses() -> None:
    """The documented client channel (source checkout install) must be
    CI-smoked on Windows and Linux — the symlink-stub incident lived exactly
    in this blind spot (wheelhouse-only smoke)."""
    for workflow_path in (RELEASE_WORKFLOW, RELEASE_DRY_RUN_WORKFLOW):
        job = _git_install_smoke_job(workflow_path)
        matrix_os = job["strategy"]["matrix"]["os"]
        assert "windows-latest" in matrix_os
        assert "ubuntu-latest" in matrix_os

        steps_text = "\n".join(step.get("run", "") for step in job["steps"])
        assert "uv tool install" in steps_text
        assert "./packages/interfaces/providence_cli" in steps_text
        assert "--with-editable" not in steps_text
        assert "providence install --wizard --non-interactive" in steps_text
        assert "providence init --default" in steps_text
        assert "providence governance validate" in steps_text
        # The checkout is itself an SDD workspace (.providence/ is committed): running
        # the client bootstrap inside it trips the nested-workspace guard in
        # `providence init`, so the smoke project must live outside the checkout.
        assert 'SMOKE_DIR="$RUNNER_TEMP/git-smoke-project"' in steps_text


def test_release_source_install_smoke_avoids_windows_git_file_urls() -> None:
    """Windows git+file URLs can be re-parsed by uv with the resolved ref as an
    ambiguous authority. The local smoke should install the package path directly
    and let uv resolve workspace-local sibling packages once."""
    for workflow_path in (RELEASE_WORKFLOW, RELEASE_DRY_RUN_WORKFLOW):
        job = _git_install_smoke_job(workflow_path)
        steps_text = "\n".join(step.get("run", "") for step in job["steps"])

        assert "git+file://" not in steps_text
        assert "@${GITHUB_SHA}" not in steps_text
        assert "@${GITHUB_REF_NAME}" not in steps_text


def test_release_gate_requires_git_install_smoke() -> None:
    """Publishing must wait for both install channels' smokes."""
    workflow = _load_workflow(RELEASE_WORKFLOW)
    release_needs = _jobs(workflow)["release"]["needs"]
    assert "release-install-smoke" in release_needs
    assert "release-git-install-smoke" in release_needs


def test_release_smoke_asserts_doctor_toolchain_report() -> None:
    """The wheelhouse smoke must prove ldflags version injection and the
    CLI<->binary handshake end-to-end via `providence doctor compiler`."""
    workflow = _load_workflow(RELEASE_WORKFLOW)
    smoke_steps = _jobs(workflow)["release-install-smoke"]["steps"]
    doctor_step = _step_run_block(
        smoke_steps, "Verify compiler toolchain doctor report matches the tag"
    )

    assert "doctor compiler" in doctor_step
    assert 'handshake["status"] == "ok"' in doctor_step


def test_release_build_step_does_not_pin_setuptools_scm_version() -> None:
    """There is no in-place pyproject.toml rewrite anymore (sync_versions.py
    was removed), so the working tree stays clean through the build and
    hatch-vcs resolves the exact tag without needing a pretend-version pin."""
    workflow = _load_workflow(REUSABLE_BUILD_WORKFLOW)
    build_steps = _jobs(workflow)["build"]["steps"]
    build_package_step = next(
        step for step in build_steps if step.get("name") == "Build packages"
    )
    env = build_package_step.get("env", {})
    assert "SETUPTOOLS_SCM_PRETEND_VERSION" not in env


def test_runtime_image_overlays_locked_venv_after_source_copy() -> None:
    """The runtime stage must not let a host .venv from a direct local Docker
    build overwrite the locked builder venv. CI stages .dockerignore before
    building, but the Dockerfile itself should remain safe if someone runs
    `docker build -f infrastructure/docker/Dockerfile .` locally."""
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    source_copy = dockerfile.index("COPY --chown=sdd:sdd . /app")
    context_venv_cleanup = dockerfile.index("RUN rm -rf /app/.venv")
    venv_copy = dockerfile.index("COPY --from=builder /app/.venv /app/.venv")

    assert source_copy < context_venv_cleanup < venv_copy


def test_runtime_image_blocks_trivy_reported_python_package_regressions() -> None:
    """Container builds must fail before Trivy if the runtime venv contains the
    exact vulnerable Python package versions reported by the security gate."""
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert "msgpack==1.2.1" in dockerfile
    assert "setuptools==84.0.0" in dockerfile
    assert "uv venv --clear /app/.venv" in dockerfile
    assert "--reinstall" in dockerfile
    assert "Version: (1\\.1\\.2|70\\.3\\.0|83\\.0\\.0)" in dockerfile
    assert "msgpack-*.dist-info/METADATA" in dockerfile
    assert "setuptools-*.dist-info/METADATA" in dockerfile
    assert (
        "--system --break-system-packages --reinstall setuptools==84.0.0" in dockerfile
    )
    assert (
        "/usr/local/lib/python*/site-packages/setuptools-*.dist-info/METADATA"
        in dockerfile
    )
    assert "msgpack-1.1.2.dist-info" in dockerfile
    assert "setuptools-70.3.0.dist-info" in dockerfile
    assert "setuptools-83.0.0.dist-info" in dockerfile
    assert "rm -rf /root/.cache/uv" in dockerfile
    assert "/usr/local/lib/python*/site-packages/pip" in dockerfile
    assert "pip/_vendor" in dockerfile
    assert (
        "pkg:pypi/(msgpack@1\\.1\\.2|setuptools@70\\.3\\.0|setuptools@83\\.0\\.0)"
        in dockerfile
    )
    assert "find / -path '*dist-info/METADATA'" in dockerfile
    assert "xargs -0 -r grep" in dockerfile


def test_docker_build_context_excludes_local_dependency_artifacts() -> None:
    dockerignore = DOCKERIGNORE.read_text(encoding="utf-8")

    assert ".venv/" in dockerignore
    assert "**/node_modules/" in dockerignore
    assert "dist/" in dockerignore


def test_runtime_image_satisfies_hadolint_entrypoint_policy() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")

    assert "\nUSER 1000\n" in dockerfile
    assert "CMD []" not in dockerfile
    assert 'ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]' in dockerfile
    assert 'CMD ["sh", "-c", "providence --help || exit 1"]' in dockerfile


def test_docker_build_paths_use_buildkit_buildx() -> None:
    makefile = _makefile_content()
    make_tasks = (REPO_ROOT / "tools" / "maintenance" / "make_tasks.py").read_text(
        encoding="utf-8"
    )
    security = _load_workflow(REUSABLE_SECURITY_WORKFLOW)
    test_workflow = _load_workflow(REUSABLE_TEST_WORKFLOW)

    assert "tools/maintenance/make_tasks.py docker-build" in makefile
    assert '--flags "$(DOCKER_BUILD_FLAGS)"' in makefile
    assert 'env["DOCKER_BUILDKIT"] = "1"' in make_tasks
    assert '"buildx"' in make_tasks
    assert '"--load"' in make_tasks
    assert "docker build -t providence" not in makefile

    security_steps = _jobs(security)["container-scan"]["steps"]
    security_runs = "\n".join(step.get("run", "") for step in security_steps)
    security_uses = "\n".join(step.get("uses", "") for step in security_steps)
    assert "docker/setup-buildx-action" in security_uses
    assert "docker buildx build --load --no-cache --pull" in security_runs
    assert "docker build -t sdd-framework:scan" not in security_runs

    container_steps = _jobs(test_workflow)["container-integrity"]["steps"]
    container_runs = "\n".join(step.get("run", "") for step in container_steps)
    container_uses = "\n".join(step.get("uses", "") for step in container_steps)
    assert "docker/setup-buildx-action" in container_uses
    assert "docker buildx build --load -t providence:latest" in container_runs
    assert "docker build -t providence:latest" not in container_runs


def test_release_dry_run_resolves_tag_without_sync_versions() -> None:
    workflow = _load_workflow(RELEASE_DRY_RUN_WORKFLOW)
    dry_run_steps = "\n".join(
        step.get("run", "") for step in _jobs(workflow)["dry-run"]["steps"]
    )
    assert "^[vV][0-9]+" in dry_run_steps
    assert 'VERSION="${VERSION#V}"' in dry_run_steps
    assert "sync_versions" not in dry_run_steps

    build_workflow = _load_workflow(REUSABLE_BUILD_WORKFLOW)
    build_steps = "\n".join(
        step.get("run", "") for step in _jobs(build_workflow)["build"]["steps"]
    )
    assert "sync_versions" not in build_steps
    dry_run_build_job = _jobs(workflow)["dry-run-build"]
    assert dry_run_build_job["needs"] == "dry-run"
    assert dry_run_build_job["with"]["tag"] == "${{ needs.dry-run.outputs.tag }}"


def test_release_dry_run_skips_exact_version_check() -> None:
    """Neither dry-run trigger path (workflow_dispatch with a candidate tag,
    or an automatic push to main) has a real Git tag at checkout time — the
    tag either hasn't been created yet (that's the point of a dry run) or
    doesn't exist at all (plain push). hatch-vcs can therefore never resolve
    exactly the placeholder/candidate `version` passed in, so the dry-run
    build must opt out of the reusable workflow's exact wheel-version check,
    or every dry run fails on a version mismatch that has nothing to do with
    whether the build actually works."""
    workflow = _load_workflow(RELEASE_DRY_RUN_WORKFLOW)
    dry_run_build_job = _jobs(workflow)["dry-run-build"]
    # _load_workflow's custom loader stringifies all YAML bools (needed to
    # handle the `on:` key elsewhere in the document), so `false` parses as
    # the string "false", not Python False.
    assert dry_run_build_job["with"]["verify-exact-version"] == "false"


def test_release_build_verifies_exact_version_by_default() -> None:
    """release.yml's real build (triggered by an actual tag push) must keep
    the exact wheel-version check enabled — unlike the dry run, the tag
    genuinely exists at checkout time there, so hatch-vcs resolving anything
    other than the exact tag version is a real bug, not a false positive."""
    workflow = _load_workflow(RELEASE_WORKFLOW)
    build_job = _jobs(workflow)["build"]
    assert "verify-exact-version" not in build_job.get("with", {})

    build_workflow = _load_workflow(REUSABLE_BUILD_WORKFLOW)
    verify_input = build_workflow["on"]["workflow_call"]["inputs"][
        "verify-exact-version"
    ]
    assert verify_input["default"] == "true"


def test_release_dry_run_triggers_on_push_to_main() -> None:
    workflow = _load_workflow(RELEASE_DRY_RUN_WORKFLOW)
    assert workflow["on"]["push"]["branches"] == ["main"]

    dry_run_steps = _jobs(workflow)["dry-run"]["steps"]
    push_step = next(
        step
        for step in dry_run_steps
        if step.get("name") == "Resolve version for automatic (push) trigger"
    )
    assert push_step["if"] == "github.event_name == 'push'"

    tag_format_step = _step_run_block(dry_run_steps, "Validate semver tag format")
    assert tag_format_step  # sanity: step still exists and has content
    tag_format_step_obj = next(
        step
        for step in dry_run_steps
        if step.get("name") == "Validate semver tag format"
    )
    assert tag_format_step_obj["if"] == "github.event_name == 'workflow_dispatch'"


def test_release_workflows_use_canonical_governance_compile_command() -> None:
    # release.yml's `build` job and release-dry-run.yml's `dry-run-build` job
    # both delegate to this single reusable workflow now — the governance
    # compile step only needs to be checked once, not per caller.
    workflow = _load_workflow(REUSABLE_BUILD_WORKFLOW)
    steps = "\n".join(step.get("run", "") for step in _jobs(workflow)["build"]["steps"])
    assert (
        "uv run python -m providence_cli governance compile --profile client" in steps
    )
    assert "uv run python -m providence_cli compile" not in steps
    assert "cp generated/client/build/governance-core.json" in steps
    assert "mkdir -p generated/client/build/final-template/.providence" in steps


def test_release_workflow_smoke_install_uses_local_dist_only() -> None:
    workflow = _load_workflow(RELEASE_WORKFLOW)
    smoke = _jobs(workflow)["release-install-smoke"]
    install_steps = "\n".join(
        step.get("run", "") for step in smoke["steps"] if "run" in step
    )
    assert "--no-index" in install_steps
    assert "--find-links dist" in install_steps


def test_release_workflows_build_cross_platform_runtime_wheelhouse() -> None:
    # Same reasoning as the governance-compile test above: both callers share
    # this one reusable workflow for the wheelhouse download step.
    workflow = _load_workflow(REUSABLE_BUILD_WORKFLOW)
    steps = "\n".join(step.get("run", "") for step in _jobs(workflow)["build"]["steps"])
    assert "--platform manylinux2014_x86_64" in steps
    assert "--platform win_amd64" in steps
    assert "--python-version 312" in steps
    assert "--find-links dist" in steps
    assert "dist/providence_cli-*.whl" in steps
    assert '"colorama>=0.4.6"' in steps


def test_release_job_depends_on_install_smoke() -> None:
    workflow = _load_workflow(RELEASE_WORKFLOW)
    jobs = _jobs(workflow)
    assert set(jobs["release"]["needs"]) == {
        "release-install-smoke",
        "release-git-install-smoke",
        "release-binary-install-smoke",
    }


def test_release_dry_run_has_windows_install_smoke_lane() -> None:
    workflow = _load_workflow(RELEASE_DRY_RUN_WORKFLOW)
    jobs = _jobs(workflow)
    assert "release-install-smoke" in jobs

    smoke = jobs["release-install-smoke"]
    matrix_os = smoke["strategy"]["matrix"]["os"]
    assert "windows-latest" in matrix_os
    assert "ubuntu-latest" in matrix_os
    assert smoke["needs"] == "dry-run-build"


def test_release_workflow_permissions_are_job_scoped() -> None:
    workflow = _load_workflow(RELEASE_WORKFLOW)

    top_level_permissions = workflow.get("permissions") or {}
    assert top_level_permissions.get("contents") != "write"
    assert top_level_permissions.get("id-token") != "write"

    jobs = _jobs(workflow)
    for job_name in ("validate", "build", "release-install-smoke"):
        job_permissions = jobs[job_name].get("permissions") or {}
        assert job_permissions.get("contents") != "write"
        assert job_permissions.get("id-token") != "write"

    assert jobs["release"]["permissions"]["contents"] == "write"
    assert jobs["provenance"]["permissions"]["id-token"] == "write"


def test_release_signing_step_is_blocking() -> None:
    workflow = _load_workflow(RELEASE_WORKFLOW)
    release_steps = _jobs(workflow)["release"]["steps"]
    sign_step = next(
        step
        for step in release_steps
        if "sigstore/gh-action-sigstore-python" in step.get("uses", "")
    )
    assert "continue-on-error" not in sign_step


def test_release_signing_uses_real_sigstore_action_with_oidc_permission() -> None:
    """The signing action must be a real, resolvable action (not a placeholder),
    and the job must request the OIDC token it needs for keyless signing."""
    workflow = _load_workflow(RELEASE_WORKFLOW)
    release_job = _jobs(workflow)["release"]
    sign_step = next(
        step
        for step in release_job["steps"]
        if "sigstore/gh-action-sigstore-python" in step.get("uses", "")
    )
    assert "@790bc6befb9d733738f18d8f895854b453640ec9" in sign_step["uses"]
    assert release_job["permissions"]["id-token"] == "write"


def test_release_workflows_invoke_tools_release_scripts_as_modules() -> None:
    """tools/release/*.py scripts do package-relative imports (e.g.
    stage_packaged_compiler_assets.py imports validate_release_assets). Invoking
    them as bare scripts (`python path/to/script.py`) puts the script's own
    directory on sys.path instead of the repo root, so the import fails with
    ModuleNotFoundError. They must be invoked as modules (`python -m
    tools.release.<name>`), which puts the repo root (cwd) on sys.path."""
    # Both release.yml's `build` job and release-dry-run.yml's `dry-run-build`
    # job delegate to reusable-release-build.yml — checking it once covers
    # both callers.
    workflow = _load_workflow(REUSABLE_BUILD_WORKFLOW)
    steps = "\n".join(step.get("run", "") for step in _jobs(workflow)["build"]["steps"])
    assert "python tools/release/stage_packaged_compiler_assets.py" not in steps
    assert "python -m tools.release.stage_packaged_compiler_assets" in steps
