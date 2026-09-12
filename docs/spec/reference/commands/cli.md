# Providence CLI Reference (v3.1)

The `providence` command is the main entry point for framework operations.

## Profile Detection

The Providence CLI operates in one of two profiles: **master** (framework development) or **client** (project instance). The profile is auto-detected using the following priority:

1. `--profile` flag (highest priority)
2. `SDD_PROFILE` environment variable
3. `.providence/profile` (`[sdd] type = master|client`)
4. If workspace is not initialized, fail with actionable message (`providence init`)

```bash
# Use explicit profile override
sdd --profile master governance compile
sdd --profile client wizard run

# Or set via environment
SDD_PROFILE=master providence governance compile
```

The current profile is inferred automatically in most cases. Profile affects which operations are permitted:

| Command | master | client |
|---------|--------|--------|
| `governance compile` | ✅ | ✅ |
| `governance load/validate` | ✅ | ✅ |
| `wizard run` | ⚠️ warn | ✅ |
| `release build` | ✅ | ❌ blocked |
| `doctor run` | ✅ | ✅ |
| `docs update/deploy` | ✅ | ✅ |

## Essential Commands

## Global Flags

- `--json`: emit structured JSON payloads for commands that support machine-readable output.
- `--verbose` / `-v`: enable detailed output for commands that support verbose mode.

Examples:

```bash
sdd --json runtime status
sdd --json governance validate
sdd --verbose runtime status
```

### Project Setup

- providence setup run: Initializes workspace dependencies and local tooling.

### Testing and Validation

- providence test run: Runs the full test pipeline and shows project coverage summary by default.
- providence test ci-validate: Runs CI-oriented validations.
- providence lint run: Runs static quality checks.

Coverage options for providence test run:

```bash
# Default coverage output
providence test run

# Disable coverage
providence test run --no-coverage

# Customize report style
providence test run --cov-report term

# Enforce minimum percentage
providence test run --cov-fail-under 80
```

### Governance Management

- providence governance load: Shows loaded governance summary.
- providence governance validate: Validates structure, file access, and fingerprints.
- providence governance generate: Generates agent seeds from governance rules.
- providence governance compile: Compiles governance artifacts (mandates + guidelines → msgpack binaries).
- providence governance sign: Signs compiled artifacts or source specs (`--source`) with Ed25519.
- providence governance audit: Performs a security audit of the workspace and signatures.
- providence governance keygen: Generates Ed25519 key pairs for signing.

### Compliance Audit

- `providence audit`: Governance drift + telemetry summary (existing behavior).
- `providence audit view --since YYYY-MM-DD --event-type VIOLATION`: filtered event viewer for compliance events.
- `providence audit export --format=csv > compliance_report.csv`: deterministic CSV export to stdout, plus evidence manifest via `--manifest-file` (default `.providence/runtime/compliance-export.manifest.json`).
- `providence audit legacy-check [--phase-date YYYY-MM-DD]`: staged legacy policy enforcement (Q3 2026 warn, Q4 2026 block).
- `providence audit bootstrap-check`: validates AGENTS/CLAUDE bootstrap contract drift against `.providence` authority model.
- `providence audit compliance-pack --out-dir .providence/runtime/compliance-pack`: generates external-review evidence bundle.

### Maintenance and Tooling

- `sdd tools list`: Lists public active tools from `tools/registry.yaml` when present.
- `sdd tools list --all`: Includes public, internal, deprecated, and project registry entries.
- `sdd tools list --include-internal`: Includes internal entries in addition to public active tools.
- `sdd tools list --include-deprecated`: Includes deprecated entries and replacement guidance when available.
- `sdd tools list --include-projects`: Includes self-contained tool projects.
- `sdd tools list --json`: Emits machine-readable registry output.
- `sdd tools run <tool-id>`: Executes a runnable manifest entry with automatic environment isolation.
- `sdd tools run <category>/<script>.py`: Executes a legacy path relative to `tools/`; this remains supported during manifest migration.

