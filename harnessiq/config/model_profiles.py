"""Global persisted model-profile configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping

from harnessiq.shared.providers import SUPPORTED_PROVIDERS
from harnessiq.utils.ledger_connections import harnessiq_home_dir

DEFAULT_MODEL_PROFILES_FILENAME = "models.json"
_SUPPORTED_PROVIDER_NAMES = frozenset(SUPPORTED_PROVIDERS)
_SUPPORTED_REASONING_EFFORTS = frozenset({"low", "medium", "high"})

ReasoningEffort = Literal["low", "medium", "high"]


@dataclass(frozen=True, slots=True)
class ModelProfile:
    """One named reusable provider/model configuration."""

    name: str
    provider: str
    model_name: str
    temperature: float | None = None
    max_output_tokens: int | None = None
    reasoning_effort: ReasoningEffort | None = None

    def __post_init__(self) -> None:
        normalized_name = self.name.strip()
        normalized_provider = self.provider.strip().lower()
        normalized_model_name = self.model_name.strip()
        if not normalized_name:
            raise ValueError("Model profile name must not be blank.")
        if normalized_provider not in _SUPPORTED_PROVIDER_NAMES:
            supported = ", ".join(sorted(_SUPPORTED_PROVIDER_NAMES))
            raise ValueError(
                f"Unsupported model provider '{self.provider}'. Supported providers: {supported}."
            )
        if not normalized_model_name:
            raise ValueError("Model profile model_name must not be blank.")
        if isinstance(self.temperature, bool):
            raise ValueError("Model profile temperature must be a number when provided.")
        if self.max_output_tokens is not None:
            if isinstance(self.max_output_tokens, bool) or self.max_output_tokens <= 0:
                raise ValueError("Model profile max_output_tokens must be greater than zero when provided.")
        if self.reasoning_effort is not None and self.reasoning_effort not in _SUPPORTED_REASONING_EFFORTS:
            supported_efforts = ", ".join(sorted(_SUPPORTED_REASONING_EFFORTS))
            raise ValueError(
                f"Unsupported reasoning_effort '{self.reasoning_effort}'. Supported values: {supported_efforts}."
            )
        object.__setattr__(self, "name", normalized_name)
        object.__setattr__(self, "provider", normalized_provider)
        object.__setattr__(self, "model_name", normalized_model_name)
        if self.temperature is not None:
            object.__setattr__(self, "temperature", float(self.temperature))
        if self.max_output_tokens is not None:
            object.__setattr__(self, "max_output_tokens", int(self.max_output_tokens))

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model_name": self.model_name,
            "name": self.name,
            "provider": self.provider,
        }
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        if self.max_output_tokens is not None:
            payload["max_output_tokens"] = self.max_output_tokens
        if self.reasoning_effort is not None:
            payload["reasoning_effort"] = self.reasoning_effort
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ModelProfile":
        return cls(
            name=str(payload["name"]),
            provider=str(payload["provider"]),
            model_name=str(payload["model_name"]),
            temperature=(
                float(payload["temperature"])
                if payload.get("temperature") is not None
                else None
            ),
            max_output_tokens=(
                int(payload["max_output_tokens"])
                if payload.get("max_output_tokens") is not None
                else None
            ),
            reasoning_effort=(
                str(payload["reasoning_effort"])
                if payload.get("reasoning_effort") is not None
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class ModelProfileCatalog:
    """Collection of named reusable model profiles."""

    profiles: tuple[ModelProfile, ...] = ()

    def __post_init__(self) -> None:
        normalized_profiles = tuple(self.profiles)
        indexed_names: set[str] = set()
        for profile in normalized_profiles:
            if not isinstance(profile, ModelProfile):
                raise TypeError("profiles must contain ModelProfile instances.")
            if profile.name in indexed_names:
                raise ValueError(f"Duplicate model profile '{profile.name}'.")
            indexed_names.add(profile.name)
        object.__setattr__(self, "profiles", normalized_profiles)

    def as_dict(self) -> dict[str, Any]:
        return {"profiles": [profile.as_dict() for profile in self.profiles]}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ModelProfileCatalog":
        raw_profiles = payload.get("profiles", [])
        if not isinstance(raw_profiles, list):
            raise ValueError("Model profile config must define 'profiles' as a list.")
        return cls(profiles=tuple(ModelProfile.from_dict(item) for item in raw_profiles))

    def profile_for(self, name: str) -> ModelProfile:
        normalized_name = name.strip()
        for profile in self.profiles:
            if profile.name == normalized_name:
                return profile
        raise KeyError(f"No model profile exists with the name '{name}'.")

    def upsert(self, profile: ModelProfile) -> "ModelProfileCatalog":
        indexed = {item.name: item for item in self.profiles}
        indexed[profile.name] = profile
        return ModelProfileCatalog(profiles=tuple(indexed[name] for name in sorted(indexed)))

    def remove(self, name: str) -> "ModelProfileCatalog":
        normalized_name = name.strip()
        indexed = {item.name: item for item in self.profiles}
        indexed.pop(normalized_name, None)
        return ModelProfileCatalog(profiles=tuple(indexed[name] for name in sorted(indexed)))


@dataclass(slots=True)
class ModelProfileStore:
    """Persist model profiles under the global HarnessIQ home directory."""

    home_dir: Path | str | None = None

    def __post_init__(self) -> None:
        self.home_dir = harnessiq_home_dir(self.home_dir)

    @property
    def config_path(self) -> Path:
        return Path(self.home_dir) / DEFAULT_MODEL_PROFILES_FILENAME

    def load(self) -> ModelProfileCatalog:
        if not self.config_path.exists():
            return ModelProfileCatalog()
        raw = self.config_path.read_text(encoding="utf-8").strip()
        if not raw:
            return ModelProfileCatalog()
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("Model profile config file must contain a JSON object.")
        return ModelProfileCatalog.from_dict(payload)

    def save(self, catalog: ModelProfileCatalog) -> Path:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(catalog.as_dict(), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return self.config_path

    def upsert(self, profile: ModelProfile) -> Path:
        return self.save(self.load().upsert(profile))

    def remove(self, name: str) -> Path:
        return self.save(self.load().remove(name))


__all__ = [
    "DEFAULT_MODEL_PROFILES_FILENAME",
    "ModelProfile",
    "ModelProfileCatalog",
    "ModelProfileStore",
    "ReasoningEffort",
]
