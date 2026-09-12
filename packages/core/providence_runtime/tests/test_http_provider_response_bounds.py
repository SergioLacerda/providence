"""Tests for HttpProvider response bounds validation (_deserialize_response)."""

from __future__ import annotations

import pytest
from providence_runtime.intelligence import (
    AnalysisResult,
    BudgetEstimate,
    CompressedContext,
)
from providence_runtime.providers.http_provider._fallbacks import _deserialize_response


def test_analysis_result_accepts_well_formed_response() -> None:
    result = _deserialize_response(
        AnalysisResult,
        {
            "task_class": "bug-fix",
            "complexity_score": 0.7,
            "suggested_path_id": "B",
            "keywords": ["auth", "regression"],
        },
        "http",
    )
    assert result.task_class == "bug-fix"
    assert result.complexity_score == 0.7


def test_analysis_result_rejects_out_of_range_complexity_score() -> None:
    with pytest.raises(ValueError, match="out of bounds"):
        _deserialize_response(
            AnalysisResult,
            {
                "task_class": "bug-fix",
                "complexity_score": 42.0,
                "suggested_path_id": "A",
                "keywords": [],
            },
            "http",
        )


def test_analysis_result_rejects_oversized_keyword_list() -> None:
    with pytest.raises(ValueError, match="expected list of at most"):
        _deserialize_response(
            AnalysisResult,
            {
                "task_class": "bug-fix",
                "complexity_score": 0.5,
                "suggested_path_id": "A",
                "keywords": [f"kw{i}" for i in range(1000)],
            },
            "http",
        )


def test_analysis_result_rejects_wrong_type_task_class() -> None:
    with pytest.raises(ValueError, match="expected string of length"):
        _deserialize_response(
            AnalysisResult,
            {
                "task_class": 12345,
                "complexity_score": 0.5,
                "suggested_path_id": "A",
                "keywords": [],
            },
            "http",
        )


def test_compressed_context_rejects_negative_bytes() -> None:
    with pytest.raises(ValueError, match="out of bounds"):
        _deserialize_response(
            CompressedContext,
            {
                "items": ["a"],
                "original_bytes": -1,
                "compressed_bytes": 0,
                "compression_ratio": 1.0,
            },
            "http",
        )


def test_budget_estimate_rejects_huge_estimated_bytes() -> None:
    with pytest.raises(ValueError, match="out of bounds"):
        _deserialize_response(
            BudgetEstimate,
            {"estimated_bytes": 10**15, "suggested_path_id": "A", "confidence": 0.5},
            "http",
        )


def test_budget_estimate_accepts_well_formed_response() -> None:
    result = _deserialize_response(
        BudgetEstimate,
        {"estimated_bytes": 12_000, "suggested_path_id": "A", "confidence": 0.9},
        "http",
    )
    assert result.estimated_bytes == 12_000
    assert result.confidence == 0.9
