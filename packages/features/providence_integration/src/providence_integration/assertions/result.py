"""Result."""


class AssertionResult:
    """Assertion result container."""

    def __init__(self, success: bool, message: str = ""):
        self.success = success
        self.message = message
