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
