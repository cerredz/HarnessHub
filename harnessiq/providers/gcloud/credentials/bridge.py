"""Binding-aware credential bridge between repo-local config and GCP secrets."""

from __future__ import annotations

import getpass
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from harnessiq.config import (
    AgentCredentialsNotConfiguredError,
    CredentialsConfigStore,
    DotEnvFileNotFoundError,
    get_provider_credential_spec,
    parse_dotenv_file,
)
from harnessiq.shared.harness_manifests import get_harness_manifest

from harnessiq.providers.gcloud.base import BaseGcpProvider
from harnessiq.providers.gcloud.credentials.secret_manager import SecretManagerProvider

_UNIVERSAL_ENV_VAR = "ANTHROPIC_API_KEY"
_UNIVERSAL_SECRET_NAME = "HARNESSIQ_ANTHROPIC_API_KEY"


@dataclass(frozen=True, slots=True)
class _CredentialTemplate:
    key: str
    env_var: str | None
    secret_name: str
    description: str
    required: bool
    source: str
    missing_reason: str | None = None


@dataclass(slots=True)
class CredentialEntry:
    """Resolved status for one runtime credential without exposing raw values by default."""

    key: str
    env_var: str | None
    secret_name: str
    description: str
    required: bool = True
    in_gcp: bool = False
    source: str = "binding"
    missing_reason: str | None = None
    local_value: str | None = field(default=None, repr=False)

    @property
    def has_local_value(self) -> bool:
        return bool(self.local_value)

    def status_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "description": self.description,
            "env_var": self.env_var,
            "gcp": self.in_gcp,
            "key": self.key,
            "local": self.has_local_value,
            "required": self.required,
            "secret_name": self.secret_name,
            "source": self.source,
        }
        if self.missing_reason:
            payload["missing_reason"] = self.missing_reason
        return payload


