"""Artifact Registry provider backed by pure gcloud command builders."""

from __future__ import annotations

from harnessiq.providers.gcloud import commands as cmd
from harnessiq.providers.gcloud.base import BaseGcpProvider
from harnessiq.providers.gcloud.client import GcloudError


class ArtifactRegistryProvider(BaseGcpProvider):
    """Manage the Artifact Registry repository and build flow for one agent."""

    @property
    def repository_name(self) -> str:
        return self.config.artifact_repository

    @property
    def repository_host(self) -> str:
        return f"{self.config.region}-docker.pkg.dev"

    @property
    def repository_path(self) -> str:
        return f"{self.repository_host}/{self.config.gcp_project_id}/{self.repository_name}"

    def repository_exists(self) -> bool:
        try:
            self.client.run_json(
                cmd.describe_repository(self.repository_name, self.config.region)
            )
            return True
        except GcloudError as exc:
            if self._is_not_found_error(exc):
                return False
            raise

    @staticmethod
    def _is_not_found_error(error: GcloudError) -> bool:
        detail = f"{error.stderr}\n{error.stdout}".lower()
        return "not found" in detail or "was not found" in detail

    def ensure_repository(self) -> None:
        if self.repository_exists():
            return
        self.client.run(
            cmd.create_repository(self.repository_name, self.config.region)
        )

    def configure_docker_auth(self) -> str:
        return self.client.run(cmd.configure_docker_auth(self.config.region))

    def build_image(self, source_dir: str = ".") -> str:
        self.ensure_repository()
        return self.client.run(cmd.submit_build(self.config.image_url, source_dir))

    def list_images(self) -> list[dict]:
        return self.client.run_json(
            cmd.list_images(self.repository_path, self.config.region)
        )

    def delete_image(self, image_uri: str | None = None) -> str:
        return self.client.run(cmd.delete_image(image_uri or self.config.image_url))