If `tools/registry.yaml` is absent, `sdd tools list` falls back to recursive Python
script discovery under `tools/` for compatibility.

### Governance Query (Ask)

`providence ask` is the single governed entrypoint: it is the source of truth that
the prompt-submit hook and the `/sdd-ask` slash/skill adapters route through.
Adapters do not classify intent independently; they consume the CLI's
structured decision. Loads compiled governance context before any agent
response.

- `providence ask "<query>"` — minimal governance context (fingerprint + mandates). Use for quick queries and skill routing decisions.
- `providence ask "<query>" --full` — full governance context with telemetry. Use when confidence or drift information is needed.
- `providence ask "<query>" --intake-only` — cheap profile for automated callers (e.g. a prompt-submit hook): emits only `execution_gate`, `intake_index_mode`, and the structured intent fields below. Skips the compiled-governance load, signature verification, handbook lookup, and telemetry emission that the full profile performs.

Both `providence ask` and `providence ask --full` emit:

```
=== Providence Governance Context ===
query_hash      : <hash>
context_source  : compiled
fingerprint     : <hash>
mandates_loaded : <n>
trust_source    : canonical
degraded        : no

PROVIDENCE GOVERNANCE: drift=<status> | governance=<status> | profile=<profile>
```

Every profile (including `--intake-only`) also emits a structured intake
contract distinguishing what was decided from what was executed:

```
intent            : governance_query | implementation_request | analysis_request | planning_request
entrypoint        : hook | explicit_command
next_action       : acknowledge_context | create_execution_contract | answer_from_governance
delegation_executed : false
provider_bound    : false
```

`delegation_executed` and `provider_bound` are always `false` today: no
runtime code path in `providence ask` invokes an external provider (e.g.
Strategist) or any other analysis skill. `next_action:
create_execution_contract` (surfaced today as `next_valid_path:
implementation_handoff`) means the calling agent should proceed with an
authorized implementation path itself — it is not a signal that
implementation, delegation, or provider execution already happened.
Governance stays provider-agnostic: using an analysis skill such as
Strategist to refine an implementation plan is the user's independent
choice, not something `providence ask` selects or invokes automatically.

If `drift=detected` or `governance=partial`, run `providence governance compile` before retrying.

```bash
# Route a request through governed context
providence ask "diagnose failing tests"

# Full telemetry (confidence gate, drift check)
providence ask "implementar plano: .providence/skills/sdd-ask/skill.yaml" --full

# Cheap profile for automated hook callers
providence ask "diagnose failing tests" --intake-only
```

### Capability Layer (Skills)

Skills are V6-schema governed capabilities (`schema_version: 1.1.0`). Each skill has explicit `triggers`, `forbidden` actions, `fallback_to`, and `idempotent` flag.

- `providence skills list` — list all registered skills with category and risk score.
- `providence skills describe <name>` — return full skill metadata including V6 fields.
- `providence skills run <name>` — execute governed skill pipeline.
- `providence skills export` — export skill definitions to `json/openai/langchain/crewai/autogen`.
- `providence skills --full-bootstrap` — regenerate all `skill.yaml` files and `registry.json` from the canonical Python `_REGISTRY`. **Overwrites** any manual edits to `.providence/skills/` — V6 fields must be set in `_REGISTRY` (`packages/core/providence_runtime/src/providence_runtime/skills.py`) to survive bootstrap.
- `providence skills learning-candidates` — generate/list supervised `RuleCandidate` entries from `FailureLedger`.
- `providence skills learning-approve <candidate-id> --rationale ... [--ttl-days N]` — human approval path; activates rule in registry.
- `providence skills learning-reject <candidate-id> --rationale ...` — human rejection path; keeps candidate history without activation.
- `providence skills learning-rules` — list active supervised rules.
- `providence skills learning-impact <rule-id> --rework-delta X --false-block-rate Y --escalation-delta Z [--rollback-flag]` — record impact and optionally trigger rollback (negative learning).
- `providence skills learning-status [--window-days N]` — summarize candidate/rule/impact health in a recent time window.

