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

The official, CI-proven install channel is the GitHub Release wheelhouse: download
the `dist/` assets from a tagged [GitHub Release](https://github.com/SergioLacerda/providence/releases)
and install `providence-cli` from those local files, e.g.:

```bash
python -m venv .providence-cli
.providence-cli/bin/python -m pip install --no-index --find-links <path-to-downloaded-dist> providence-cli
```

On Windows PowerShell, use the venv's Windows entrypoint instead:

```powershell
python -m venv .providence-cli
.\.providence-cli\Scripts\python.exe -m pip install --no-index --find-links <path-to-downloaded-dist> providence-cli
```

`.github/workflows/release.yml` installs from these exact release artifacts on
both `windows-latest` and `ubuntu-latest` before a release is published, so this
path is proven cross-platform.

#### Verifying a Release

Every tagged release publishes `dist/SHA256SUMS` alongside the standalone
`sdd-compile` binaries, signed with [Sigstore](https://www.sigstore.dev/)
(keyless signing — no key management on your end). To verify a downloaded
binary:

```bash
# Checksum
sha256sum -c SHA256SUMS --ignore-missing

# Sigstore signature (requires the sigstore CLI: pip install sigstore)
python -m sigstore verify github \
  --cert-identity "https://github.com/SergioLacerda/providence/.github/workflows/release.yml@refs/tags/<tag>" \
  dist/sdd-compile-linux-amd64
```

Every release also carries a [SLSA build provenance
attestation](https://slsa.dev/) over the full `dist/` directory, verifiable with
the GitHub CLI: `gh attestation verify dist/<file> --repo
SergioLacerda/providence`.

> **Current scope:** checksums and Sigstore signatures above cover the standalone
> `sdd-compile` binaries. Python wheel coverage
> (`providence_cli-*.whl` and friends) is tracked separately — see the release pipeline's
> own CI configuration for the latest status before relying on wheel-level
> verification.

If you have [uv](https://astral.sh/uv), skip the manual download above with a
single command that installs straight from the same tagged release's wheelhouse
(`providence-cli` plus every `providence-*` sibling package it depends on — this
project is a multi-package monorepo, so those siblings are never published to
PyPI on their own; `--find-links` here points at the tag's own release-assets
page, not a git checkout). Replace `v1.0.15` with the tag you want:

```bash
uv tool install providence-cli --find-links "https://github.com/SergioLacerda/providence/releases/expanded_assets/v1.0.15"
cd your-project
providence install --wizard
providence init --default
providence governance validate
```

> **Do not** use `uv tool install git+https://...#subdirectory=packages/interfaces/providence_cli`
> — it cannot resolve this project's `providence-*` sibling packages from
> outside a full local workspace checkout and fails with "was not found in the
> package registry". Use the `--find-links` form above, or the manual
> download in [Client / Adopter Flow](#client--adopter-flow), instead.

If PowerShell reports `providence : O termo 'providence' nao e reconhecido`,
the CLI is not on that shell's `PATH`. Either reopen the terminal after
installation, add the install directory to `PATH`, or run from a source checkout
with `uv`:

```powershell
$env:UV_CACHE_DIR = "$PWD\.uv-cache"
uv run providence install --wizard
```

Setting `UV_CACHE_DIR` inside the checkout is optional, but it avoids failures
when the global `uv` cache under `%LOCALAPPDATA%\uv\cache` is not writable.

`providence install --wizard` runs a single guided flow (language, hook mode, agent
selection, then generate) — no phase menu to navigate. Useful flags:

- `--only-template` — generate the final template bundle without deploying it
  into your project root
- `--from-file <path>` — bring your own hand-edited mandates/guidelines JSON
  instead of generating a fresh one
- `--non-interactive` — skip prompts, reusing a prior `wizard-config.json` or
  sane defaults
- `--output-dir <path>` — change where the generated template lands

`providence wizard run` still works as a legacy alias and deploys the generated files
into the project root by default.

The wizard's final output tells you the exact next command to run to
complete the M015 governance handshake — run it before your agent's first
governed action.

This path is cross-platform and does not require cloning this repository first.

Detailed walkthrough: `docs/guides/CLIENT_ONBOARDING.md`

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

#### Building the Docker image locally

`make docker-build` (and `infrastructure/docker/Dockerfile`) requires the
BuildKit-only `--mount=type=cache` syntax, which needs the `docker buildx` CLI
plugin. Without it you'll see `the --mount option requires BuildKit`, and then
`buildx component is missing` if you force `DOCKER_BUILDKIT=1`. Install the
plugin first (e.g. `sudo pacman -S docker-buildx` on Arch/Manjaro, or
`sudo apt install docker-buildx-plugin` on Debian/Ubuntu) before running
`make docker-build`.

## Core Workflows

### Governance

```bash
providence governance compile
providence governance validate
providence governance score --verbose
providence governance keygen --key-id my-org-01
providence governance sign --key-id my-org-01
```

`providence governance sign --key-id <id>` reads `.providence/trust/<id>.key` unless
`--key-path` is provided. Full bootstrap and client onboarding use `dev-01` by
default, so a bootstrap log can mention `.providence/trust/dev-01.key` even when a
separate direct signing flow uses another key id.

`providence governance sign` and runtime signature verification use a native Ed25519
backend (the `sdd-compile` binary) and do not require `openssl.exe` on
Windows or any other platform. `providence governance keygen` still shells out to
OpenSSL to generate the key pair; if keygen fails with `[WinError 2]` while
running `openssl`, verify the dependency first:

```powershell
where openssl
openssl version
```

Install OpenSSL or update `PATH` before rerunning `providence governance keygen`.

### Runtime and Audit

```bash
providence runtime status
providence audit
providence skills list
providence skills describe sdd-validate-governance
```

## Agent Onboarding After Governance Activation

After governance artifacts are active in a project, use the governed skills
interface to inspect and validate the runtime before delegating work to agents:

```bash
providence skills list
providence skills describe sdd-validate-governance
providence skills run sdd-validate-governance
```

### Quality Gates

```bash
providence test run
providence lint run
make pre-delivery
```

Complete command reference: `docs/spec/reference/commands/cli.md`

`providence ask` is the single governed entrypoint for governance queries and agent
handoff decisions. Prompt-submit hooks and `/sdd-ask` adapters route through the
CLI decision instead of classifying intent themselves. An implementation handoff
from `providence ask` is guidance for the calling agent to use an authorized execution
path; it is not provider delegation, provider binding, or evidence that
implementation already ran.

## Security and Trust Model

Providence uses a fail-closed governance model for sensitive execution paths.

- governance artifacts can be signed with Ed25519 keys
- runtime validation can reject missing or invalid signatures
- human review requirements are represented as governed policy, not ad hoc process
- compliance events are emitted for auditability and post-run inspection

Recommended production posture:

```bash
export SDD_SIGNATURE_MODE=strict
```

Further reading:

- `docs/spec/reference/SECURITY.md`
- `docs/spec/canonical/core/policies/P003_MANDATORY_HUMAN_REVIEW.md`

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

## Contributing Workflow

Contributor changes are expected to pass local quality gates before handoff:

1. run `make pre-delivery`
2. update governed artifacts or golden files when intentionally required
3. submit for human review

Governed review and delivery rules are documented under the canonical policy
set in `docs/spec/canonical/core/`.

## License

This project is licensed under the **MIT License**.

- Repository: <https://github.com/SergioLacerda/providence>
- Published docs: <https://sergiolacerda.github.io/providence/>
- License text: `LICENSE`
- Attribution and professional services notice: `NOTICE.md`
