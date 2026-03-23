"""Model metadata extraction helpers for provider-backed output sinks."""

from __future__ import annotations

from typing import Any, Mapping

_known_model_provider_names = (
    "openai",
    "anthropic",
    "grok",
    "gemini",
    "exa",
    "resend",
    "notion",
    "confluence",
    "supabase",
    "linear",
    "slack",
    "discord",
)
_known_client_provider_names = (
    "openai",
    "anthropic",
    "grok",
    "gemini",
    "exa",
    "resend",
    "notion",
    "confluence",
    "supabase",
    "linear",
)


def extract_model_metadata(model: Any) -> dict[str, Any]:
    """Return best-effort provider/model metadata for an injected AgentModel."""
    metadata: dict[str, Any] = {
        "model_class": type(model).__name__,
        "model_module": type(model).__module__,
    }
    custom = getattr(model, "ledger_metadata", None)
    if callable(custom):
        provided = custom()
        if isinstance(provided, Mapping):
            metadata.update({str(key): value for key, value in provided.items()})
            return metadata

    provider = _extract_provider_name(model)
    model_name = _extract_model_name(model)
    if provider is not None:
        metadata["provider"] = provider
    if model_name is not None:
        metadata["model_name"] = model_name

    tracing_enabled = _coerce_optional_bool(getattr(model, "_tracing_enabled", None))
    if tracing_enabled is not None:
        metadata["tracing_enabled"] = tracing_enabled
    project_name = _coerce_optional_string(getattr(model, "_project_name", None))
    if project_name is not None:
        metadata["project_name"] = project_name
    return metadata


def _extract_provider_name(model: Any) -> str | None:
    for attribute_name in ("provider", "_provider", "provider_name", "_provider_name"):
        candidate = _coerce_optional_string(getattr(model, attribute_name, None))
        if candidate is not None:
            return candidate

    module = type(model).__module__.lower()
    for name in _known_model_provider_names:
        if name in module:
            return name

    client = getattr(model, "_client", None)
    if client is None:
        return None
    client_module = type(client).__module__.lower()
    for name in _known_client_provider_names:
        if name in client_module:
            return name
    return None


def _extract_model_name(model: Any) -> str | None:
    for attribute_name in ("model_name", "_model_name", "model", "_model"):
        candidate = _coerce_optional_string(getattr(model, attribute_name, None))
        if candidate is not None:
            return candidate
    return None


def _coerce_optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _coerce_optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


__all__ = ["extract_model_metadata"]
