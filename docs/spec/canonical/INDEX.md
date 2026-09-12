# 🗺️ Canonical Specification Map (LLM Semantic Entrypoint)

> **Context:** This is the root of the SDD Canonical Specification. Use this map to navigate deep technical and governance rules.
> **Navigation:** For AI agents, see the [Semantic Map](./SEMANTIC_MAP.md) for deep knowledge graph navigation.

## 🏗️ Core (Immutable Governance Kernel)

*Non-negotiable rules and mandates that govern all agent behavior.*

- **Mandates**: [core/mandates/INDEX.md](./core/mandates/INDEX.md) — Primary execution mandates.
- **Guidelines**: [core/policies/INDEX.md](./core/policies/INDEX.md) — Customization and governance policy rules.
- **Policies**: [core/policies/INDEX.md](./core/policies/INDEX.md) — Enforcement levels (Strict/Permissive).
- **Invariants**: [core/INDEX.md](./core/INDEX.md) — Architectural lock-in rules.
- **Governance Sources Registry**: [governance-sources.yaml](./governance-sources.yaml) — Maps canonical source documents to generated runtime governance outputs.

## 🧩 Specifications (Technical Guardrails)

*Technical standards for implementing features and maintaining code quality.*

- **Definition of Done**: [specifications/definition_of_done.md](./specifications/definition_of_done.md) — 45+ criteria for task completion.
- **Security Model**: [specifications/security-model.md](./specifications/security-model.md) — Rules for subprocesses, shell execution, and path validation.
- **Testing Standard**: [specifications/testing.md](./specifications/testing.md) — TDD requirements and layer coverage.
- **Architecture**: [specifications/architecture.md](./specifications/architecture.md) — Ports & Adapters (Hexagonal) alignment.

## 🚀 Key Features

*Specific framework capabilities and their governing rules.*

- **Clean Architecture**: [features/CLEAN_ARCHITECTURE.md](./features/CLEAN_ARCHITECTURE.md)
- **TDD Workflow**: [features/TDD.md](./features/TDD.md)
- **Customization**: [features/CUSTOMIZATION_GOVERNANCE.md](./features/CUSTOMIZATION_GOVERNANCE.md)

## 🌐 Language Adapter Guidelines

*Language-specific enforcement — filtered per client by wizard Phase 4. Canonical layer stays agnostic.*

- **Schema & Contract**: [guides/architecture/language-adapter-guidelines.md](../../../docs/guides/architecture/language-adapter-guidelines.md) — How to write adapter guidelines (mandatory fields, maturity levels, exception policy)
- **Python example**: [guides/architecture/examples/python-dependency-direction.md](../../../docs/guides/architecture/examples/python-dependency-direction.md)
- **Go example**: [guides/architecture/examples/go-dependency-direction.md](../../../docs/guides/architecture/examples/go-dependency-direction.md)
- **Java example**: [guides/architecture/examples/java-dependency-direction.md](../../../docs/guides/architecture/examples/java-dependency-direction.md)
- **TypeScript example**: [guides/architecture/examples/nodejs-typescript-dependency-direction.md](../../../docs/guides/architecture/examples/nodejs-typescript-dependency-direction.md)
- **DSL source (G01–G022)**: [.providence/source/guidelines.dsl](../../../../.providence/source/guidelines.dsl) — Language adapters plus contextual language-preference guidance

## 📐 Language Engineering Guidelines (M018)

*Full per-language reference. Wizard selects language; compiled output contains relevant guidelines.*

- **Core principles**: [guides/guidelines/core-engineering-principles.md](../../../docs/guidelines/core-engineering-principles.md) — M018 human reference
- **Python**: [guides/guidelines/languages/python.md](../../../docs/guidelines/languages/python.md)
- **Go**: [guides/guidelines/languages/go.md](../../../docs/guidelines/languages/go.md)
- **Java**: [guides/guidelines/languages/java.md](../../../docs/guidelines/languages/java.md)
- **TypeScript**: [guides/guidelines/languages/typescript.md](../../../docs/guidelines/languages/typescript.md)

## 🔌 Plugin Governance (M019)

*How external plugins and skills declare identity, negotiate capabilities, and adhere to host governance.*

- **Overview**: [guides/plugins/plugin-governance-overview.md](../../../docs/guides/plugins/plugin-governance-overview.md) — Federation model, M017 vs M019, integration modes
- **Registration Protocol**: [guides/plugins/registration-protocol.md](../../../docs/guides/plugins/registration-protocol.md) — Agent-mediated handshake flow
- **Entry Reference**: [guides/plugins/plugin-entry-reference.md](../../../docs/guides/plugins/plugin-entry-reference.md) — All registry entry fields
- **M019 Mandate**: [core/mandates/M019_GOVERNANCE_FEDERATION.md](./core/mandates/M019_GOVERNANCE_FEDERATION.md)
- **Live registry**: [.providence/plugins/registry.yaml](../../../../.providence/plugins/registry.yaml)

---
**Note for Agents:** All mandates are strictly enforced via SHA-256 fingerprints compiled into the `.providence/` control plane. Any modification to `core/meta/` requires running `providence governance validate` to refresh the session signature.