Built-in skills (registry `schema_version: 1.1.0`):

| Skill | Category | Risk | Idempotent | Fallback |
|-------|----------|------|------------|---------|
| `sdd-ask` | orchestrator | controlled | no | — |
| `sdd-diagnose` | analysis | low | yes | — |
| `sdd-correct` | correction | medium | no | sdd-diagnose |
| `sdd-converge` | convergence | high | no | sdd-correct |
| `sdd-stabilize` | operations | medium | yes | sdd-diagnose |
| `sdd-review-architecture` | architecture | high | yes | sdd-diagnose |
| `sdd-validate-governance` | governance | medium | yes | — |
| `sdd-compress-context` | economy | low | yes | — |

JSON minimum contract for skills:

- `state`, `profile`, `skill`, `policy_result`, `exit_code`, `reason`, `governance_footer`.

Canonical envelope (contract-first, preferred for new consumers):

- `status`: `ok | error`
- `command`: canonical command id (e.g. `runtime status`, `skills run`)
- `ok`: boolean success flag
- `error`: `null` or `{code, message}`
- `data`: command payload (authoritative fields)

Skill output schema (`skill_output.schema.yaml`):

- `status`: `ok | error | degraded`
- `confidence.overall`: float `[0.0, 1.0]`
- `error.category`: taxonomy key (see `.providence/skills/contracts/skill_output.schema.yaml`)
- `next_skill`: id of recommended next skill, or `null`

Governance footer contract:

- `PROVIDENCE GOVERNANCE: drift=<status> | governance=<status> | profile=<profile>`

JSON automation examples:

```bash
sdd --json governance compile | jq '.data.summary'
sdd --json governance load --path runtime | jq '.data.summary'
sdd --json governance validate | jq '.ok,.data.preflight'
providence skills list
providence skills describe sdd-ask
sdd --json skills learning-status | jq '.data.status'
sdd --json skills learning-candidates | jq '.data.created_count,.data.candidates | length'
sdd --json skills run sdd-diagnose | jq '.data.artifacts.diagnosis_attestation'
sdd --json skills run sdd-converge | jq '.data.artifacts.freeze_mode_state'

```

Supervised learning workflow (safe default):

```bash
# 1) Observe candidates derived from recurring failures
sdd --json skills learning-candidates

# 2) Human decision
sdd --json skills learning-approve rc-abc123 --rationale "validated recurrence" --ttl-days 30
# or
sdd --json skills learning-reject rc-abc123 --rationale "insufficient evidence"

# 3) Measure impact
sdd --json skills learning-impact rr-def456 \
  --rework-delta -0.12 \
  --false-block-rate 0.04 \
  --escalation-delta 0.01

# 4) Detect degradation and rollback
sdd --json skills learning-impact rr-def456 \
  --rework-delta 0.22 \
  --false-block-rate 0.38 \
  --escalation-delta 0.19 \
  --rollback-flag
```

### Scaffold

Generate new skills and slash commands from V6-compliant canonical templates.

- `sdd scaffold skill <name>` — create a new skill under `.providence/skills/<name>/` with `skill.yaml` and `SKILL.md`.
- `sdd scaffold command <name>` — create a new slash command under `.providence/commands/<name>/` with `command.yaml`.

Options for `sdd scaffold skill`:

| Flag | Default | Description |
|------|---------|-------------|
| `--category` | `operations` | `analysis`, `architecture`, `convergence`, `correction`, `economy`, `governance`, `operations`, `orchestrator` |
| `--risk` | `low` | `low`, `medium`, `high`, `critical`, `controlled` |
| `--description` | auto | One-line skill description |
| `--when-to-use` | `when needed` | Primary trigger phrase |

