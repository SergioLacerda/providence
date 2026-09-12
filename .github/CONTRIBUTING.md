# Contributing to Providence

Thank you for your interest in contributing. This document covers how to set up your environment, run tests, and submit changes.

## Table of Contents

- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [Linting and Type Checking](#linting-and-type-checking)
- [Governance Compliance](#governance-compliance)
- [Submitting Changes](#submitting-changes)
- [Commit Message Convention](#commit-message-convention)

---

## Development Setup

**Prerequisites:** Python 3.10+, [uv](https://docs.astral.sh/uv/)

```bash
# Clone and enter the repo
git clone https://github.com/SergioLacerda/providence.git
cd providence

# Install all workspace dependencies
make install

# Verify the setup
providence runtime status
```

---

## Project Structure

```
packages/
  core/
    providence_core/        # Domain models, fingerprinting, registry
    sdd_compiler/    # Governance artifact compiler
    providence_telemetry/   # Observability / audit trail
  features/
    providence_integration/ # Integration layer (external tools)
  interfaces/
    providence_cli/         # CLI entry point (`sdd` command)
    providence_wizard/      # Interactive setup wizard
tests/
  unit/              # Fast, isolated unit tests
  integration/       # Tests with real I/O and CLI
  contract/          # Golden-file contract tests
docs/
  spec/canonical/    # Governance specifications (authoritative)
```

---

## Running Tests

```bash
# All tests (unit + integration + contract)
make check

# Unit + integration only, with coverage
make test

# HTML coverage report
make coverage
```

Tests require **90% coverage** on `packages/`. The threshold is enforced by `--cov-fail-under` in the `test` and `coverage` Makefile targets.

---

## Linting and Type Checking

```bash
make lint
```

This runs, in order:

| Tool | Role |
|---|---|
| `ruff` | Fast linting and import sorting |
| `ruff format` | Code formatting (line length: 88) |
| `mypy` | **Canonical** static type checker (strict mode) |
| `bandit` | Security scanning |

> **Type checking policy:** mypy is the only type-checking gate (strict mode).

---

## Governance Compliance

Providence enforces its own governance rules at runtime. Before opening a PR:

```bash
# Compile governance artifacts
providence governance compile

# Validate compliance
providence governance validate

# Check workspace health
providence runtime status
```

All three must pass cleanly before submitting.

---

## Submitting Changes

SDD enforces **Policy P003: Mandatory Human Review**. This means:

1. **Agents propose, humans dispose** — no autonomous commits or merges
2. Every PR description must contain one of:
   - `Human Review: [Signed-off]`
   - `Review-Token: <token>`
3. The CI workflow will reject PRs that lack this evidence

### Steps

1. Fork the repo and create a feature branch
2. Make your changes
3. Run `make check` and `make lint`
4. Run `providence governance validate`
5. Open a PR using the [pull request template](.github/pull_request_template.md)
6. Include `Human Review: [Signed-off]` in the PR body

---

## Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

[optional body]
```

Common types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`

Examples:
```
feat(compiler): add fingerprint caching for incremental builds
fix(cli): handle missing .providence/profile gracefully
docs(contributing): add governance compliance steps
```

---

## Questions

Open a [GitHub Discussion](https://github.com/SergioLacerda/providence/discussions) for questions, or file a [bug report](.github/ISSUE_TEMPLATE/BUG_REPORT.md) for defects.
