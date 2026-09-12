"""Base."""

from typing import Any

from providence_integration.engine.types import RuntimeContext


class Assertion:
    """Assertion."""

    def __init__(self, **kwargs: Any) -> None:
        self.params: dict[str, Any] = kwargs

    def execute(self, context: RuntimeContext) -> Any:
        """Execute."""
        raise NotImplementedError()

    def param_str(self, key: str, default: str = "") -> str:
        """Param Str."""
        value = self.params.get(key, default)
        return str(value)

    def param_int(self, key: str, default: int = 0) -> int:
        """Param Int."""
        value = self.params.get(key, default)
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return default
        return default