Generated `skill.yaml` includes all V6 fields (`triggers`, `forbidden`, `fallback_to`, `idempotent`, `context_policy`) with `schema_version: 1.1.0`. Fill in `triggers` and `forbidden` before committing.

```bash
# Create a new read-only analysis skill
sdd scaffold skill my-skill --category analysis --risk low \
  --description "Analyze X for Y"

# Create the matching slash command
sdd scaffold command my-skill --routes-to my-skill
```

Templates live in `.providence/templates/` (deployed by wizard from `providence_integration`). To add a skill to the canonical registry so it survives `--full-bootstrap`, add a `SkillDefinition` entry to `packages/core/providence_runtime/src/providence_runtime/skills.py`.

### Wizard

- `providence install --wizard` — canonical entrypoint. Runs a single guided flow
  (language/hook-mode/agent-selection prompts, then generate-or-load-custom,
  compile, seeds, deploy to project root) — no user-facing phase choice.
  _(client primary; warns in master)_
- `providence wizard run` — legacy alias for the same command; deploys to project
  root by default.

| Flag | Effect |
|------|--------|
| `--output-dir <path>` | Change where the generated template lands (default: `generated/client/build/final-template/`) |
| `--only-template` | Stop after generating the final template bundle; do not deploy it into the project root |
| `--from-file <path>` | Supply a custom mandates/guidelines JSON instead of generating one (validated before use) |
| `--non-interactive` | Resolve preferences/agent selection without prompting (reuses an existing `wizard-config.json` or falls back to defaults) |

The wizard deploys `.providence/templates/` to the target project, enabling `sdd scaffold skill` in generated workspaces.

### Documentation Artifacts

- sdd docs update: Discovers all markdown in /docs, synthesizes `mandate.spec`, `guidelines.dsl`, and `discovery-index.json` under `generated/client/build/docs-meta/`.
- sdd docs deploy: Deploys MkDocs static site (requires mkdocs installed). Aliases: `sdd docs`, `sdd documentation`.

Options for sdd docs update:

```bash
# Dry run — shows what would be generated without writing files
sdd docs update --dry-run
```

Options for sdd docs deploy:

```bash
# Default — force rebuild and deploy
sdd docs deploy

# Skip force flag
sdd docs deploy --no-force
```

### Release

- providence release build: Builds release artifacts into `dist/`. _(master only — blocked in client)_

### Version

- providence version: Shows the installed Providence CLI version.

### Diagnostics

- providence doctor run: Executes protocol-based diagnostics using integration flow steps.

Runtime JSON example:

```bash
sdd --json runtime status | jq '.data.state,.data.ask_confidence'
```

Ask learning recommendation JSON example:

```bash
sdd --json ask "diagnose recurring correction blocks" \
  | jq '.data.learning_context,.data.learning_recommendations.signals,.data.learning_recommendations.next_actions'
```

Ask decision envelope JSON example:

```bash
sdd --json ask "fix governance drift in runtime" | jq '.data.ask_decision_envelope'
```

## Doctor Modes

The doctor command supports two execution modes:

- isolated (default): runs in a temporary isolated workspace.
- real: runs against the current repository workspace.

Examples:

```bash
# Default (isolated)
providence doctor run

# Real workspace diagnostics
providence doctor run --mode real

# Custom protocol file
providence doctor run --spec packages/features/providence_integration/src/providence_integration/protocol/integration_flow.yaml
```

## Notes on Diagnostic Semantics

- Diagnostic status is protocol-step based and returns a score.
- A run only exits successfully when all protocol steps pass.
- The protocol now guards against false-green runs where pytest reports only skipped tests.

## Command Help

Use help per command for authoritative flags:

```bash
sdd --help
providence doctor --help
providence governance validate --help
```

## Related Documentation

See the project README and CHANGELOG for additional context.
