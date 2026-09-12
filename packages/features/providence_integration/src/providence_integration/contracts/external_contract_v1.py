"""External contract v1 for SDD governor <-> narrative executor integration."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

CONTRACT_VERSION_V1 = "1"
NarrativeChannel = Literal["mcp", "sdk"]
NarrativeMode = Literal["refine-only", "delegate"]
NarrativeDomain = Literal["coding", "generic"]
NarrativeOutcome = Literal["success", "fallback", "error"]
ExecutionPath = Literal["internal", "external"]


class NarrativeContractError(ValueError):
    """Base error for contract validation and compatibility failures."""

    code = "CONTRACT_ERROR"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        self.code = code or self.code
        super().__init__(message)


class ContractVersionMismatchError(NarrativeContractError):
    """Raised when the request contract_version is not supported."""

    code = "CONTRACT_VERSION_MISMATCH"


class ModeNotSupportedError(NarrativeContractError):
    """Raised when the requested mode is not accepted by the executor."""

    code = "MODE_NOT_SUPPORTED"


class ChannelNotSupportedError(NarrativeContractError):
    """Raised when the transport channel is not supported."""

    code = "CHANNEL_NOT_SUPPORTED"


class ContractFieldMismatchError(NarrativeContractError):
    """Raised when response fields diverge from the originating request."""

    code = "CONTRACT_FIELD_MISMATCH"


class NarrativeRequestInput(BaseModel):
    """Payload the governor passes to the narrative executor."""

    prompt: str
    context: dict[str, Any] = Field(default_factory=dict)
    token_budget: int | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("prompt")
    @classmethod
    def prompt_must_be_non_empty(cls, value: str) -> str:
        """Reject blank prompts."""
        if not value.strip():
            raise ValueError("prompt must be a non-empty string")
        return value

    @field_validator("token_budget")
    @classmethod
    def token_budget_must_be_positive(cls, value: int | None) -> int | None:
        """Reject non-positive token budgets."""
        if value is not None and value <= 0:
            raise ValueError("token_budget must be positive when provided")
        return value


class NarrativePolicy(BaseModel):
    """Policy flags that control fallback and governance behaviour."""

    preserve_mandates: bool = True
    fallback_on_error: bool = True

    model_config = ConfigDict(extra="forbid")


class NarrativeTelemetry(BaseModel):
    """Mandatory correlation and outcome telemetry."""

    trace_id: str
    channel: NarrativeChannel
    mode: NarrativeMode
    latency_ms: int = Field(ge=0)
    outcome: NarrativeOutcome
    fallback_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_hit: bool | None = None
    model_used: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("trace_id", "model_used", "fallback_reason")
    @classmethod
    def non_empty_optional_strings(cls, value: str | None) -> str | None:
        """Reject blank optional string fields when present."""
        if value is not None and not value.strip():
            raise ValueError("string fields must be non-empty when provided")
        return value

    @model_validator(mode="after")
    def fallback_reason_required_when_needed(self) -> NarrativeTelemetry:
        """Require fallback_reason when outcome is fallback."""
        if self.outcome == "fallback" and not self.fallback_reason:
            raise ValueError("fallback_reason is required when outcome=fallback")
        return self


class NarrativeResponseResult(BaseModel):
    """Structured result returned by the executor."""

    refined_prompt: str | None = None
    response: str | None = None
    compression_ratio: float | None = None
    warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @field_validator("refined_prompt", "response")
    @classmethod
    def non_empty_optional_text(cls, value: str | None) -> str | None:
        """Reject blank optional text fields when present."""
        if value is not None and not value.strip():
            raise ValueError("string fields must be non-empty when provided")
        return value

    @field_validator("compression_ratio")
    @classmethod
    def compression_ratio_in_range(cls, value: float | None) -> float | None:
        """Reject compression ratios outside [0.0, 1.0]."""
        if value is not None and not 0.0 <= value <= 1.0:
            raise ValueError("compression_ratio must be between 0.0 and 1.0")
        return value


class NarrativeRequestEnvelope(BaseModel):
    """Canonical request envelope shared by MCP and SDK channels."""

    contract_version: str
    trace_id: str
    channel: NarrativeChannel
    mode: NarrativeMode
    domain: NarrativeDomain
    input: NarrativeRequestInput
    policy: NarrativePolicy = Field(default_factory=NarrativePolicy)
    governance_context: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    @field_validator("contract_version", "trace_id", "domain")
    @classmethod
    def non_empty_required_text(cls, value: str) -> str:
        """Reject blank required string fields."""
        if not value.strip():
            raise ValueError("field must be a non-empty string")
        return value


class NarrativeResponseEnvelope(BaseModel):
    """Canonical response envelope shared by MCP and SDK channels."""

    contract_version: str
    trace_id: str
    channel: NarrativeChannel
    mode: NarrativeMode
    outcome: NarrativeOutcome
    latency_ms: int = Field(ge=0)
    result: NarrativeResponseResult
    telemetry: NarrativeTelemetry
    fallback_reason: str | None = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("contract_version", "trace_id")
    @classmethod
    def non_empty_required_text(cls, value: str) -> str:
        """Reject blank required string fields."""
        if not value.strip():
            raise ValueError("field must be a non-empty string")
        return value

    @field_validator("fallback_reason")
    @classmethod
    def fallback_reason_non_empty(cls, value: str | None) -> str | None:
        """Reject blank fallback_reason when present."""
        if value is not None and not value.strip():
            raise ValueError("fallback_reason must be non-empty when provided")
        return value

    @model_validator(mode="after")
    def validate_internal_consistency(self) -> NarrativeResponseEnvelope:
        """Verify all correlated fields agree with the response envelope."""
        if self.outcome == "fallback" and not self.fallback_reason:
            raise ValueError("fallback_reason is required when outcome=fallback")
        if self.telemetry.trace_id != self.trace_id:
            raise ValueError("telemetry.trace_id must match response.trace_id")
        if self.telemetry.channel != self.channel:
            raise ValueError("telemetry.channel must match response.channel")
        if self.telemetry.mode != self.mode:
            raise ValueError("telemetry.mode must match response.mode")
        if self.telemetry.outcome != self.outcome:
            raise ValueError("telemetry.outcome must match response.outcome")
        if self.telemetry.fallback_reason != self.fallback_reason:
            raise ValueError(
                "telemetry.fallback_reason must match response.fallback_reason"
            )
        return self


def build_request_envelope(
    *,
    channel: NarrativeChannel,
    mode: NarrativeMode,
    domain: NarrativeDomain,
    prompt: str,
    context: dict[str, Any] | None = None,
    token_budget: int | None = None,
    contract_version: str = CONTRACT_VERSION_V1,
    trace_id: str,
    policy: NarrativePolicy | None = None,
    governance_context: dict[str, Any] | None = None,
) -> NarrativeRequestEnvelope:
    """Create a validated request envelope."""

    return NarrativeRequestEnvelope(
        contract_version=contract_version,
        trace_id=trace_id,
        channel=channel,
        mode=mode,
        domain=domain,
        input=NarrativeRequestInput(
            prompt=prompt,
            context=context or {},
            token_budget=token_budget,
        ),
        policy=policy or NarrativePolicy(),
        governance_context=governance_context or {},
    )


def build_response_envelope(
    *,
    request: NarrativeRequestEnvelope,
    outcome: NarrativeOutcome,
    latency_ms: int,
    result: NarrativeResponseResult | dict[str, Any],
    telemetry: NarrativeTelemetry | dict[str, Any],
    fallback_reason: str | None = None,
) -> NarrativeResponseEnvelope:
    """Create a validated response envelope from an originating request."""

    response = NarrativeResponseEnvelope(
        contract_version=request.contract_version,
        trace_id=request.trace_id,
        channel=request.channel,
        mode=request.mode,
        outcome=outcome,
        latency_ms=latency_ms,
        result=result
        if isinstance(result, NarrativeResponseResult)
        else NarrativeResponseResult.model_validate(result),
        telemetry=telemetry
        if isinstance(telemetry, NarrativeTelemetry)
        else NarrativeTelemetry.model_validate(telemetry),
        fallback_reason=fallback_reason,
    )
    validate_response_matches_request(request, response)
    return response


def validate_request_compatibility(
    request: NarrativeRequestEnvelope,
    *,
    supported_versions: set[str] | None = None,
    supported_modes: set[NarrativeMode] | None = None,
    supported_channels: set[NarrativeChannel] | None = None,
) -> None:
    """Validate request compatibility against supported contract values."""

    versions = supported_versions or {CONTRACT_VERSION_V1}
    modes = supported_modes or {"refine-only", "delegate"}
    channels = supported_channels or {"mcp", "sdk"}

    if request.contract_version not in versions:
        raise ContractVersionMismatchError(
            f"unsupported contract_version: {request.contract_version}"
        )
    if request.mode not in modes:
        raise ModeNotSupportedError(f"unsupported mode: {request.mode}")
    if request.channel not in channels:
        raise ChannelNotSupportedError(f"unsupported channel: {request.channel}")


def validate_response_matches_request(
    request: NarrativeRequestEnvelope,
    response: NarrativeResponseEnvelope,
) -> None:
    """Validate response is semantically aligned with the originating request."""

    if response.contract_version != request.contract_version:
        raise ContractFieldMismatchError(
            "response.contract_version must match request.contract_version"
        )
    if response.trace_id != request.trace_id:
        raise ContractFieldMismatchError(
            "response.trace_id must match request.trace_id"
        )
    if response.channel != request.channel:
        raise ContractFieldMismatchError("response.channel must match request.channel")
    if response.mode != request.mode:
        raise ContractFieldMismatchError("response.mode must match request.mode")


def choose_execution_path(
    *,
    allow_external_delegation: bool,
    mode: NarrativeMode,
) -> ExecutionPath:
    """Resolve internal vs external execution path for the decision gate."""

    return (
        "external" if allow_external_delegation and mode == "delegate" else "internal"
    )


def resolve_fallback_outcome(
    *,
    contract_version_supported: bool,
    executor_available: bool,
    timeout_occurred: bool,
    unsafe_response: bool,
    fallback_on_error: bool,
) -> tuple[NarrativeOutcome, str | None]:
    """Resolve deterministic outcome and fallback reason."""

    if not contract_version_supported:
        return "error", "CONTRACT_VERSION_MISMATCH"
    if unsafe_response:
        return "error", "unsafe_response"
    if timeout_occurred:
        if fallback_on_error:
            return "fallback", "SEMANTIC_TIMEOUT"
        return "error", "SEMANTIC_TIMEOUT"
    if not executor_available:
        if fallback_on_error:
            return "fallback", "LLM_UNAVAILABLE"
        return "error", "LLM_UNAVAILABLE"
    return "success", None


def raise_contract_validation_error(exc: ValidationError) -> NarrativeContractError:
    """Convert a Pydantic validation error into a governed contract error."""

    message = exc.errors(include_url=False)[0].get("msg", str(exc))
    return NarrativeContractError(message)
