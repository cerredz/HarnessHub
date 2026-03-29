"""Artifact-formalization runtime exception types."""


class ArtifactNotFoundError(FileNotFoundError):
    """Raised when a required input artifact is not present on disk."""


class OutputArtifactMissingError(RuntimeError):
    """Raised when required output artifacts are still missing."""


__all__ = ["ArtifactNotFoundError", "OutputArtifactMissingError"]
