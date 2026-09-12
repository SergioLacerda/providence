# Architecture Diagrams

Providence architecture using the [C4 model](https://c4model.com/). Three levels of detail:

| Level | File | Audience |
|---|---|---|
| L1 — Context | [c4-context.md](c4-context.md) | Anyone — what the system does and who uses it |
| L2 — Containers | [c4-containers.md](c4-containers.md) | Developers — the major packages and their relationships |
| L3 — Components (providence_runtime) | [c4-components-runtime.md](c4-components-runtime.md) | Contributors — internal structure of the execution engine |
| L3 — Components (providence_cli) | [c4-components-cli.md](c4-components-cli.md) | Contributors — command dispatch and CLI envelope contracts |

All diagrams use [Mermaid](https://mermaid.js.org/) and render inline in the documentation site.

See [c4-and-contracts-scoping-plan.md](c4-and-contracts-scoping-plan.md) for the scoping decision behind future L3 diagrams and per-component API contracts.
