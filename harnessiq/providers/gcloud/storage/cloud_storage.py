"""Raw Cloud Storage provider helpers for GCP-backed HarnessIQ deployments."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from harnessiq.providers.gcloud import commands as cmd
from harnessiq.providers.gcloud.base import BaseGcpProvider
from harnessiq.providers.gcloud.client import GcloudError


class CloudStorageProvider(BaseGcpProvider):
    """Manage buckets and raw object operations without higher-level sync logic."""

    _STATE_ROOT_PREFIX = "runtime-state"

    @property
    def default_bucket_name(self) -> str:
        return f"harnessiq-{self.config.gcp_project_id[:20]}-agent-memory"

    def create_bucket(self, bucket_name: str | None = None) -> str:
        return self.client.run(
            cmd.create_bucket(
                cmd.BucketSpec(
                    bucket_name=bucket_name or self.default_bucket_name,
                    location=self.config.region,
                )
            )
        )

    def read_text(self, gs_uri: str) -> str:
        return self.client.run(cmd.cat_object(gs_uri))

    def write_text(self, gs_uri: str, content: str) -> str:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".txt",
            encoding="utf-8",
            delete=False,
        ) as handle:
            handle.write(content)
            temp_path = Path(handle.name)
        try:
            return self.client.run(cmd.copy_to_gcs(str(temp_path), gs_uri))
        finally:
            if temp_path.exists():
                os.unlink(temp_path)

    def list_objects(self, gs_uri: str) -> list[str]:
        raw = self.client.run(cmd.list_objects(gs_uri))
        return [line.strip() for line in raw.splitlines() if line.strip()]

    def delete_object(self, gs_uri: str) -> str:
        return self.client.run(cmd.delete_object(gs_uri))

    def runtime_state_uri(self, memory_path: str) -> str:
        normalized = memory_path.strip().strip("/")
        if not normalized:
            raise ValueError("memory_path must not be blank.")
        return f"gs://{self.default_bucket_name}/{self._STATE_ROOT_PREFIX}/{normalized}/"

    def sync_memory_from_gcs(self, memory_path: str, local_path: Path | str) -> bool:
        destination = Path(local_path)
        source_uri = self.runtime_state_uri(memory_path)
        if not self._prefix_exists(source_uri):
            return False
        destination.mkdir(parents=True, exist_ok=True)
        self.client.run(
            [
                "storage",
                "rsync",
                source_uri,
                str(destination),
                "--recursive",
            ]
        )
        return True

    def sync_memory_to_gcs(self, memory_path: str, local_path: Path | str) -> bool:
        source = Path(local_path)
        if not source.exists():
            return False
        self.create_bucket()
        self.client.run(
            [
                "storage",
                "rsync",
                str(source),
                self.runtime_state_uri(memory_path),
                "--recursive",
                "--delete-unmatched-destination-objects",
            ]
        )
        return True

    def _prefix_exists(self, gs_uri: str) -> bool:
        try:
            return bool(self.list_objects(gs_uri))
        except GcloudError:
            return False
