# Language Adapter Guidelines — Schema Reference

**Status:** Active
**Relates to:** M001 (Clean Architecture), M016 (Guardrail Non-Regression)
**Location in pipeline:** Wizard Phase 4 (filter by language tags)

---

## Overview

Language adapter guidelines translate universal, agnostic mandates into
concrete enforcement for a specific technology stack. They live in
`.providence/source/guidelines.dsl` and are filtered by the wizard at client
onboarding time based on the declared target language.

**Separation principle:**

- Canonical mandates (`mandate.dsl`) — zero language content, always applied

- Language adapter guidelines (`guidelines.dsl`) — tagged, filtered per client

---

## DSL Format

```
guideline G<NN> {
  type: HARD | SOFT
  title: "<mandate name> — <language>"
  description: "<language-specific enforcement intent>"
  category: architecture | testing | security | performance | git | documentation
  mandate_ref: <mandate ID, e.g. M001>
  tags: ["<primary-language>", "<tool-1>", "<tool-2>"]
  enforcement: {
    gate: pre-commit | ci | pr
    severity: block | warn
    tools: ["<command-1>", "<command-2>"]
  }
  violations: ["<violation_snake_case>", "..."]
  exception_policy: {
    requires: ["diagnosis", "evidence", "temporary_marker", "follow_up_task"]
    ttl: sprint | quarter | permanent
  }
  maturity_level: 0 | 1 | 2 | 3 | 4
  examples: ["<must-block example>", "<must-pass example>"]
}
```

---

## Mandatory Fields

Every language adapter guideline MUST declare all of these fields:

| Field | Purpose |
|-------|---------|
| `type`|`HARD`blocks CI;`SOFT` is advisory |
| `title`| Human-readable, format:`<mandate> — <language>` |
| `description` | One sentence: what is being enforced and why |
| `category` | Domain category matching the canonical mandate |
| `mandate_ref` | ID of the canonical mandate this adapts |
| `tags` | Language and tool identifiers (used by Phase 4 filter) |
| `enforcement.gate`| When it runs:`pre-commit`, `ci`, or `pr` |
| `enforcement.severity`|`block`(hard gate) or`warn` (advisory) |
| `enforcement.tools` | Concrete commands with required flags |
| `violations` | Named violation patterns this catches |
| `exception_policy` | Waiver requirements — must inherit M016 contract |
| `maturity_level` | Current level (0–4, see below) |
| `examples` | At least one must-block and one must-pass |

---

## Tags Convention

Tags must include the primary language identifier so Phase 4 can filter correctly.
Language identifiers used by the wizard:

| Language | Primary tag | Tool tags (examples) |
|----------|-------------|----------------------|
| Python | `python`|`ruff`, `mypy`, `pytest`, `import-linter` |
| Go | `go`|`golangci-lint`, `go-vet` |
| Java | `java`|`archunit`, `checkstyle`, `pmd`, `spotbugs`, `maven`, `gradle` |
| JavaScript/TypeScript | `js`|`eslint`, `tsc`, `typescript`, `jest`, `vitest`, `npm` |

Guidelines without `tags` are universal and reach every client regardless
of declared language. This is the expected shape for contextual language
guidelines that depend on `M011` but do not target a programming language,
such as:

- `G021` — interaction/chat/UI preference surfaces

- `G022` — workspace-local notes and analysis surfaces

---

## Maturity Levels

```
0 — documented   : principle written, no automation
1 — scripted     : tools run locally on demand
2 — automated    : tools run in CI on every push
3 — enforced     : violations block merge (HARD gate active)
4 — measured     : violation rate tracked in telemetry
```

New guidelines start at `0`. The `maturity_level` field declares the
**current** level, not the target. Increment only when evidence exists.

---

## Exception Policy

Every adapter guideline must declare how violations can be waived.
The minimum required fields mirror M016:

```
exception_policy: {
  requires: ["diagnosis", "evidence", "temporary_marker", "follow_up_task"]
  ttl: sprint | quarter | permanent
}
```

- `diagnosis`: written explanation of why the rule cannot be followed

- `evidence`: code comment or PR link documenting the exception

- `temporary_marker`: `# noqa`, `// nolint`, `# type: ignore` with justification

- `follow_up_task`: linked task to remove the exception

- `ttl`: how long the exception is valid before mandatory review

---

## Examples

### By topic (Dependency Direction — M001)

- [Python — Dependency Direction](examples/python-dependency-direction.md) (G01)

- [Go — Dependency Direction](examples/go-dependency-direction.md) (G02)

- [Java — Dependency Direction](examples/java-dependency-direction.md) (G03)

- [Node.js / TypeScript — Dependency Direction](examples/nodejs-typescript-dependency-direction.md) (G04)

### Full language reference (all topics: code style, anti-patterns, performance, structure)

- [Python Engineering Guidelines](../../guidelines/languages/python.md) — G01, G05, G09, G13, G17

- [Go Engineering Guidelines](../../guidelines/languages/go.md) — G02, G06, G10, G14, G18

- [Java Engineering Guidelines](../../guidelines/languages/java.md) — G03, G07, G11, G15, G19

- [TypeScript Engineering Guidelines](../../guidelines/languages/typescript.md) — G04, G08, G12, G16, G20

See complete DSL: `.providence/source/guidelines.dsl` — G01–G022 covering language adapters plus contextual language-preference guidance.
