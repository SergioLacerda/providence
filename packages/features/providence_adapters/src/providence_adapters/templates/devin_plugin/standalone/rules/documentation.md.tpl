# Documentation

Ruleset version: `{{ standalone_ruleset_version }}`
Last verified: `{{ last_verified }}`

Comments and documentation should explain WHY, not WHAT. Well-named code already says what it does. Concise comments also conserve context window â€” see `token-economy.md`.

- Document hidden constraints, bug references, and upstream limitations â€” the things a reader cannot infer from the code itself.
- Skip comments that restate the line below them (`// increment counter` above `i++`).
- Public functions get a docstring with intent and one usage example.
- Reference issue numbers or commit references when a line exists because of a specific bug â€” a future reader should be able to find the "why" without reading the version-control log.