class CredentialBridge(BaseGcpProvider):
    """Resolve repo-local harness credential bindings and mirror them into GCP."""

    def __init__(
        self,
        client,
        config,
        *,
        repo_root: Path | str | None = None,
        secret_manager: SecretManagerProvider | None = None,
    ) -> None:
        super().__init__(client, config)
        resolved_repo_root = Path(repo_root) if repo_root is not None else self._resolve_repo_root(Path.cwd())
        self._repo_root = resolved_repo_root.expanduser().resolve()
        self._secret_manager = secret_manager or SecretManagerProvider(client, config)

    @property
    def repo_root(self) -> Path:
        return self._repo_root

    def discover(self) -> list[CredentialEntry]:
        env_values = self._load_repo_env_values()
        templates = self._build_templates()
        return [
            CredentialEntry(
                key=template.key,
                env_var=template.env_var,
                secret_name=template.secret_name,
                description=template.description,
                required=template.required,
                in_gcp=self._secret_manager.secret_exists(template.secret_name),
                source=template.source,
                missing_reason=template.missing_reason,
                local_value=(env_values.get(template.env_var) if template.env_var else None),
            )
            for template in templates
        ]

    def status(self) -> list[CredentialEntry]:
        return self.discover()

    def sync(self, interactive: bool = True, dry_run: bool = False) -> list[CredentialEntry]:
        entries = self.discover()
        needs_save = False

        missing_bindings = [entry for entry in entries if entry.required and entry.env_var is None]
        if missing_bindings:
            first = missing_bindings[0]
            raise RuntimeError(self._missing_binding_message(first.key, first.missing_reason))

        for entry in entries:
            if not entry.local_value and not entry.in_gcp:
                if not entry.required:
                    continue
                if interactive and entry.env_var:
                    entry.local_value = getpass.getpass(
                        f"Enter value for {entry.env_var} to store in GCP Secret Manager: "
                    )
                else:
                    raise RuntimeError(
                        f"Required credential '{entry.key}' is not available locally and does not exist in "
                        f"GCP Secret Manager. {self._missing_local_fix(entry)}"
                    )

            if entry.local_value and not entry.in_gcp:
                if not dry_run:
                    self._secret_manager.set_secret(entry.secret_name, entry.local_value)
                entry.in_gcp = True
                needs_save = True
            elif entry.local_value and entry.in_gcp:
                if interactive:
                    overwrite = input(
                        f"Secret '{entry.secret_name}' already exists in GCP. Overwrite it with the local value? [y/N] "
                    ).strip().lower()
                    if overwrite == "y":
                        if not dry_run:
                            self._secret_manager.rotate_secret(entry.secret_name, entry.local_value)
                        needs_save = True
                else:
                    pass

            if entry.in_gcp and entry.env_var and self._register_secret_reference(entry):
                needs_save = True

        if needs_save and not dry_run:
            self.config.save()
        return entries

    def add_custom(
        self,
        env_var: str,
        secret_name: str,
        *,
        value: str | None = None,
        dry_run: bool = False,
    ) -> None:
        normalized_env_var = env_var.strip()
        normalized_secret_name = secret_name.strip()
        if not normalized_env_var:
            raise ValueError("env_var must not be blank.")
        if not normalized_secret_name:
            raise ValueError("secret_name must not be blank.")

        resolved_value = value
        if resolved_value is None:
            resolved_value = self._load_repo_env_values().get(normalized_env_var)
        if resolved_value is None:
            resolved_value = getpass.getpass(f"Enter value for {normalized_env_var}: ")

        if not dry_run:
            self._secret_manager.set_secret(normalized_secret_name, resolved_value)
        updated = self._register_secret_reference(
            CredentialEntry(
                key=normalized_env_var,
                env_var=normalized_env_var,
                secret_name=normalized_secret_name,
                description=f"Custom credential for {normalized_env_var}",
                in_gcp=True,
            )
        )
        if updated and not dry_run:
            self.config.save()

    def remove(self, env_var: str, *, delete_from_gcp: bool = False, dry_run: bool = False) -> None:
        normalized_env_var = env_var.strip()
        if not normalized_env_var:
            raise ValueError("env_var must not be blank.")
        secret = next((item for item in self.config.secrets if item["env_var"] == normalized_env_var), None)
        if secret is None:
            raise ValueError(f"No credential with env_var '{normalized_env_var}' is registered for this config.")

        if delete_from_gcp and not dry_run:
            self._secret_manager.delete_secret(secret["secret_name"])

        self.config.secrets = [
            item for item in self.config.secrets if item["env_var"] != normalized_env_var
        ]
        if not dry_run:
            self.config.save()

    def _build_templates(self) -> list[_CredentialTemplate]:
        templates: list[_CredentialTemplate] = [
            _CredentialTemplate(
                key=_UNIVERSAL_ENV_VAR,
                env_var=_UNIVERSAL_ENV_VAR,
                secret_name=_UNIVERSAL_SECRET_NAME,
                description="Anthropic API key for provider-backed model execution.",
                required=True,
                source="repo_env",
            )
        ]

        manifest = self._load_manifest()
        if manifest is None:
            return templates

        references = self._load_binding_references()
        seen_keys = {template.key for template in templates}

        for family in manifest.provider_families:
            spec = self._load_provider_spec(family)
            if spec is None:
                continue
            for field in spec.fields:
                key = f"{family}.{field.name}"
                env_var = references.get(key)
                templates.append(
                    _CredentialTemplate(
                        key=key,
                        env_var=env_var,
                        secret_name=self._secret_name_for_binding_reference(
                            env_var=env_var,
                            key=key,
                        ),
                        description=field.description,
                        required=True,
                        source=("binding" if env_var else "missing_binding"),
                        missing_reason=(
                            None
                            if env_var
                            else f"No repo-local credential binding exists for '{key}' under '{self.config.credential_binding_name}'."
                        ),
                    )
                )
                seen_keys.add(key)

        for key, env_var in sorted(references.items()):
            if key in seen_keys:
                continue
            family, separator, field_name = key.partition(".")
            if not separator:
                continue
            spec = self._load_provider_spec(family)
            description = (
                next((field.description for field in spec.fields if field.name == field_name), None)
                if spec is not None
                else None
            )
            templates.append(
                _CredentialTemplate(
                    key=key,
                    env_var=env_var,
                    secret_name=self._secret_name_for_binding_reference(env_var=env_var, key=key),
                    description=description or f"{family} credential field '{field_name}'.",
                    required=True,
                    source="binding",
                )
            )
            seen_keys.add(key)

        return templates

    def _load_manifest(self):
        if self.config.manifest_id is None:
            return None
        return get_harness_manifest(self.config.manifest_id)

    def _load_provider_spec(self, family: str):
        try:
            return get_provider_credential_spec(family)
        except KeyError:
            return None

    def _load_binding_references(self) -> dict[str, str]:
        if self.config.manifest_id is None:
            return {}
        store = CredentialsConfigStore(repo_root=self.repo_root)
        try:
            binding = store.load().binding_for(self.config.credential_binding_name)
        except AgentCredentialsNotConfiguredError:
            return {}
        return {
            reference.field_name: reference.env_var
            for reference in binding.references
        }

    def _load_repo_env_values(self) -> dict[str, str]:
        store = CredentialsConfigStore(repo_root=self.repo_root)
        try:
            return parse_dotenv_file(store.env_path)
        except DotEnvFileNotFoundError:
            return {}

    def _register_secret_reference(self, entry: CredentialEntry) -> bool:
        if entry.env_var is None:
            return False
        existing = next(
            (
                item for item in self.config.secrets
                if item["secret_name"] == entry.secret_name or item["env_var"] == entry.env_var
            ),
            None,
        )
        if existing is not None:
            return False
        self.config.secrets.append(
            {
                "env_var": entry.env_var,
                "secret_name": entry.secret_name,
            }
        )
        return True

    def _secret_name_for_binding_reference(self, *, env_var: str | None, key: str) -> str:
        if env_var:
            return f"HARNESSIQ_{self._agent_token()}_{self._normalize_token(env_var)}"
        return f"HARNESSIQ_{self._agent_token()}_{self._normalize_token(key)}"

    def _agent_token(self) -> str:
        return self._normalize_token(self.config.agent_name)

    def _missing_binding_message(self, key: str, reason: str | None) -> str:
        detail = reason or f"No credential binding metadata exists for '{key}'."
        return (
            f"{detail} Run the harness credential binding flow first so GCP sync can reuse the repo-local "
            "binding model."
        )

    def _missing_local_fix(self, entry: CredentialEntry) -> str:
        if entry.env_var is None:
            return self._missing_binding_message(entry.key, entry.missing_reason)
        return f"Add '{entry.env_var}' to the repo-local .env file or sync the secret to GCP through another path."

    @staticmethod
    def _normalize_token(value: str) -> str:
        return "".join(character if character.isalnum() else "_" for character in value.strip().upper()).strip("_")

    @staticmethod
    def _resolve_repo_root(path: Path) -> Path:
        resolved = path.expanduser().resolve()
        for candidate in (resolved, *resolved.parents):
            if (candidate / ".git").exists():
                return candidate
        return resolved
