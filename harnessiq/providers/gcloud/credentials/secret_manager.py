"""Secret Manager provider backed by pure gcloud command builders."""

from __future__ import annotations

from typing import Any

from harnessiq.providers.gcloud import commands as cmd
from harnessiq.providers.gcloud.base import BaseGcpProvider
from harnessiq.providers.gcloud.client import GcloudError


class SecretManagerProvider(BaseGcpProvider):
    """Manage deployment-time secrets without embedding values in commands."""

    def secret_exists(self, secret_name: str) -> bool:
        try:
            self.client.run_json(cmd.describe_secret(secret_name))
            return True
        except GcloudError as exc:
            if self._is_not_found_error(exc):
                return False
            raise

    def create_secret(self, secret_name: str, *, replication: str = "automatic") -> str:
        spec = cmd.SecretSpec(
            secret_name=secret_name,
            project_id=self.config.gcp_project_id,
            replication=replication,
        )
        return self.client.run(cmd.create_secret(spec))

    def add_secret_version(self, secret_name: str, value: str) -> str:
        return self.client.run(cmd.add_secret_version(secret_name), input_text=value)

    def set_secret(self, secret_name: str, value: str, *, replication: str = "automatic") -> str:
        if not self.secret_exists(secret_name):
            self.create_secret(secret_name, replication=replication)
        return self.add_secret_version(secret_name, value)

    def rotate_secret(self, secret_name: str, value: str) -> str:
        return self.add_secret_version(secret_name, value)

    def get_secret(self, secret_name: str) -> dict[str, Any]:
        return self.client.run_json(cmd.describe_secret(secret_name))

    def list_secrets(self) -> list[dict[str, Any]]:
        return self.client.run_json(cmd.list_secrets())

    def list_secret_versions(self, secret_name: str) -> list[dict[str, Any]]:
        return self.client.run_json(cmd.list_secret_versions(secret_name))

    def delete_secret(self, secret_name: str) -> str:
        return self.client.run(cmd.delete_secret(secret_name))

    @staticmethod
    def _is_not_found_error(error: GcloudError) -> bool:
        detail = f"{error.stderr}\n{error.stdout}".lower()
        return "not found" in detail or "was not found" in detail
