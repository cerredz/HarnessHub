"""IAM provider backed by pure gcloud command builders."""

from __future__ import annotations

from harnessiq.providers.gcloud import commands as cmd
from harnessiq.providers.gcloud.base import BaseGcpProvider
from harnessiq.providers.gcloud.client import GcloudError


REQUIRED_ROLES = [
    "roles/secretmanager.secretAccessor",
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/storage.objectAdmin",
    "roles/artifactregistry.reader",
]


class IamProvider(BaseGcpProvider):
    """Manage the service account used by one GCP-backed agent deployment."""

    @property
    def service_account_email(self) -> str:
        if self.config.service_account_email:
            return self.config.service_account_email
        project_number = self.client.run(
            cmd.describe_project(self.config.gcp_project_id, value_field="projectNumber")
        ).strip()
        return f"{project_number}-compute@developer.gserviceaccount.com"

    def create_service_account(
        self,
        sa_name: str = "harnessiq-runner",
        display_name: str = "HarnessIQ Cloud Run Runner",
    ) -> str:
        spec = cmd.ServiceAccountSpec(
            sa_id=sa_name,
            project_id=self.config.gcp_project_id,
            display_name=display_name,
        )
        sa_email = f"{sa_name}@{self.config.gcp_project_id}.iam.gserviceaccount.com"
        try:
            self.client.run(cmd.create_service_account(spec))
        except GcloudError as exc:
            if "already exists" not in f"{exc.stderr}\n{exc.stdout}".lower():
                raise
        self.config.service_account_email = sa_email
        self.config.save()
        return sa_email

    def grant_required_roles(self, sa_email: str | None = None) -> None:
        target = sa_email or self.service_account_email
        for role in REQUIRED_ROLES:
            self.client.run(
                cmd.add_iam_binding(
                    cmd.IamBinding(
                        project_id=self.config.gcp_project_id,
                        member=f"serviceAccount:{target}",
                        role=role,
                    )
                )
            )

    def describe_service_account(self) -> dict:
        return self.client.run_json(cmd.describe_service_account(self.service_account_email))

    def list_granted_roles(self) -> list[str]:
        policy = self.client.run_json(cmd.get_iam_policy(self.config.gcp_project_id))
        member = f"serviceAccount:{self.service_account_email}"
        return [
            binding["role"]
            for binding in policy.get("bindings", [])
            if member in binding.get("members", [])
        ]

    def missing_roles(self) -> list[str]:
        granted = set(self.list_granted_roles())
        return [role for role in REQUIRED_ROLES if role not in granted]
