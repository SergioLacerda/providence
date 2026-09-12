# 🧠 SDD Core Orchestrator

> **System Role:** The central backbone and lifecycle orchestrator of the SDD Framework.

## 🎯 Overview

The `providence-core` package is the "Brain" of the architecture. It does not perform low-level parsing or integration itself; instead, it orchestrates the specialized packages (`providence-integration`, `sdd-compiler`) to ensure a seamless end-to-end governance lifecycle.

## 🛠️ Core Capabilities

1.  **Governance Orchestration (Phase 3)**:
    *   Coordinates the transition from **Phase 1 (Pipeline)** to **Phase 2 (Compiler)**.
    *   Ensures that fingerprints generated during build are correctly salt-verified during compilation.
2.  **Deployment Management (Phase 4)**:
    *   Handles the distribution of binary artifacts to the `runtime/compiled/` directory.
    *   Manages **Deployment Manifests** and version tracking for governance updates.
    *   Implements safe backup procedures during artifact promotion.
3.  **Lifecycle Authority**: Defines the state machine for project-framework alignment, providing the logic for "bootstrap" scenarios in CI/CD and Docker environments.
4.  **Integrity Verification**: Validates the complete pipeline (Core → Integration → Compiler → Deployment) through cross-artifact checks.

## 🚀 Pipeline Integration

`providence-core` acts as the command center for the following workflow:

1.  **Trigger**: CLI or CI/CD invokes `GovernanceOrchestrator`.
2.  **Execution**: Invokes `PipelineBuilder` (Integration) and `GovernanceCompiler` (Compiler).
3.  **Promotion**: `DeploymentManager` pushes artifacts to the local runtime.
4.  **Ready**: Signals to the `providence-wizard` and AI Agents that the environment is fully provisioned.

## 📂 Architecture

```
providence_core/
├── governance_orchestrator.py # PHASE 3: End-to-end build coordination
├── deployment_manager.py     # PHASE 4: Artifact promotion and versioning
└── tools/                    # Core utilities and diagnostic helpers
```

---
**Standard:** World Class Engineering - v3.0
**Status:** Mandatory Core Component (Backbone)
