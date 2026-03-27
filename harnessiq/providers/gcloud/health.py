"""Health and prerequisite validation for GCP-backed HarnessIQ deployments."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass

from harnessiq.providers.gcloud import commands as cmd
from harnessiq.providers.gcloud.base import BaseGcpProvider
from harnessiq.providers.gcloud.client import GcloudError


@dataclass(slots=True)
class HealthCheckResult:
    """One discrete health-check outcome."""

    name: str
    passed: bool
    message: str
    fix: str | None = None


class HealthProvider(BaseGcpProvider):
    """Validate local auth prerequisites and project readiness checks."""

    REQUIRED_APIS = [
        "run.googleapis.com",
        "artifactregistry.googleapis.com",
        "cloudbuild.googleapis.com",
        "cloudscheduler.googleapis.com",
        "secretmanager.googleapis.com",
        "logging.googleapis.com",
        "monitoring.googleapis.com",
        "storage.googleapis.com",
        "iam.googleapis.com",
    ]

    def check_gcloud_installed(self) -> HealthCheckResult:
        installed = shutil.which("gcloud") is not None
        return HealthCheckResult(
            name="gcloud CLI installed",
            passed=installed,
            message="gcloud CLI found" if installed else "gcloud CLI not found",
            fix=None if installed else "https://cloud.google.com/sdk/docs/install",
        )

    def check_gcloud_auth(self) -> HealthCheckResult:
        try:
            active_account = self.client.run(cmd.list_active_accounts()).strip()
        except GcloudError as exc:
            return HealthCheckResult(
                name="gcloud CLI auth (gcloud auth login)",
                passed=False,
                message=str(exc),
                fix="gcloud auth login",
            )
        return HealthCheckResult(
            name="gcloud CLI auth (gcloud auth login)",
            passed=bool(active_account),
            message=f"Active account: {active_account}" if active_account else "No active CLI account",
            fix=None if active_account else "gcloud auth login",
        )

    def check_adc(self) -> HealthCheckResult:
        adc_paths = [
            os.path.expanduser("~/.config/gcloud/application_default_credentials.json"),
            os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", ""),
        ]
        found = any(path and os.path.exists(path) for path in adc_paths)
        return HealthCheckResult(
            name="Application Default Credentials (ADC)",
            passed=found,
            message="ADC credentials file found"
            if found
            else "ADC not configured — Python client libraries will not authenticate",
            fix=None if found else "gcloud auth application-default login",
        )

    def check_anthropic_key_local(self) -> HealthCheckResult:
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        found = bool(key) and key.startswith("sk-ant-")
        return HealthCheckResult(
            name="ANTHROPIC_API_KEY (local)",
            passed=found,
            message="Found in environment" if found else "Not found in environment",
            fix=None if found else "export ANTHROPIC_API_KEY=sk-ant-...",
        )

    def check_apis_enabled(self) -> list[HealthCheckResult]:
        results: list[HealthCheckResult] = []
        for api in self.REQUIRED_APIS:
            try:
                enabled_name = self.client.run(cmd.is_service_enabled(api)).strip()
                enabled = enabled_name == api
                results.append(
                    HealthCheckResult(
                        name=f"API: {api}",
                        passed=enabled,
                        message="Enabled" if enabled else "NOT enabled",
                        fix=None
                        if enabled
                        else f"gcloud services enable {api} --project={self.config.gcp_project_id}",
                    )
                )
            except GcloudError as exc:
                results.append(
                    HealthCheckResult(
                        name=f"API: {api}",
                        passed=False,
                        message=str(exc),
                    )
                )
        return results

    def check_service_account_secret_access(self) -> HealthCheckResult:
        service_account = self.config.service_account_email
        if not service_account:
            try:
                project_number = self.client.run(cmd.get_project_number(self.config.gcp_project_id)).strip()
            except GcloudError as exc:
                return HealthCheckResult(
                    name="Service account Secret Manager access",
                    passed=False,
                    message=str(exc),
                )
            service_account = f"{project_number}-compute@developer.gserviceaccount.com"

        try:
            policy = self.client.run_json(cmd.get_iam_policy(self.config.gcp_project_id))
        except GcloudError as exc:
            return HealthCheckResult(
                name="Service account Secret Manager access",
                passed=False,
                message=str(exc),
            )

        member = f"serviceAccount:{service_account}"
        has_access = any(
            binding.get("role") == "roles/secretmanager.secretAccessor"
            and member in binding.get("members", [])
            for binding in policy.get("bindings", [])
        )
        return HealthCheckResult(
            name="Service account Secret Manager access",
            passed=has_access,
            message=f"{service_account} has secretAccessor"
            if has_access
            else f"{service_account} is missing roles/secretmanager.secretAccessor",
            fix=None
            if has_access
            else (
                f"gcloud projects add-iam-policy-binding {self.config.gcp_project_id} "
                f"--member=serviceAccount:{service_account} "
                "--role=roles/secretmanager.secretAccessor"
            ),
        )

    def validate_all(self, fail_fast: bool = False) -> list[HealthCheckResult]:
        results: list[HealthCheckResult] = []

        def _record(result: HealthCheckResult) -> None:
            results.append(result)
            if fail_fast and not result.passed:
                message = f"Health check failed: {result.name}\n{result.message}"
                if result.fix:
                    message += f"\nFix: {result.fix}"
                raise RuntimeError(message)

        _record(self.check_gcloud_installed())
        _record(self.check_gcloud_auth())
        _record(self.check_adc())
        _record(self.check_anthropic_key_local())
        _record(self.check_service_account_secret_access())
        for result in self.check_apis_enabled():
            _record(result)
        return results
