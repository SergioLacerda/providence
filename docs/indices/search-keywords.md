# Search Keywords

Semantic keyword index for discovering documentation by topic.

---

## 🎯 Framework Concepts

Core SDD framework terminology and abstractions.

- Spec-Driven Development
- SDD governance
- governance activation
- handshake protocol
- compliance audit log
- workspace profile
- compiled artifacts
- authority hierarchy
- immutable kernel
- source of truth
- CORE (immutable governance kernel)
- PATH routing (A, B, C, D, E, F)

---

## 🏛️ Constitutional Foundation

Mandates, policies, and rules that cannot be overridden.

### Mandates

- M001: Clean Architecture
- M002: TDD (Test-Driven Development)
- M003: Context Awareness
- M005: Token Economy
- M007: Telemetry
- mandate enforcement

### Policies

- P001: Project Boundary
- P002: Honest Critique
- P003: Mandatory Human Review
- P004: Pre-Delivery Quality Gate
- immutable policy
- policy violation
- human review requirement
- autonomous commit prohibition

### Rules

- code style rules
- testing rules (F.I.R.S.T)
- dependency resolution
- module structure
- formatting standards
- logging standards

---

## 🏗️ Architecture Decisions

Strategic choices and rationale.

- ADR (Architecture Decision Record)
- clean architecture
- hexagonal architecture (ports & adapters)
- 8-layer architecture
- domain layer
- application layer
- infrastructure layer
- interface layer
- async-first design
- no blocking operations
- vector index (black box)
- campaign scoping
- multi-level scoping
- thread isolation

---

## 🧭 Context-Aware Patterns

How agents load, manage, and reason about context.

### Context Loading

- context budget
- context loading strategy
- context poisoning
- context verification
- context compression
- semantic pruning
- functional skeletonizing
- layer masking
- context-aware agent pattern
- intelligence providers (TFIDF, AST, HTTP, Local)

### Task Classification

- task classification
- PATH A (bug fix)
- PATH B (simple feature)
- PATH C (complex feature)
- PATH D (parallel work)
- PATH E (hotfix)
- PATH F (refactoring)
- PATH routing
- impact assessment
- blast radius
- confidence threshold
- go/no-go decision

### Anti-Patterns

- cognitive overload
- scope creep (scope drift)
- premature execution
- symptom fixing (symptom-driven fixing)
- resolution bypass
- context ignorance
- context overloading
- rule bypass
- state desync
- heuristic execution mode

---

## 📋 Implementation Standards

Code quality, testing, and development practices.

### Development

- definition of done (DoD)
- merge validation
- quality gate
- feature checklist
- layer implementation
- UseCase organization
- Runtime consolidation
- factory pattern
- storage architecture
- RAG pipeline

### Testing

- Golden Rule (never alter production code for tests)
- test pyramid (unit/integration/E2E)
- layer-specific testing strategy
- Fake Adapter pattern
- Fixture Factory
- parametrized tests
- contract test
- mocking rules
- test coverage requirements
- regression test

### Code Quality

- code comment philosophy (WHY not WHAT)
- naming conventions
- type hints
- error handling
- import organization
- documentation requirements
- checkpoint format

---

## 🔄 Development Workflow

Processes, tools, and protocols for effective development.

### Runtime & Execution

- agent entrypoint
- agent runtime protocol
- 7-phase execution flow
- Phase 0 (context check)
- Phase 1 (load rules)
- Phase 2 (detect conflicts)
- Phase 3 (choose path)
- Phase 4 (load task context)
- Phase 5 (implement)
- Phase 6 (validate)
- Phase 7 (checkpoint)
- pre-commit hook
- CI/CD validation

### Governance Lifecycle

- `providence init` (workspace initialization)
- `providence governance compile`
- `providence governance validate`
- `providence governance generate`
- `providence governance score`
- `providence governance adherence`
- `providence runtime status` (AHP/GAP state)
- `providence lint spec`
- `providence ask` / `providence ask --full` (governance query)
- `providence test run`
- `providence doctor` (diagnostics)
- `providence setup` (venv/dependencies)
- `providence release` (version management)

### Collaboration

- commit message protocol
- ADR (Architecture Decision Record) process
- RFC (Request for Comments)
- code review process
- honest critique
- debt-aware reporting
- Known Limitations section
- pull request template

---

## 🆘 Emergency Procedures

Critical failure modes and recovery.

- drift detection
- governance drift
- compliance event
- pre-commit hook failure
- CI/CD gate failure
- corruption recovery
- canonical corruption
- metrics corruption
- state desync recovery
- context poisoning antidote
- policy violation escalation
- human review gate
- breach mode (token budget exceeded)

---

## 📚 Reference & Glossary

Definitions and cross-references.

### Telemetry & Monitoring

- OpenTelemetry (OTEL)
- runtime events
- governance events
- compliance events
- telemetry sink
- trace context
- metric (Golden Signals)
- span naming convention
- on-call model
- incident response
- blameless post-mortem

### Observability Standards

- logging levels
- PII anonymization
- retention policy
- tracing (distributed tracing)
- metrics collection
- alert routing
- escalation policy
- runbook

### Performance & Budgets

- token economy
- budget utilization
- budget_utilization_pct
- compression ratio
- compression_ratio
- retry cap
- retry ceiling
- reflection ceiling
- circuit breaker
- cognitive entropy
- execution budget
- GREEN YELLOW RED BREACH zones
- tokens_input
- tokens_output
- context_bytes_loaded
- path budget (PATH A: 40KB, B: 45KB, C: 85KB, D: 35KB/thread)
- SLO (Service Level Objective)
- latency budget
- throughput target
- error rate threshold

### Security & Compliance

- threat model
- attack surface
- attack vector
- OWASP Top 10
- authentication (JWT, OAuth2)
- authorization (RBAC)
- campaign isolation
- session management
- HTTPS/TLS
- AES-256-GCM encryption
- GDPR compliance
- CCPA compliance
- PCI compliance
- audit checklist
- incident notification
- evidence preservation

### Configuration & Storage

- workspace profile (INI schema)
- `.providence/` (governance workspace)
- `.providence/context-aware/` (project runtime state)
- `.providence-cache.md` (task context cache)
- `compliance-events.jsonl` (audit log)
- `generated/` (compiled artifacts)
- msgpack encoding
- DSL (Domain-Specific Language)
- specification file (`.spec`, `.dsl`)

---

**Last Updated:** May 2026
**Categories:** 8 (Framework, Constitutional, Architecture, Context, Standards, Workflow, Emergency, Reference)
**Total Keywords:** 200+
