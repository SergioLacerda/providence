# Providence

> **📖 [Documentation](https://sergiolacerda.github.io/providence/)** &nbsp;·&nbsp; **🧭 [Selector](https://sergiolacerda.github.io/providence/selector/)**

**Executable governance platform for agentic systems**

Providence turns architectural and governance specifications into executable
runtime contracts. It compiles governed source artifacts, validates drift,
enforces runtime policies, and records compliance evidence for AI-assisted
systems.

<div align="center">

| Pipeline | Quality | Ecosystem |
|:---:|:---:|:---:|
| [![Health](https://github.com/SergioLacerda/providence/actions/workflows/health.yml/badge.svg?branch=main)](https://github.com/SergioLacerda/providence/actions/workflows/health.yml) | [![CodeQL](https://github.com/SergioLacerda/providence/actions/workflows/codeql.yml/badge.svg?branch=main)](https://github.com/SergioLacerda/providence/actions/workflows/codeql.yml) | [![Built with uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv) |
| [![Validation](https://github.com/SergioLacerda/providence/actions/workflows/sdd-validation.yml/badge.svg?branch=main)](https://github.com/SergioLacerda/providence/actions/workflows/sdd-validation.yml) | [![Release](https://github.com/SergioLacerda/providence/actions/workflows/release.yml/badge.svg)](https://github.com/SergioLacerda/providence/actions/workflows/release.yml) | [![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/) |
| [![Docs](https://github.com/SergioLacerda/providence/actions/workflows/docs.yml/badge.svg?branch=main)](https://github.com/SergioLacerda/providence/actions/workflows/docs.yml) | [![Governance: SDD](https://img.shields.io/badge/governance-SDD-blueviolet)](docs/spec/canonical/core/) | [![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE) |
| | [![Coverage](https://codecov.io/gh/SergioLacerda/providence/branch/main/graph/badge.svg)](https://codecov.io/gh/SergioLacerda/providence) | |

**[Documentation](https://sergiolacerda.github.io/providence/)** •
**[Client Onboarding](docs/guides/CLIENT_ONBOARDING.md)** •
**[CLI Reference](docs/spec/reference/commands/cli.md)** •
**[Technical Guide](docs/guides/TECHNICAL_GUIDE.md)** •
**[Contributing Setup](docs/guides/ONBOARDING.md)**

</div>

---

## Overview

Providence provides four core functions:

- compile governed specifications into machine-consumable artifacts
- validate governance integrity and specification drift
- enforce runtime and workflow policies through CLI and skills
- record compliance and audit evidence during execution

It is designed for teams that want governance to be verified during execution,
not only documented after the fact.

## Problem Statement

Specification-driven governance for AI systems commonly breaks down in practice:

- mandates exist as documentation but are not enforced at runtime
- specification changes drift from active contracts without detection
- compliance is checked late, often after execution
- operational evidence is inconsistent or missing

Providence addresses this by compiling governed source material into executable
artifacts, validating them before use, and enforcing a fail-closed model where
required governance conditions must hold before sensitive execution proceeds.

## Architecture Overview

At a high level, the platform is organized into three layers:

| Layer | Purpose | Examples |
|---|---|---|
| Core | runtime contracts, telemetry, governance primitives | `providence_core`, `providence_runtime`, `providence_telemetry` |
| Features | compilation, integration, skill and adapter workflows | `sdd_compiler`, `providence_integration`, `providence_skills` |
| Interfaces | user-facing entrypoints | `providence_cli`, `providence_wizard` |

Outside `packages/`, `apps/landing/` is the public landing page (Astro +
React), published at the site root (`/`) alongside the MkDocs docs
(`/docs/`) and the interactive Selector (`/selector/`).

Execution flow:

```text
Governed source docs
        ↓
compiler / generation pipeline
        ↓
compiled artifacts + signatures
        ↓
runtime + CLI enforcement
        ↓
compliance events and audit evidence
```

For deeper architecture material, see `docs/architecture/README.md` and
`docs/spec/canonical/`.

## Quick Start

### Client / Adopter Flow

Install from the tagged release wheelhouse (`providence-cli` plus every
`providence-*` sibling package it depends on — this is a multi-package
monorepo, so those siblings are never published to PyPI on their own):

```bash
uv tool install providence-cli --find-links "https://github.com/SergioLacerda/providence/releases/expanded_assets/v1.0.17"
cd your-project
providence install --wizard
providence init --default
providence governance validate
```

> **Do not** use `uv tool install git+https://...#subdirectory=packages/interfaces/providence_cli`
> — it cannot resolve the `providence-*` sibling packages from outside a full
> local workspace checkout and fails with "was not found in the package
> registry", tag-pinned or not.

Detailed onboarding, release verification, security, and workflow guidance:
[`docs/guides/README.md`](docs/guides/README.md).

### Contributor Flow

Use this path when working on the Providence repository itself:

```bash
git clone https://github.com/SergioLacerda/providence.git
cd providence
uv run providence setup run
uv run providence init --default
make hooks-install
make pre-delivery
```

Contributor setup and troubleshooting: `docs/guides/ONBOARDING.md`

After setup, run `make pre-delivery`, update governed artifacts or golden files
when intentionally required, and submit the changes for human review.

## Core Workflows and Details

See the [detailed workflows README](docs/guides/README.md) for governance,
runtime, agent onboarding, quality gates, release verification, security, and
Docker build guidance.

## Documentation Paths

Choose the shortest path for your intent:

| Need | Start Here |
|---|---|
| install and bootstrap a governed project | `docs/guides/CLIENT_ONBOARDING.md` |
| work on this repository | `docs/guides/ONBOARDING.md` |
| understand architecture | `docs/architecture/README.md` |
| inspect CLI commands | `docs/spec/reference/commands/cli.md` |
| navigate the documentation system | `docs/README.md` |
| view the published docs site | <https://sergiolacerda.github.io/providence/> |

## License

This project is licensed under the **MIT License**.

- Repository: <https://github.com/SergioLacerda/providence>
- Published docs: <https://sergiolacerda.github.io/providence/>
- License text: `LICENSE`
- Attribution and professional services notice: `NOTICE.md`
