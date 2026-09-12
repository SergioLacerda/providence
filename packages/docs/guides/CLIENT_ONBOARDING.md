# Client Onboarding Guide

Get your SDD workspace running with governed bootstrap and agent command packs.

## Prerequisites

- Python 3.10+
- Git
- [uv](https://astral.sh/uv) (required)

## Quick Start (One Command)

> Prerequisite: install the Providence CLI first — see [Step 1](#step-by-step-setup-client-project)
> below if you haven't already.

After `providence install --wizard` has generated and deployed your project template,
`providence init --default` runs the full client bootstrap chain in one step: workspace
profile, governance generate (`--full-bootstrap`), skills bootstrap
(`--full-bootstrap --regenerate-seeds`), and runtime validation. It is
equivalent to `providence init --type client --name local-dev --language en --force`,
with any of `--type`/`--name`/`--language`/`--force` you pass explicitly
taking precedence.

Pass `--language en|pt-BR` (case-insensitive) to persist a client-side
language preference into `.providence/profile`; it is bridged into the compiled
`.providence/metadata.json`'s `language_context` the next time `providence governance
compile` runs, unless a prior `providence wizard` run already populated it (wizard
output always takes precedence).

```bash
cd <your-project>
providence install --wizard
providence init --default
providence governance validate
```

`providence install --wizard` deploys generated files into the project root by default.
Use `--only-template` to stop after producing `generated/client/build/final-template/`.
It also supports `--from-file <path>` (bring your own governance JSON) and
`--non-interactive` (skip prompts) — see `docs/spec/reference/commands/cli.md`
for the full flag reference.

Each step is skipped automatically if it already ran (idempotent re-run); use
`--force` (or `--default`, which implies it) to re-run all steps.

## Step-by-step Setup (Client Project)

**Step 1 — Install the Providence CLI from a released version.** Two supported channels,
both pinned to a tag:

```bash
# 1a. (Preferred) GitHub Release wheelhouse — the official, CI-proven channel.
#     Download the dist/ assets attached to the tagged release
#     (https://github.com/SergioLacerda/providence/releases), then:
pip install --no-index --find-links <dist-dir> providence-cli

# 1b. (Alternative) Tag-pinned git install — no asset download, needs git + network.
#     Replace vX.Y.Z with the latest release tag from the releases page:
uv tool install "git+https://github.com/SergioLacerda/providence@vX.Y.Z#subdirectory=packages/interfaces/providence_cli"
```

`.github/workflows/release.yml` verifies the wheelhouse install on `windows-latest`
and `ubuntu-latest` before publishing. The wheelhouse wheel bundles the native
`sdd-compile` binaries (`providence_core/_native/`), so no runtime download is needed;
the git channel resolves the binary from the release assets at first use.

> **Development installs only:** installing without a tag
> (`git+https://...#subdirectory=...`) builds the **default branch HEAD** — an
> unreleased version. Use it only for developing providence itself, never for
> client onboarding: HEAD code paired with release binaries is exactly the skew
> class the version handshake exists to reject.

```bash
# 2. Enter your project and run the wizard
cd <your-project>
providence install --wizard

# 3. Activate runtime/governance in the generated template
#    (this single command also runs steps 4-6 below automatically)
providence init --type client --name <your-project> --force

# 4. Compile + generate + sign + handshake
providence governance generate --full-bootstrap

# 5. Generate skills/commands/seeds for agent entrypoints
providence skills --full-bootstrap --regenerate-seeds

# 6. Verify runtime/governance health
providence runtime status
providence governance validate

# 7. Verify the compiler toolchain (read-only JSON report)
providence doctor compiler
```

A healthy `providence doctor compiler` report shows `binary.resolution_rule` as `packaged`
(wheelhouse install) or `download` (git install), `handshake.status: "ok"` (or
`skipped_dev_binary` on dev builds), and `validate.ok: true` once governance has been
generated. Anything else — see the
[Windows standalone troubleshooting guide](windows-standalone-troubleshooting.md).

### Windows signing troubleshooting

Key generation (`providence governance keygen`), signing (`providence governance sign`,
full bootstrap), and runtime signature verification all use a native Ed25519
backend (the `sdd-compile` binary) and do not shell out to OpenSSL — Windows
standalone installs do not require `openssl.exe` on `PATH`.

The `sdd-compile` binary itself is resolved in this order: `SDD_COMPILE_BIN`
env var → repo-local build → `PATH` → binary bundled in the providence-core wheel →
download from the matching GitHub Release.

Only wheels built by the release CI bundle the native binaries. A source
install (for example `uv tool install "git+https://...#subdirectory=..."`)
has no bundled binary and falls back to the release download, which requires
working TLS certificate verification. If that download fails with
`CERTIFICATE_VERIFY_FAILED`, either:

- install from the release wheelhouse instead (the CI-proven channel above:
  `pip install --no-index --find-links <dist-dir> providence-cli`) — the bundled
  binary makes the download unnecessary; or
- download `sdd-compile-windows-amd64.exe` from the GitHub Release manually
  and point `SDD_COMPILE_BIN` at it; or
- behind a TLS-intercepting corporate proxy, set `SSL_CERT_FILE` to a CA
  bundle that includes the proxy's certificate.

Full bootstrap and client onboarding use the default key id `dev-01`, so an
idempotent bootstrap can print:

```text
Key dev-01 already exists at .providence\trust\dev-01.key
```

That line is informational. A direct command such as
`providence governance sign --key-id my-org-01` resolves
`.providence\trust\my-org-01.key`; it does not fall back to `dev-01`. To use a custom
key id directly, generate it first:

```bash
providence governance keygen --key-id my-org-01
providence governance sign --key-id my-org-01
```

### Zero-state onboarding behavior

`providence install --wizard` runs a single guided flow in an empty workspace — no
phase menu, no manual staging required:

1. Language, hook-mode, and agent-selection prompts (skippable via
   `--non-interactive`)
2. Governance generation (or `--from-file <path>` to supply your own)
3. Compilation and seed generation into `generated/client/build/`
4. Deployment of the final template into the project root

Runtime activation is intentionally deferred to step 3 (`providence init` + bootstrap commands).

### Seedling Selection

The interactive seedling selector groups options into four sections:

- **CORE** — `governance`, `agents-md`, `prompt-commands`, `activation-guide`,
  `verify`. Always part of the recommended default.
- **IDEs** — `vscode`, `cursor`, `antigravity`.
- **AGENTS** — `claude`, `codex`, `gemini`, `copilot`.
- **OPTIONAL** — `ci`, `compliance`, `personal-overlay`. Off by
  default; select explicitly to generate `.github/workflows/sdd-validation.yml`
  or `compliance.seed.json`.

Leaving the selection empty applies the **recommended default** (CORE + all
IDEs + all AGENTS) — it is not "generate everything," and it never includes
CI/CD or compliance artifacts unless you opt in.

Only the artifacts belonging to your selection are generated, deployed, and
validated. Files from a previous wizard run that belong to options you no
longer select are **not** deleted automatically — a future `--prune-unselected`
mode may add that, but the current behavior never removes files on its own.

## Agent Custom Commands (Slash/Prompt Packs)

Custom command packs are generated from canonical `.providence` artifacts.

- Copilot prompts: `.github/prompts/*.prompt.md`
- Cursor rules: `.cursor/rules/sdd-commands.mdc`
- Codex commands: `.codex/commands.md` + `.codex/skills/*.prompt.md`
- Gemini commands: `.gemini/commands.md`

Core aliases include: `/sdd-ask`, `/sdd-organize`, `/sdd-diagnose`.

`/sdd-ask` is a thin adapter over the CLI command `providence ask`. The CLI is the
single governed source of truth for intent classification, execution gate, and
handoff guidance; slash commands and prompt-submit hooks must not classify or
route independently. When `providence ask` reports implementation intent, it emits a
governed handoff (`next_valid_path: implementation_handoff`) for the calling
agent. It does not execute implementation, bind a provider, or invoke an
analysis skill automatically; the structured fields `delegation_executed` and
`provider_bound` remain `false` until a future explicit delegation contract
exists.

To regenerate:

```bash
providence skills --full-bootstrap
```

## CLI Reference

For authoritative flags and command contracts:

- `docs/spec/reference/commands/cli.md`

## Telemetry

Compliance events are written to `.providence/runtime/compliance-events.jsonl` (JSONL, append-only).

```bash
# View latest events
cat .providence/runtime/compliance-events.jsonl | tail -20

# Filter violations only
grep '"event": "VIOLATION"' .providence/runtime/compliance-events.jsonl
```

To override the log path: `export SDD_COMPLIANCE_LOG=/path/to/events.jsonl`
To disable writes: `export SDD_COMPLIANCE_LOG=disabled`

## Troubleshooting

### `/sdd-ask` returns `API Error: 500`

This usually indicates a provider/IDE API incident, not a local Providence CLI failure.

1. Stop retrying the same slash command in the IDE for that turn.
2. Run the local governed fallback in terminal:

```bash
providence runtime status
providence governance validate
providence ask --full "<your question>"
```

1. Capture the `request_id` from the 500 response and report it for incident triage.
