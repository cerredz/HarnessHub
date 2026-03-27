"""Centralized application exception taxonomy."""

from __future__ import annotations


class AppError(Exception):
    """Base class for application-defined failures."""

    http_status = 500


class ValidationError(AppError, ValueError):
    """Raised when caller-provided input or arguments fail validation."""

    http_status = 422


class ConfigurationError(ValidationError):
    """Raised when runtime dependencies or configuration are invalid."""

    http_status = 500


class NotFoundError(AppError, LookupError):
    """Raised when a requested application resource cannot be found."""

    http_status = 404


class ResourceNotFoundError(NotFoundError, FileNotFoundError):
    """Raised when a file-backed resource cannot be found."""

    http_status = 404


class StateError(AppError, RuntimeError):
    """Raised when an operation is invalid for the current runtime state."""

    http_status = 409


class ExternalServiceError(AppError, RuntimeError):
    """Raised when an external service or transport request fails."""

    http_status = 502


__all__ = [
    "AppError",
    "ConfigurationError",
    "ExternalServiceError",
    "NotFoundError",
    "ResourceNotFoundError",
    "StateError",
    "ValidationError",
]
