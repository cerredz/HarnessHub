"""Deterministic billing heuristics for one GCP-backed agent deployment."""

from __future__ import annotations

from dataclasses import dataclass

from harnessiq.providers.gcloud.base import BaseGcpProvider


@dataclass(slots=True)
class CostEstimate:
    """Approximate monthly deployment cost under explicit pricing assumptions."""

    cloud_run_per_run_usd: float
    cloud_run_monthly_usd: float
    scheduler_monthly_usd: float
    secret_manager_monthly_usd: float
    artifact_registry_monthly_usd: float
    total_monthly_usd: float
    assumptions: list[str]


class BillingProvider(BaseGcpProvider):
    """Estimate approximate monthly GCP cost from one saved agent config."""

    def estimate_monthly_cost(self) -> CostEstimate:
        cpu = float(self.config.cpu)
        memory_gib = self._parse_memory_gib(self.config.memory)
        timeout_seconds = self.config.task_timeout_seconds

        cpu_cost_per_run = cpu * timeout_seconds * 0.00002400
        memory_cost_per_run = memory_gib * timeout_seconds * 0.00000250
        per_run = cpu_cost_per_run + memory_cost_per_run

        monthly_runs = self._estimate_monthly_runs(self.config.schedule_cron)
        cloud_run_monthly = per_run * monthly_runs
        scheduler_monthly = 0.10 if self.config.schedule_cron else 0.0

        secret_count = len(self.config.secrets)
        secret_manager_monthly = (secret_count * 0.06) + (
            monthly_runs * secret_count * 0.06 / 10000
        )

        artifact_registry_monthly = 0.05
        total = (
            cloud_run_monthly
            + scheduler_monthly
            + secret_manager_monthly
            + artifact_registry_monthly
        )

        return CostEstimate(
            cloud_run_per_run_usd=round(per_run, 6),
            cloud_run_monthly_usd=round(cloud_run_monthly, 4),
            scheduler_monthly_usd=round(scheduler_monthly, 4),
            secret_manager_monthly_usd=round(secret_manager_monthly, 4),
            artifact_registry_monthly_usd=round(artifact_registry_monthly, 4),
            total_monthly_usd=round(total, 4),
            assumptions=[
                f"CPU: {cpu} vCPU, Memory: {self.config.memory}",
                f"Task timeout used fully: {timeout_seconds}s per run",
                f"Monthly runs: {monthly_runs} (from schedule: {self.config.schedule_cron or 'manual only'})",
                f"Secrets: {secret_count}",
                "Region: us-central1 Tier 1 pricing",
                "Prices current as of 2026; verify against live GCP pricing before budgeting decisions.",
            ],
        )

    @staticmethod
    def _parse_memory_gib(memory: str) -> float:
        if memory.endswith("Gi"):
            return float(memory[:-2])
        if memory.endswith("Mi"):
            return float(memory[:-2]) / 1024
        return 0.5

    @staticmethod
    def _estimate_monthly_runs(cron: str | None) -> int:
        if not cron:
            return 0
        parts = cron.split()
        if len(parts) != 5:
            return 30
        _, hour, *_ = parts
        if hour.startswith("*/"):
            interval = int(hour[2:])
            return int((24 / interval) * 30)
        if hour == "*":
            return 24 * 30
        return 30
