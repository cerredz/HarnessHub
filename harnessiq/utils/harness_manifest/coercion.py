"""Coercion helpers for harness manifest parameter values."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping

if TYPE_CHECKING:
    from harnessiq.shared.harness_manifest import HarnessParameterSpec


def coerce_parameters(
    parameters: Mapping[str, Any],
    *,
    specs: tuple["HarnessParameterSpec", ...],
    open_ended: bool,
    label: str,
) -> dict[str, Any]:
    """Normalize one parameter mapping according to manifest-declared specs."""
    if open_ended and not specs:
        return {str(key): value for key, value in parameters.items()}
    spec_index = {spec.key: spec for spec in specs}
    normalized: dict[str, Any] = {}
    for raw_key, value in parameters.items():
        key = str(raw_key).strip()
        spec = spec_index.get(key)
        if spec is None:
            if open_ended:
                normalized[key] = value
                continue
            supported = ", ".join(sorted(spec_index))
            raise ValueError(f"Unsupported {label} parameter '{key}'. Supported: {supported}.")
        normalized[key] = spec.coerce(value)
    return normalized


def is_empty_nullable(value: Any) -> bool:
    """Treat blank or explicit null-like strings as an empty nullable parameter value."""
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    normalized = value.strip().lower()
    return not normalized or normalized in {"null", "none"}


def coerce_integer(value: Any) -> int:
    """Coerce one manifest parameter value to an integer with boolean rejection."""
    if isinstance(value, bool):
        raise ValueError("Boolean values are not valid integer parameters.")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        return int(value)
    raise ValueError("Parameter must be an integer.")


def coerce_number(value: Any) -> float:
    """Coerce one manifest parameter value to a float with boolean rejection."""
    if isinstance(value, bool):
        raise ValueError("Boolean values are not valid numeric parameters.")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        return float(value)
    raise ValueError("Parameter must be a number.")


def coerce_boolean(value: Any) -> bool:
    """Coerce one manifest parameter value to a boolean using common CLI literals."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    raise ValueError("Parameter must be a boolean.")


def coerce_string(value: Any) -> str:
    """Coerce one manifest parameter value to a non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Parameter must be a non-empty string.")
    return value


__all__ = [
    "coerce_boolean",
    "coerce_integer",
    "coerce_number",
    "coerce_parameters",
    "coerce_string",
    "is_empty_nullable",
]
