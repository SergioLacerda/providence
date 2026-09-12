"""cached_load decorator and global ContextCache instance."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from ._context_cache import ContextCache


def cached_load(cache_obj: ContextCache) -> Callable[..., Any]:
    """Decorator to add caching to ContextLoader.load_result

    Args:
        cache_obj: ContextCache instance to use

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(self: Any, request: Any) -> Any:
            # Get artifact ID if available
            artifact_id: str | None = None
            if request.artifact is not None:
                # Use artifact's ID if available, otherwise generate one
                attr_id = getattr(request.artifact, "artifact_id", None)
                artifact_id = (
                    str(attr_id) if attr_id is not None else str(id(request.artifact))
                )

            # Get budget utilization percentage from request
            budget_utilization_pct = getattr(request, "budget_utilization_pct", 0.0)
            if budget_utilization_pct is None:
                budget_utilization_pct = 0.0

            # Try cache
            cached = cache_obj.get(
                artifact_id,
                request.query,
                request.max_items,
                request.item_types,
                budget_utilization_pct,
            )
            if cached is not None:
                return cached

            # Cache miss — call original function
            result = func(self, request)

            # Cache the result
            cache_obj.set(
                artifact_id,
                request.query,
                request.max_items,
                request.item_types,
                result,
                budget_utilization_pct,
            )

            return result

        return wrapper

    return decorator


# Global cache instance
_context_cache = ContextCache(max_size=128, ttl_seconds=300)


def get_context_cache() -> ContextCache:
    """Get the global context cache instance

    Returns:
        Global ContextCache instance
    """
    return _context_cache
