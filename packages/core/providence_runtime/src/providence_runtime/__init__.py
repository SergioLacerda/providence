"""providence_runtime - runtime execution engine for SDD governance.

The runtime executes compiled governance — it never acts as a normative
source.  All decisions are traceable to canonical artifact IDs.
"""

from .alerts import AlertDispatcher
from .artifacts import CompiledArtifact, GovernanceItem
from .budget import (
    ReflectionCapReachedError,
    RetryBudget,
    RetryCapReachedError,
    TokenBudgetBreachError,
)
from .context import BudgetBreachError, ContextLoader, ContextRequest, ContextResult
from .drift import DriftDetector, DriftReport
from .entropy import (
    ConvergenceReport,
    ConvergenceTracker,
    DecompositionSuggestion,
    EntropyAdvisor,
    EntropyScore,
    PathDistribution,
    SessionDriftScorer,
)
from .injection import GovernanceInjector, InjectionResult
from .intelligence import (
    AnalysisResult,
    BudgetEstimate,
    CompressedContext,
    ContextBundle,
    IntelligenceProvider,
    LocalIntelligenceProvider,
    ProviderRegistry,
    TaskContext,
)
from .learning import FailureLedgerEntry, RuleCandidate, SupervisedLearningStore
from .metrics import (
    EconomySnapshot,
    ModelMetrics,
    PrometheusTextRenderer,
    TokenEconomyCollector,
)
from .otel import OtelExporter, OtlpHttpExporter
from .policy import PolicyEngine, PolicyResult
from .providers import AstProvider, HttpProvider, TfidfProvider
from .reader import BudgetStatus, TelemetryReader, TokenStats
from .session import SessionManager, SessionState
from .skills import (
    AwakeningProfile,
    SkillContractError,
    SkillDefinition,
    SkillEngine,
    SkillRunResult,
    UnauthorizedSkillError,
    format_governance_footer,
    validate_awakening_profile,
    validate_skill_definition,
)
from .telemetry import (
    EVENT_SCHEMA_VERSION,
    OtelAttributes,
    OtelBridge,
    RuntimeEvent,
    TelemetrySink,
    create_sink,
    get_otel_endpoint,
)
from .validator import SchemaValidator, TraceabilityValidator, is_sensitive_event

__all__ = [
    # Artifacts
    "CompiledArtifact",
    "GovernanceItem",
    # Session
    "SessionManager",
    "SessionState",
    # Skills runtime
    "SkillContractError",
    "UnauthorizedSkillError",
    "SkillDefinition",
    "AwakeningProfile",
    "SkillRunResult",
    "SkillEngine",
    "format_governance_footer",
    "validate_skill_definition",
    "validate_awakening_profile",
    # Governance injection
    "GovernanceInjector",
    "InjectionResult",
    # Policy
    "PolicyEngine",
    "PolicyResult",
    # Context loading
    "BudgetBreachError",
    "ContextLoader",
    "ContextRequest",
    "ContextResult",
    # Budget enforcement (§economy/efficiency-policy.md)
    "RetryBudget",
    "RetryCapReachedError",
    "ReflectionCapReachedError",
    "TokenBudgetBreachError",  # raw token/cost ceiling breach (budget.py)
    # Pluggable Intelligence Providers (§economy/efficiency-policy.md Phase 5-6)
    "AnalysisResult",
    "BudgetEstimate",
    "CompressedContext",
    "ContextBundle",
    "IntelligenceProvider",
    "LocalIntelligenceProvider",
    "ProviderRegistry",
    "TaskContext",
    # Supervised learning
    "FailureLedgerEntry",
    "RuleCandidate",
    "SupervisedLearningStore",
    # Provider implementations (§6.3)
    "TfidfProvider",
    "AstProvider",
    "HttpProvider",
    # Cognitive entropy scoring (§economy/efficiency-policy.md Phase 4)
    "ConvergenceReport",
    "ConvergenceTracker",
    "DecompositionSuggestion",
    "EntropyAdvisor",
    "EntropyScore",
    "PathDistribution",
    "SessionDriftScorer",
    # Drift detection
    "DriftDetector",
    "DriftReport",
    # Telemetry
    "EVENT_SCHEMA_VERSION",
    "RuntimeEvent",
    "TelemetrySink",
    "create_sink",  # Phase 1: Factory for OTel activation via env var
    "get_otel_endpoint",
    # Telemetry Reader (Phase 1: Local query interface)
    "TelemetryReader",
    "TokenStats",
    "BudgetStatus",
    # OTEL bridge (§13 Phase C)
    "OtelAttributes",
    "OtelBridge",
    "OtelExporter",
    "OtlpHttpExporter",
    # Validators
    "SchemaValidator",
    "TraceabilityValidator",
    "is_sensitive_event",
    # Fase 2: Metrics and alerts
    "TokenEconomyCollector",
    "EconomySnapshot",
    "ModelMetrics",
    "PrometheusTextRenderer",
    "AlertDispatcher",
]
