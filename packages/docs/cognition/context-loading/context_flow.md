---
governance_source:
  id: HBK-CONTEXT-LOADING
  type: handbook
  kind: decision_model
  status: active
  title: Context Flow
  refs: [M003, M005]
  task_types: [planning, implementation, diagnosis]
  operation_phases: [context_loading, planning]
  load_policy:
    mode: selective
    max_tokens: 700
    require_relevance_reason: true
  summary: How agents route, prune, and pack relevant context before execution.
---

# 🧠 Context Flow — Token Optimization

```mermaid
flowchart TD

    %% Sources
    CANON[📚 CANONICAL\nRules / ADRs / Specs]
    REAL[🔍 REALITY\nCurrent state / issues]
    DEV[🟢 DEVELOPMENT\nActive work]
    AICTX[🧠 .providence/context-aware\nSummaries / tasks]
    RUNTIME[⚡ .providence/runtime\nIndexes / keywords]
    RUNBOOKS[📖 RUNBOOKS\nOperational procedures]

    %% Query
    QUERY[🎯 Task Query\n"What am I doing?"]
    QUERY --> ROUTER

    %% Router
    ROUTER[🧭 Context Router\nSelect relevant docs only]

    CANON --> ROUTER
    REAL --> ROUTER
    DEV --> ROUTER
    AICTX --> ROUTER
    RUNTIME --> ROUTER
    RUNBOOKS --> ROUTER

    %% Optimization
    ROUTER --> PRUNE[✂️ Pruning Engine\nRemove irrelevant content]
    PRUNE --> PACK[📦 Context Packing\nOptimize tokens]

    %% Agent
    PACK --> AGENT[🤖 Agent Input\nOptimized Context (~40–85KB)]

    %% Execution
    AGENT --> OUTPUT[💡 Execution / Code / Decisions]

    %% Feedback
    OUTPUT --> AICTX
    OUTPUT --> REAL

    %% CI feedback
    OUTPUT --> CI[⚖️ CI/CD Validation]
    CI --> CANON
```

## Runbook Consultation

Use `docs/runbooks/README.md` as a selective index when a task involves
operational failure, diagnosis, hotfix, repeated failure, release recovery,
generated-runtime drift, or context-budget breach.

The context router must load at most one matching runbook leaf unless the task
explicitly requires cross-runbook comparison. Record why the selected runbook is
relevant before loading it. If no runbook matches an active incident, use
`docs/incidents/PLAYBOOKS.md` as the fallback operational procedure.
