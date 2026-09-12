# Canonical mandate specification (DSL block format).
# Parsed by providence_wizard.orchestration.wizard.spec_parser.MandateSpecParser
# Authored from docs/spec/canonical/** and generated/master/compiled/governance-core.json.
# This file ships as providence_core package data and is the default bootstrap source
# for `sdd install --wizard` (adoption_level=FULL loads every mandate below).

mandate M001 {
  type: "SELECTABLE MANDATE"
  title: "Clean Architecture"
  description: "Ensure maintainability and testability by separating concerns into distinct, independent layers using the 8-layer Clean Architecture pattern: Domain, Use Cases, Ports, Adapters, Infrastructure, External Services, UI/CLI, Composition Root."
  category: "architecture"
  rationale: "Enforcing layer boundaries keeps business logic independent of frameworks and infrastructure, enabling long-term maintainability and safe refactors."
}

mandate M002 {
  type: "SELECTABLE MANDATE"
  title: "Test-Driven Development (TDD)"
  description: "Ensure 100% functional coverage and design clarity by writing tests before implementation code, following the Red-Green-Refactor cycle."
  category: "quality"
  rationale: "Writing the failing test first clarifies intent and design before implementation exists, preventing untested code paths from reaching production."
}

mandate M003 {
  type: "HARD MANDATE"
  title: "Context Awareness & Task Caching"
  description: "Ensure absolute continuity of state and logic across parallel agents, long-running tasks, and multi-repository environments by maintaining a persistent, project-isolated Context Cache."
  category: "cognition"
  rationale: "Prevents agents from breaking each other's assumptions during parallel work, prevents goal drift as the token window fills with implementation detail, and prevents rule bleed across multiple open repositories."
}

mandate M005 {
  type: "HARD MANDATE"
  title: "Token Economy Enforcement"
  description: "Ensure every agent respects token budget zones and circuit-breaker thresholds to prevent context overflow, degraded output, and undetected budget breaches."
  category: "economy"
  rationale: "Without enforced budget zones, agents silently overflow the context window, producing incomplete or hallucinated responses. Zone-based enforcement gives a graduated response: compression at YELLOW, explicit warning at RED, hard block at BREACH."
}

mandate M006 {
  type: "HARD MANDATE"
  title: "RFC Process for Breaking Changes"
  description: "Breaking changes to the SDD framework (CLI commands, governance schema, artifact formats, or runtime contracts) must go through a formal Request for Comments process before shipping."
  category: "governance"
  rationale: "Unilateral breaking changes erode trust between the framework and its adopters. The RFC process ensures backward-compatibility concerns are surfaced early and that impacted users have a migration path."
}

mandate M007 {
  type: "HARD MANDATE"
  title: "Telemetry Enforcement"
  description: "Ensure 100% traceability of agentic decisions and governance compliance via structured telemetry and OpenTelemetry integration."
  category: "observability"
  rationale: "Unrecorded governance decisions are a security risk. Telemetry provides the black box required to debug agent failures, audit compliance breaches, and optimize token economy efficiency across the ecosystem."
}

mandate M008 {
  type: "HARD MANDATE"
  title: "Audit Integrity"
  description: "Preserve and protect the integrity of the audit trail (.providence/audit-trail/compliance-events.jsonl) to ensure forensic capability, regulatory compliance, and accountability for all governance-aware operations."
  category: "security"
  rationale: "If governance fails, replaying and understanding what happened requires an immutable log. Regulators require immutable audit trails, and agents must not be able to hide violations after the fact."
}

mandate M009 {
  type: "HARD MANDATE"
  title: "OpenTelemetry Compliance"
  description: "Maintain distributed trace continuity across the agentic ecosystem by enforcing valid OpenTelemetry (OTEL) context propagation on all governance-aware operations."
  category: "observability"
  rationale: "Multi-agent systems need to correlate work across agents and services, show causality across system boundaries for audits, and trace through the full decision chain when debugging."
}

mandate M010 {
  type: "HARD MANDATE"
  title: "Delivery Hygiene Enforcement"
  description: "Guarantee that every implementation is delivered with updated tests and strict quality hygiene, including mandatory auto-fix and revalidation before handoff."
  category: "quality"
  rationale: "Running a linter alone verifies but does not remediate. Strict hygiene requires auto-fix first, then full revalidation, to prevent handing off avoidable style and lint debt to human reviewers."
}

mandate M011 {
  type: "HARD MANDATE"
  title: "English Language Standard"
  description: "Enforce a single language standard for engineering artifacts to prevent ambiguity, mixed-language drift, and communication inconsistency across humans and agents."
  category: "communication"
  rationale: "Mixed-language technical artifacts are ambiguous to review, hard to search, and drift out of sync when only one language version gets updated. A single canonical language keeps engineering artifacts unambiguous for every contributor and agent."
}

mandate M015 {
  type: "HARD MANDATE"
  title: "Bidirectional Agent Handshake"
  description: "Ensure every agentic interaction is governed by a formal trust boundary via a bidirectional challenge/response protocol before any skill or tool execution begins."
  category: "security"
  rationale: "Without a formal handshake, an agent could execute skills or tools that were never authorized for the current session, silently expanding its effective privileges beyond what governance intended."
}

mandate M016 {
  type: "HARD MANDATE"
  title: "Guardrail Non-Regression"
  description: "Ensure that guardrails evolve in a net-positive direction. Increments and optimizations are allowed and encouraged. Regression -- any change that removes coverage, weakens enforcement, or introduces hazards -- is not."
  category: "governance"
  rationale: "Guardrails are governance infrastructure. The system should get safer over time, not weaker. Silent regression through hacks or lazy refactors is indistinguishable from no regression until a violation actually occurs."
}

mandate M017 {
  type: "HARD MANDATE"
  title: "Analysis Plugin Compliance"
  description: "Ensure that analysis plugins respect SDD-injected base_path, execution_provider, and approval_gate."
  category: "governance"
  rationale: "Plugins extend SDD with external orchestration capabilities. Without governance over their write scope and execution authority, a plugin could silently corrupt the workspace or bypass approval controls."
}

mandate M018 {
  type: "HARD MANDATE"
  title: "Code Quality Baseline"
  description: "Enforce a universal code quality baseline across all language implementations to ensure consistency, maintainability, and correctness of engineering artifacts. Language-specific enforcement is delegated to guideline entries (G-series) that reference this mandate."
  category: "quality"
  rationale: "A shared baseline (lint, format, type-check, full test suite, auto-fix before revalidation) keeps quality consistent across every language implementation instead of leaving it to per-language convention."
}

mandate M019 {
  type: "HARD MANDATE"
  title: "Governance Federation"
  description: "Define how any plugin or skill declares identity, negotiates capabilities, and adheres to host governance before execution inside an SDD-governed environment."
  category: "governance"
  rationale: "M017 covers execution enforcement for analysis plugins specifically. M019 covers the federation layer generally: how any plugin enters the governance environment, declares itself, and is prevented from overriding or inventing rules outside host governance."
}

mandate M020 {
  type: "HARD MANDATE"
  title: "Governed Compact Logging"
  description: "All agent interfaces -- both input to the LLM and output to the user -- must follow the Simple Governed IO pattern: a canonical event or context produces a simple base form, with an optional profile-gated verbose expansion."
  category: "observability"
  rationale: "Governance operations historically produced verbose, narrative-style content on both sides of the agent boundary. A compact canonical form keeps context budgets and user-facing output legible while still allowing verbose expansion when a profile explicitly requires it."
}
