"""Intelligence providers for context analysis and compression.

Providers implement the IntelligenceProvider protocol to offer various
strategies for understanding and compressing governance context.

Available providers:
- TfidfProvider: TF-IDF similarity-based provider (pure Python, no ML deps)
- AstProvider: Python AST structure-based provider
- HttpProvider: HTTP-delegated provider for external intelligence services
- LocalIntelligenceProvider: Fallback simple keyword matching (from intelligence.py)
"""

from __future__ import annotations

from .ast_provider import AstProvider
from .http_provider import HttpProvider
from .tfidf_provider import TfidfProvider

__all__ = ["TfidfProvider", "AstProvider", "HttpProvider"]
