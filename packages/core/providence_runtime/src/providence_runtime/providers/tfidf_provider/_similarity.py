"""Tokenization and cosine-similarity helpers for TfidfProvider."""

from __future__ import annotations

import math
from collections import Counter


def _tokenize(text: str) -> list[str]:
    """Simple word tokenization (lowercase, split on whitespace)."""
    return text.lower().split()


def _cosine_similarity(vec1: list[str], vec2: list[str]) -> float:
    """Compute cosine similarity between two token vectors."""
    count1 = Counter(vec1)
    count2 = Counter(vec2)

    if not count1 or not count2:
        return 0.0

    dot_product = sum(count1[term] * count2[term] for term in count1 if term in count2)
    magnitude1 = math.sqrt(sum(count**2 for count in count1.values()))
    magnitude2 = math.sqrt(sum(count**2 for count in count2.values()))

    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)
