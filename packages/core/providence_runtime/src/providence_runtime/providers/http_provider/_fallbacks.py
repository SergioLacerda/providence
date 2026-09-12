"""Fallback results and response deserialization for HttpProvider."""

from __future__ import annotations

from typing import Any

from providence_runtime.intelligence import (
    AnalysisResult,
    BudgetEstimate,
    CompressedContext,
    ContextBundle,
)


def _degraded_analysis_result() -> AnalysisResult:
    return AnalysisResult(
        task_class="unknown",
        complexity_score=0.5,
        suggested_path_id="A",
        keywords=[],
        provider="http",
    )


def _fallback_compressed_context(context: ContextBundle) -> CompressedContext:
    compressed_bytes = sum(len(item.encode()) for item in context.items)
    return CompressedContext(
        items=context.items,
        original_bytes=compressed_bytes,
        compressed_bytes=compressed_bytes,
        compression_ratio=1.0,
        provider="http",
    )


def _fallback_budget_estimate() -> BudgetEstimate:
    return BudgetEstimate(
        estimated_bytes=50_000,
        suggested_path_id="A",
        confidence=0.2,
        provider="http",
    )


_MAX_KEYWORDS = 100
_MAX_STRING_LEN = 1_000
_MAX_ITEMS = 10_000
_MAX_BYTES = 1_000_000_000  # 1 GB sanity ceiling


def _bounded_str(value: Any, *, default: str, max_len: int = _MAX_STRING_LEN) -> str:
    if not isinstance(value, str) or len(value) > max_len:
        raise ValueError(f"expected string of length <= {max_len}, got {value!r}")
    return value or default


def _bounded_float(value: Any, *, lo: float = 0.0, hi: float = 1.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"expected number in [{lo}, {hi}], got {value!r}")
    if not (lo <= value <= hi):
        raise ValueError(f"value {value!r} out of bounds [{lo}, {hi}]")
    return float(value)


def _bounded_int(value: Any, *, lo: int = 0, hi: int = _MAX_BYTES) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"expected int in [{lo}, {hi}], got {value!r}")
    if not (lo <= value <= hi):
        raise ValueError(f"value {value!r} out of bounds [{lo}, {hi}]")
    return int(value)


def _bounded_str_list(
    value: Any, *, max_items: int = _MAX_KEYWORDS, max_item_len: int = _MAX_STRING_LEN
) -> list[str]:
    if not isinstance(value, list) or len(value) > max_items:
        raise ValueError(f"expected list of at most {max_items} strings, got {value!r}")
    for item in value:
        if not isinstance(item, str) or len(item) > max_item_len:
            raise ValueError(f"expected list of bounded strings, got {value!r}")
    return value


def _deserialize_response(
    result_type: type[Any], response_data: dict[str, Any], provider_name: str
) -> Any:
    """Deserialize a raw HTTP response payload into the requested result type.

    Fields are validated against type/size/range bounds so a misbehaving or
    hostile remote endpoint cannot inject oversized or malformed values;
    invalid responses raise ``ValueError``, which callers already treat as a
    provider failure and fall back to a degraded local result.
    """
    if result_type == AnalysisResult:
        return AnalysisResult(
            task_class=_bounded_str(
                response_data.get("task_class", "unknown"), default="unknown"
            ),
            complexity_score=_bounded_float(response_data.get("complexity_score", 0.5)),
            suggested_path_id=_bounded_str(
                response_data.get("suggested_path_id", "A"), default="A", max_len=8
            ),
            keywords=_bounded_str_list(response_data.get("keywords", [])),
            provider=provider_name,
        )
    elif result_type == CompressedContext:
        return CompressedContext(
            items=_bounded_str_list(
                response_data.get("items", []),
                max_items=_MAX_ITEMS,
                max_item_len=_MAX_STRING_LEN * 10,
            ),
            original_bytes=_bounded_int(response_data.get("original_bytes", 0)),
            compressed_bytes=_bounded_int(response_data.get("compressed_bytes", 0)),
            compression_ratio=_bounded_float(
                response_data.get("compression_ratio", 1.0), lo=0.0, hi=10.0
            ),
            provider=provider_name,
        )
    elif result_type == BudgetEstimate:
        return BudgetEstimate(
            estimated_bytes=_bounded_int(response_data.get("estimated_bytes", 50_000)),
            suggested_path_id=_bounded_str(
                response_data.get("suggested_path_id", "A"), default="A", max_len=8
            ),
            confidence=_bounded_float(response_data.get("confidence", 0.5)),
            provider=provider_name,
        )
    else:
        raise ValueError(f"Unknown result type: {result_type}")
