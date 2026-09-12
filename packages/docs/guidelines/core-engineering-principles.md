# Core Engineering Principles (M018)

**Mandate:** M018 — Code Quality Baseline
**Applies to:** All projects, all languages
**Filtered by wizard:** No — these rules are always active

---

## Function and File Size

- Functions: 4–20 lines. One thing, done well. Split when longer.
- Files: under 500 lines. Split by responsibility when exceeded.
- One responsibility per module (SRP). When a file is hard to name, it does too much.

## Naming

- Names must be specific and unique. Target: ≤ 5 grep hits in the codebase.
- Avoid: `data`, `handler`, `Manager`, `Helper`, `Utils`, `Common`.
- Names reveal intention. Grep-friendly names reduce agent context cost.

## Types

- Types must be explicit. No `any`, no untyped `Dict`, no untyped function signatures.
- Typed code is unambiguous for both humans and AI agents.
- Validate external input at system boundaries — never trust raw JSON.

## Duplication

- No code duplication. Extract shared logic into named functions or modules.
- Three similar lines is a pattern. Four is a function.
- DRY applies to logic, not structure — duplication in config is sometimes correct.

## Control Flow

- Early returns over nested ifs. Maximum 2 levels of indentation.
- Guard clauses at the top. Happy path at the bottom.
- Exception messages must include the offending value and expected shape.

## Dependencies

- Inject dependencies via constructor or parameter.
- Never via global state, module-level singletons, or import-time mutation.
- Wrap third-party libraries behind a thin interface owned by the project.

## Comments

- Comments document WHY and provenance: hidden constraints, bug references, upstream limitations.
- Skip `// increment counter` above `i++`. The code explains WHAT.
- Public functions: docstring with intent and one usage example.
- Reference issue numbers or commit SHAs when a line exists because of a specific bug.

## Clean Code for AI Agents

These principles become technical obligations when AI agents work on the codebase:

- **Small functions** = one tool call, full attention, no pagination.
- **Unique names** = ≤ 5 grep hits, agent navigates directly to the right code.
- **Explicit types** = signature answers questions without reading the body.
- **Comments with provenance** = agent knows WHY without reading git log.
- **Tests that run headlessly** = agent writes code, runs tests, adjusts, repeats.

---

## Related

- Language-specific enforcement: [Python](languages/python.md) · [Go](languages/go.md) · [Java](languages/java.md) · [TypeScript](languages/typescript.md)
- DSL guidelines filtered by language: `/.providence/source/guidelines.dsl`
- Mandate source: `/.providence/source/mandates/mandates.md` — M018
