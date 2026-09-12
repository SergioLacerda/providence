# 🧙 SDD Project Wizard (providence-wizard)

## 🎯 Overview

The `providence_wizard` is the interactive orchestration engine of the SDD v3.0 framework. It guides developers and organizations through a structured, multi-phase process to bootstrap new projects that are "SDD-compliant" by design.

## 🛠️ Core Capabilities

1.  **Phased Provisioning**: Orchestrates a 3-phase flow for governance adoption:
    *   **Phase 1 (Discovery)**: Extracts rules from core specs and generates human-readable Markdown templates.
    *   **Phase 2 (Customization)**: Allows users to opt-in/opt-out of specific guidelines via status fields.
    *   **Phase 3 (Activation)**: Compiles the final governance into secure, fingerprinted binary artifacts.
2.  **Seedling Generation**: Automatically creates the project "DNA", including:
    *   `.vscode/agents/`: AI agent context and seeds.
    *   `.providence/`: Governance/runtime structures for autonomous agents.
    *   `.github/workflows/`: SDD-aware CI/CD pipelines.
3.  **Multi-Language Support**: Tailors the generated project structure for Python, TypeScript, and Java.
4.  **Governance Enforcement**: Seals the project with SHA-256 fingerprints (SALT), ensuring that any local modifications to mandates are detectable.

## 🚀 Execution Flow (v3.0)

| Phase | Action | Output |
| :--- | :--- | :--- |
| **1. Template** | Parse `.spec` files | `phase-1-choices/*.md` |
| **2. Review** | User edits status fields | `phase-2-input/*.md` |
| **3. Compile** | Build final artifacts | `.providence/runtime/` & `.providence/source/` |

## 📂 Architecture

```
providence_wizard/
├── orchestration/       # Phase-specific logic (1 through 7)
│   ├── phase_wizard_v3.py # Main v3 orchestrator
│   └── intelligent_seedlings_generator.py # DNA Generator
├── templates/           # Base project seedlings (.providence, .github, etc)
├── validator.py         # Compliance checking logic
└── loader.py            # Governance loading for runtime
```

---
**Standard:** World Class Engineering - v3.0 (Provisioning Layer)
**Status:** Active / Production-Ready
