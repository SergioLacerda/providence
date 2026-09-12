# Architecture

Ruleset version: `{{ standalone_ruleset_version }}`
Last verified: `{{ last_verified }}`

Function/file size, naming, typing, and dependency-direction rules that apply regardless of language. Language-specific detail lives in `go.md`.

## Function and File Size

- Functions: 4â€“20 lines. One thing, done well. Split when longer.
- Files: under 500 lines. Split by responsibility when exceeded.
- One responsibility per module. When a file is hard to name, it does too much.

## Naming

- Names must be specific and unique. Target: no more than a handful of matches when you search the codebase for the name.
- Avoid `data`, `handler`, `Manager`, `Helper`, `Utils`, `Common` â€” names that could mean anything mean nothing.
- Names reveal intention. A reader should be able to guess what a function does from its name alone.

## Types

- Types must be explicit. No `any`, no untyped dict/map, no untyped function signatures.
- Typed code is unambiguous for both humans and anyone reading it later.
- Validate external input at system boundaries â€” never trust raw input from outside the process.

## Duplication

- No code duplication. Extract shared logic into named functions or modules.
- Three similar lines is a pattern. Four is a function.
- Duplication in logic should be eliminated; duplication in configuration is sometimes correct.

## Control Flow

- Early returns over nested ifs. Prefer no more than 2 levels of indentation.
- Guard clauses at the top. Happy path at the bottom.
- Error messages must include the offending value and the expected shape.

## Error Handling

- Every error path must produce a message that includes: what failed, the input that caused it, and what the caller should do next.
- Never swallow errors silently. Log or propagate â€” never ignore.
- Distinguish between recoverable errors (retry, fallback) and fatal errors (crash early with diagnostic). Do not mix the two.

## Security

- Validate and sanitize all external input at system boundaries.
- Never embed secrets (API keys, passwords, tokens) in source code â€” use environment variables or a secrets manager.
- Prefer allowlists over denylists for input validation.
- Log security-relevant events (auth failures, permission denials) without logging sensitive data (passwords, tokens, PII).
- Use parameterized queries â€” never string-concatenate user input into queries.

## Dependencies

- Inject dependencies via constructor or parameter â€” see `go.md` for dependency version hygiene.
- Never via global state, module-level singletons, or import-time mutation.
- Wrap third-party libraries behind a thin interface you own, so a library swap touches one place.
