"""Stage-runtime exception types."""


class StageAdvancementError(RuntimeError):
    """Raised when a stage cannot advance to the requested destination."""


class StageCompletionError(RuntimeError):
    """Raised when stage completion payloads are invalid for the current stage."""
