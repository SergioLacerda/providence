# Sovereign Factory: Support Tools (`tools/`)

Developer and CI utilities for the Providence monorepo.
These tools follow the **Sovereign Factory** pattern: they are self-contained, deterministic, and environment-agnostic via **PEP 723**.

---

## Execution Standards

All tools should be executed via **uv** to ensure dependency isolation and cross-platform (Windows/Linux) parity.

### 1. Unified CLI (Recommended)
The Providence CLI provides a discovery layer for all tools:
```bash
providence tools list                         # List public active tools
providence tools list --all                   # Include internal, deprecated, and project entries
providence tools list --include-deprecated    # Include deprecated entries with replacements
providence tools list --json                  # Emit machine-readable registry output
providence tools run <tool-id>                # Execute by manifest ID (e.g. maintenance/lint_all)
providence tools run <category>/<script>.py   # Legacy path execution remains supported
```

`providence tools list` is manifest-driven when `tools/registry.yaml` exists. The
manifest is a curated discovery contract: it separates public commands from
internal helpers, deprecated compatibility scripts, and self-contained tool
projects. If the manifest is absent, the CLI falls back to recursive Python
script discovery for migration compatibility.

### 2. Direct Execution (PEP 723)
Tools can be run directly using `uv`, which will automatically manage the script's dependencies:
```bash
uv run python tools/maintenance/lint_all.py
```

---

## Directory Map And Ownership

```
tools/
├── architecture/
│   ├── validate_imports.py       Layer isolation validator
│   ├── validate_cycles.py        Import cycle validator
│   ├── validate_import_style.py  Relative import style validator
│   ├── validate_class_size.py    Class size validator
│   └── score.py                  Architecture health score
│
├── ci/
│   ├── check_*.py                Workflow-facing policy and readiness checks
│   ├── environment_gates.py      CI environment and runtime drift gates
│   └── config/                   CI check configuration
│
├── docs/
│   ├── check_links.py            MkDocs/docs link checker
│   └── check_runtime_path_schema.py Runtime documentation path validator
│
├── deploy/
│   └── validate_deploy_contract.py Deployment contract validator
│
├── debug/
│   └── debug_msgpack.py          Local compiled-artifact inspection helper
│
├── governance/
│   ├── compliance.py             [Hardened] Ed25519 source governance validator (P003)
│   ├── seedling_loader.py        Auto-load and activate governance seedlings
│   ├── personal_overlay.py       Personal overlay resolution
│   └── capability_sync_audit.py  Runtime capability synchronization audit
│
├── guardrails/
│   ├── core/                     Guardrail analyzer framework primitives
│   ├── analyzers/                Runtime and telemetry analyzers
│   ├── checkers/                 Specialized guardrail checkers
│   ├── reporters/                Shared report rendering
│   ├── cli.py                    Module CLI entry point
│   └── analysis.yaml             Default guardrails configuration
│
├── health/
│   └── health_check.py           Portable health engine (uv-powered)
│
├── lib/
│   └── providence_env.py         Shared repo/path helpers for tools
│
├── maintenance/
│   ├── make_tasks.py             Makefile target implementation router
│   ├── lint_all.py               Orchestrated monorepo linting (ruff, mypy, arch)
│   └── thread_audit_report.py    Thread/process audit documentation generator
│
├── release/
│   ├── validate_release_assets.py Release asset validator
│   ├── stage_packaged_compiler_assets.py Packaged compiler asset staging
│   └── verify_wheel_*.py         Wheel asset and dependency checks
│
├── scripts/
│   ├── deployment_manager.py     Deployment helper
│   └── git-hooks/                Repository Git hook templates
│
├── sdd-compile/
│   ├── go.mod                    Self-contained Go compiler tool project
│   ├── cmd/                      Compiler command implementations
│   ├── internal/                 Compiler internals
│   └── tests/                    Go contract, smoke, signing, and performance tests
│
├── testing/
│   ├── diagnostics.py            14-check diagnostic suite
│   ├── run-all-tests.py          Parallelized multi-layer pytest runner (xdist)
│   ├── generate-schemas.py       Contract schema generator
│   └── update-golden-snapshots.py Update contract test fixtures
│
├── analysis/
│   ├── evaluate_pending_completion.py Active `.analysis` lifecycle evaluator
│   └── deprecated/               Archived analysis scripts superseded by guardrails
│
├── quiz/
│   └── quiz_executor.py          Local quiz/check helper
│
└── verify_mkdocs_paths.py        Verify nav paths in mkdocs.yml
```

## Tool Registry Contract

`tools/registry.yaml` is the source of truth for the `providence tools` discovery
surface.

Required fields per entry:

- `id`: stable CLI-facing identifier.
- `path`: repository-relative path under `tools/`.
- `visibility`: `public`, `internal`, `deprecated`, or `project`.
- `status`: `active`, `experimental`, or `deprecated`.
- `runner`: `uv-python`, `python-module`, `go-project`, or `external`.
- `description`: short user-facing summary.

Optional fields include `replacement`, `category`, `tags`, `docs_refs`,
`ci_consumers`, `module`, and `allow_direct_run`.

Default list output includes only `visibility: public` and `status: active`
entries. Internal, deprecated, and project entries require explicit list flags.
Manifest IDs and legacy relative paths are both accepted by `providence tools run`
during the migration period.

### Placement Rules

- Put workflow-only checks in `tools/ci/`.
- Put reusable source-analysis framework code in `tools/guardrails/`.
- Put architecture boundary checks in `tools/architecture/`.
- Put documentation validators in `tools/docs/`.
- Put Makefile/developer workflow implementations in `tools/maintenance/`.
- Put release packaging and artifact checks in `tools/release/`.
- Put shared helpers in `tools/lib/` only when they are used across multiple tool categories.
- Treat `tools/sdd-compile/` as a self-contained tool project, not as a normal script bucket.
- Treat `tools/analysis/evaluate_pending_completion.py` as `.analysis` lifecycle tooling, not as a guardrails analyzer.
- Treat `tools/analysis/deprecated/` as archived compatibility context only.

---

## Core Workflows

### Testing (Parallel & Layered)
```bash
# Run all tests in parallel
make test

# Run tests for a specific layer (e.g. core)
uv run python tools/testing/run-all-tests.py --layer core

# Pass extra arguments to pytest
make test ARGS="-- -k test_compliance"
```

### Linting & Auto-fix
```bash
# Run all quality checks (ruff, mypy, architecture)
make lint

# Apply all safe auto-fixes
make lint-fix
```

### Hardened Governance (P003)
To comply with the "Human-in-the-loop" mandate (P003), governance changes must be signed with an Ed25519 key:
```bash
# 1. Generate your auditor key (one-time)
providence governance keygen --key-id human-sergio

# 2. Sign the source governance configuration
providence governance sign --source --key-id human-sergio
```

---

## Tool Status (Sovereign Factory Ready)

| Tool | Engine | Status | Notes |
|---|---|---|---|
| `lint_all.py` | PEP 723 | ✅ NEW | Orchestrates ruff + mypy + arch |
| `run-all-tests.py` | PEP 723 | ✅ UPGRADED | Parallel execution + full coverage |
| `compliance.py` | PEP 723 | ✅ HARDENED | Validates Ed25519 signatures |
| `health_check.py` | PEP 723 | ✅ ACTIVE | Core CI/CD gate |
