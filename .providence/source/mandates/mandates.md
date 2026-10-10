# Mandates - SDD v3.0

 IA-FIRST DESIGN NOTICE
- **Status**: Architecture-level governance rules
- **Optimization**: Optimized for AI agent parsing
- **Version**: 3.0
- **Generated**: 2026-10-02T22:19:05.635657

## Core Mandates

Mandatory rules that CANNOT be customized or skipped.

## M001: Clean Architecture

**Criticality**: high
**Customizable**: No

Ensure maintainability and testability by separating concerns into distinct, independent layers using the 8-layer Clean Architecture pattern: Domain, Use Cases, Ports, Adapters, Infrastructure, External Services, UI/CLI, Composition Root.

## M002: Test-Driven Development (TDD)

**Criticality**: high
**Customizable**: No

Ensure 100% functional coverage and design clarity by writing tests before implementation code, following the Red-Green-Refactor cycle.

## M003: Context Awareness & Task Caching

**Criticality**: high
**Customizable**: No

Ensure absolute continuity of state and logic across parallel agents, long-running tasks, and multi-repository environments by maintaining a persistent, project-isolated Context Cache.

## M005: Token Economy Enforcement

**Criticality**: high
**Customizable**: No

Ensure every agent respects token budget zones and circuit-breaker thresholds to prevent context overflow, degraded output, and undetected budget breaches.

## M006: RFC Process for Breaking Changes

**Criticality**: high
**Customizable**: No

Breaking changes to the SDD framework (CLI commands, governance schema, artifact formats, or runtime contracts) must go through a formal Request for Comments process before shipping.

## M007: Telemetry Enforcement

**Criticality**: high
**Customizable**: No

Ensure 100% traceability of agentic decisions and governance compliance via structured telemetry and OpenTelemetry integration.

## M008: Audit Integrity

**Criticality**: high
**Customizable**: No

Preserve and protect the integrity of the audit trail (.providence/audit-trail/compliance-events.jsonl) to ensure forensic capability, regulatory compliance, and accountability for all governance-aware operations.

## M009: OpenTelemetry Compliance

**Criticality**: high
**Customizable**: No

Maintain distributed trace continuity across the agentic ecosystem by enforcing valid OpenTelemetry (OTEL) context propagation on all governance-aware operations.

## M010: Delivery Hygiene Enforcement

**Criticality**: high
**Customizable**: No

Guarantee that every implementation is delivered with updated tests and strict quality hygiene, including mandatory auto-fix and revalidation before handoff.

## M011: English Language Standard

**Criticality**: high
**Customizable**: No

Enforce a single language standard for engineering artifacts to prevent ambiguity, mixed-language drift, and communication inconsistency across humans and agents.


**Mandatory surfaces**: code, technical_docs, governance, cli_help

**Contextual surfaces**: chat, ui, workspace_local_docs, analysis_docs

**Context source**: wizard `language_context` preferences guide contextual surfaces only and never override M011.

**Workspace-local docs paths**: .analysis/

**Guideline anchors**: G021, G022

## M015: Bidirectional Agent Handshake

**Criticality**: high
**Customizable**: No

Ensure every agentic interaction is governed by a formal trust boundary via a bidirectional challenge/response protocol before any skill or tool execution begins.

## M016: Guardrail Non-Regression

**Criticality**: high
**Customizable**: No

Ensure that guardrails evolve in a net-positive direction. Increments and optimizations are allowed and encouraged. Regression -- any change that removes coverage, weakens enforcement, or introduces hazards -- is not.

## M017: Analysis Plugin Compliance

**Criticality**: high
**Customizable**: No

Ensure that analysis plugins respect SDD-injected base_path, execution_provider, and approval_gate.

## M018: Code Quality Baseline

**Criticality**: high
**Customizable**: No

Enforce a universal code quality baseline across all language implementations to ensure consistency, maintainability, and correctness of engineering artifacts. Language-specific enforcement is delegated to guideline entries (G-series) that reference this mandate.

## M019: Governance Federation

**Criticality**: high
**Customizable**: No

Define how any plugin or skill declares identity, negotiates capabilities, and adheres to host governance before execution inside an SDD-governed environment.

## M020: Governed Compact Logging

**Criticality**: high
**Customizable**: No

All agent interfaces -- both input to the LLM and output to the user -- must follow the Simple Governed IO pattern: a canonical event or context produces a simple base form, with an optional profile-gated verbose expansion.
