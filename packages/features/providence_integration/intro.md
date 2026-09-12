# 🔗 SDD Integration Engine

> **System Role:** Core automation and provisioning engine for the SDD Framework.

## 🎯 Overview

The `providence-integration` package is the operational arm of the SDD (Specification-Driven Development) architecture. It transforms theoretical governance (Specs) into actionable project structures and "intelligent seedlings" for AI agents.

## 🛠️ Core Capabilities

1.  **Automation Engine**: A step-based execution system that orchestrates project setup and framework alignment.
2.  **Specialized Runners**:
    *   `Filesystem`: Secure directory and file structure generation.
    *   `Git`: Automated repository preparation and governance anchoring.
    *   `Command`: Hardened execution of environmental setup scripts.
    *   `Config`: Dynamic management of `.spec.config` and environment variables.
3.  **Seedling Repository**: Source of truth for optimized agent entrypoints (`.providence/`, `.cursor/`, `.github/`).
4.  **Governance Pipeline**: Implements the `PipelineBuilder` used to compile DSLs into high-performance binary artifacts.

## 🚀 Integration in SDD Wizard v3.0

This package is a mandatory dependency for the `providence-wizard`. Its lifecycle integration includes:

*   **Phase 3 (Compiler)**: Powering the build pipeline to generate `governance-core.json`.
*   **Phase 4-6 (Provisioning)**: Injecting intelligent seedlings and setting up the `.providence/` runtime environment.
*   **Health Check (Doctor)**: Providing automated diagnostics to ensure project-framework alignment.

## 📂 Architecture

```
providence_integration/
├── engine/          # Orchestration and Step Execution
├── runners/         # Specialized execution units (Git, FS, Command)
├── templates/       # "Intelligent Seedlings" for AI Agents
└── builders/        # Governance compilation pipelines
```

---
**Standard:** World Class Engineering - v3.0
**Status:** Active Core Component
