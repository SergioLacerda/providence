# 🖥️ SDD Command Line Interface (providence-cli)

## 🎯 Overview

The `providence_cli` package is the primary interaction layer for the SDD v3.0 framework. It provides a unified command-line tool (`sdd`) to orchestrate the full project lifecycle, from environment setup to governance validation and CI/CD integration.

## 🛠️ Core Capabilities

1.  **Environment Management**: Automated setup of virtual environments and installation of SDD core packages.
2.  **Governance Orchestration**: Loading, validating, and generating artifacts from compiled governance.
3.  **Quality Control**: Integrated linting, testing, and system diagnostics (`doctor`).
4.  **Agent Integration**: Automatic generation of VS Code Agent seeds (`.vscode/agents/`) based on governance specs.
5.  **Extension Framework**: Pluggable architecture allowing for custom commands and integrations without modifying the core CLI.
6.  **Lazy Loading**: High-performance CLI architecture that only imports command modules on demand, ensuring `sdd --help` is always responsive even with missing dependencies.

## 🚀 Key Commands

| Command | Purpose |
| :--- | :--- |
| `providence setup run` | Initializes the local workspace and installs all dependencies. |
| `providence test run` | Executes the full test suite (unit, integration, e2e). |
| `providence governance validate` | Verifies the integrity and fingerprints of compiled governance. |
| `providence wizard run` | Starts the interactive project provisioning wizard. |
| `providence doctor run` | Performs deep diagnostics on the integration flow and environment. |
| `providence governance generate` | Exports governance as VS Code Agent seeds. |

## 📂 Architecture

The CLI follows a modular "lazy-loaded" design to prevent import errors during initial setup phases:

```
providence_cli/
├── commands/           # Individual command implementations
│   ├── governance.py   # Artifact management
│   ├── setup.py        # Workspace provisioning
│   └── ...
├── generators/         # Template and agent seed generation
├── utils/              # Shared CLI helpers (loaders, environment)
└── main.py             # LazyCommandGroup orchestrator
```

---
**Standard:** World Class Engineering - v3.0 (Interface Layer)
**Status:** Active / Production-Ready
