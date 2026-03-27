"""Argparse-backed Google Cloud CLI commands for provider-backed operations."""

from __future__ import annotations

import argparse
from typing import Any

from harnessiq.cli.common import emit_json
from harnessiq.providers.gcloud import GcpAgentConfig, GcpContext


def register_gcloud_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = _add_help_parser(
        subparsers,
        "gcloud",
        help_text="Manage Google Cloud deployment configuration and operations",
        description="Manage Google Cloud deployment configuration and operations",
    )
    gcloud_subparsers = parser.add_subparsers(dest="gcloud_command")

    init_parser = _add_help_parser(
        gcloud_subparsers,
        "init",
        help_text="Initialize or refresh one GCP deployment config",
    )
    _add_init_arguments(init_parser)
    init_parser.set_defaults(command_handler=_handle_init)

    health_parser = _add_help_parser(
        gcloud_subparsers,
        "health",
        help_text="Inspect GCP deployment prerequisites",
    )
    _add_agent_argument(health_parser)
    health_parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Raise on the first failed health check instead of returning the full result set.",
    )
    health_parser.set_defaults(command_handler=_handle_health)

    credentials_parser = _add_help_parser(
        gcloud_subparsers,
        "credentials",
        help_text="Manage repo-local to GCP credential synchronization",
    )
    credential_subparsers = credentials_parser.add_subparsers(dest="gcloud_credentials_command")

    status_parser = _add_help_parser(
        credential_subparsers,
        "status",
        help_text="Show credential sync status for one GCP config",
    )
    _add_agent_argument(status_parser)
    status_parser.set_defaults(command_handler=_handle_credentials_status)

    sync_parser = _add_help_parser(
        credential_subparsers,
        "sync",
        help_text="Sync repo-local credentials into GCP Secret Manager",
    )
    _add_agent_argument(sync_parser)
    sync_parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Disable prompts and fail when required credentials are missing locally.",
    )
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the sync result without mutating Secret Manager or the saved config.",
    )
    sync_parser.set_defaults(command_handler=_handle_credentials_sync)

    set_parser = _add_help_parser(
        credential_subparsers,
        "set",
        help_text="Register one custom credential in GCP Secret Manager",
    )
    _add_agent_argument(set_parser)
    set_parser.add_argument("--env-var", required=True, help="Runtime environment variable name.")
    set_parser.add_argument("--secret-name", required=True, help="Secret Manager secret name.")
    set_parser.add_argument(
        "--value",
        help="Optional inline value. Prefer the repo-local .env file or an interactive prompt for sensitive values.",
    )
    set_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the planned registration without mutating Secret Manager or the saved config.",
    )
    set_parser.set_defaults(command_handler=_handle_credentials_set)

    remove_parser = _add_help_parser(
        credential_subparsers,
        "remove",
        help_text="Remove one registered credential from the GCP config",
    )
    _add_agent_argument(remove_parser)
    remove_parser.add_argument("--env-var", required=True, help="Registered runtime environment variable name.")
    remove_parser.add_argument(
        "--delete-from-gcp",
        action="store_true",
        help="Also delete the backing secret from Secret Manager.",
    )
    remove_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the planned removal without mutating Secret Manager or the saved config.",
    )
    remove_parser.set_defaults(command_handler=_handle_credentials_remove)

    check_parser = _add_help_parser(
        credential_subparsers,
        "check",
        help_text="Check local GCP authentication prerequisites",
    )
    check_parser.set_defaults(command_handler=_handle_credentials_check)

    _add_help_parser(
        gcloud_subparsers,
        "build",
        help_text="Build and publish the configured container image",
    )

    _add_help_parser(
        gcloud_subparsers,
        "deploy",
        help_text="Deploy or update the configured Cloud Run job",
    )

    _add_help_parser(
        gcloud_subparsers,
        "schedule",
        help_text="Create or update the configured scheduler job",
    )

    _add_help_parser(
        gcloud_subparsers,
        "execute",
        help_text="Trigger an immediate Cloud Run job execution",
    )

    _add_help_parser(
        gcloud_subparsers,
        "logs",
        help_text="Read Cloud Run execution logs",
    )

    _add_help_parser(
        gcloud_subparsers,
        "cost",
        help_text="Estimate the configured monthly GCP deployment cost",
    )


def _handle_init(args: argparse.Namespace) -> int:
    context = _create_init_context(args)
    health_results: list[dict[str, Any]] = []
    if not args.skip_health:
        health_results = _serialize_health_results(context.health.validate_all(fail_fast=args.fail_fast))

    config_path = None
    if not args.dry_run:
        config_path = str(context.config.save())

    credentials: list[dict[str, Any]] = []
    if not args.skip_credential_sync:
        credentials = [
            entry.status_dict()
            for entry in context.credentials.bridge.sync(
                interactive=not args.non_interactive,
                dry_run=args.dry_run,
            )
        ]
        if not args.dry_run:
            config_path = str(GcpAgentConfig.config_path_for(context.config.agent_name))

    payload = _context_payload(context)
    payload.update(
        {
            "config_path": config_path,
            "credentials": credentials,
            "dry_run": args.dry_run,
            "health": health_results,
            "skip_credential_sync": args.skip_credential_sync,
            "skip_health": args.skip_health,
            "status": _init_status(args, health_results),
        }
    )
    emit_json(payload)
    return 0


def _handle_health(args: argparse.Namespace) -> int:
    context = _load_context(args.agent)
    results = _serialize_health_results(context.health.validate_all(fail_fast=args.fail_fast))
    payload = _context_payload(context)
    payload.update(
        {
            "health": results,
            "status": _health_status(results),
        }
    )
    emit_json(payload)
    return 0


def _handle_credentials_status(args: argparse.Namespace) -> int:
    context = _load_context(args.agent)
    credentials = [entry.status_dict() for entry in context.credentials.bridge.status()]
    payload = _context_payload(context)
    payload.update(
        {
            "credentials": credentials,
            "status": "ok",
        }
    )
    emit_json(payload)
    return 0


def _handle_credentials_sync(args: argparse.Namespace) -> int:
    context = _load_context(args.agent, dry_run=args.dry_run)
    credentials = [
        entry.status_dict()
        for entry in context.credentials.bridge.sync(
            interactive=not args.non_interactive,
            dry_run=args.dry_run,
        )
    ]
    payload = _context_payload(context)
    payload.update(
        {
            "config_path": str(GcpAgentConfig.config_path_for(context.config.agent_name)),
            "credentials": credentials,
            "dry_run": args.dry_run,
            "status": "synced" if not args.dry_run else "dry_run",
        }
    )
    emit_json(payload)
    return 0


def _handle_credentials_set(args: argparse.Namespace) -> int:
    context = _load_context(args.agent, dry_run=args.dry_run)
    context.credentials.bridge.add_custom(
        args.env_var,
        args.secret_name,
        value=args.value,
        dry_run=args.dry_run,
    )
    payload = _context_payload(context)
    payload.update(
        {
            "config_path": str(GcpAgentConfig.config_path_for(context.config.agent_name)),
            "dry_run": args.dry_run,
            "env_var": args.env_var,
            "secret_name": args.secret_name,
            "status": "registered" if not args.dry_run else "dry_run",
        }
    )
    emit_json(payload)
    return 0


def _handle_credentials_remove(args: argparse.Namespace) -> int:
    context = _load_context(args.agent, dry_run=args.dry_run)
    context.credentials.bridge.remove(
        args.env_var,
        delete_from_gcp=args.delete_from_gcp,
        dry_run=args.dry_run,
    )
    payload = _context_payload(context)
    payload.update(
        {
            "config_path": str(GcpAgentConfig.config_path_for(context.config.agent_name)),
            "delete_from_gcp": args.delete_from_gcp,
            "dry_run": args.dry_run,
            "env_var": args.env_var,
            "status": "removed" if not args.dry_run else "dry_run",
        }
    )
    emit_json(payload)
    return 0


def _handle_credentials_check(args: argparse.Namespace) -> int:
    del args
    provider = _build_local_health_provider()
    results = _serialize_health_results(
        [
            provider.check_gcloud_installed(),
            provider.check_gcloud_auth(),
            provider.check_adc(),
            provider.check_anthropic_key_local(),
        ]
    )
    emit_json(
        {
            "health": results,
            "scope": "credentials_auth",
            "status": _health_status(results),
        }
    )
    return 0


def _create_init_context(args: argparse.Namespace) -> GcpContext:
    kwargs = {
        "artifact_repository": args.artifact_repository,
        "cpu": args.cpu,
        "image_name": args.image_name,
        "image_tag": args.image_tag,
        "job_name": args.job_name,
        "manifest_id": args.manifest_id,
        "max_retries": args.max_retries,
        "memory": args.memory,
        "parallelism": args.parallelism,
        "schedule_cron": args.schedule_cron,
        "scheduler_job_name": args.scheduler_job_name,
        "service_account_email": args.service_account_email,
        "task_count": args.task_count,
        "task_timeout_seconds": args.task_timeout_seconds,
        "timezone": args.timezone,
    }
    filtered_kwargs = {key: value for key, value in kwargs.items() if value is not None}
    return GcpContext.from_init(
        agent_name=args.agent,
        project_id=args.project_id,
        region=args.region,
        dry_run=args.dry_run,
        **filtered_kwargs,
    )


def _load_context(agent_name: str, *, dry_run: bool = False) -> GcpContext:
    return GcpContext.from_config(agent_name, dry_run=dry_run)


def _build_local_health_provider():
    return GcpContext.from_init(
        agent_name="local-auth-check",
        project_id="local-project",
        region="us-central1",
        dry_run=False,
    ).health


def _serialize_health_results(results: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "fix": getattr(result, "fix", None),
            "message": result.message,
            "name": result.name,
            "passed": result.passed,
        }
        for result in results
    ]


def _context_payload(context: GcpContext) -> dict[str, Any]:
    return {
        "agent": context.config.agent_name,
        "project_id": context.config.gcp_project_id,
        "region": context.config.region,
    }


def _health_status(results: list[dict[str, Any]]) -> str:
    return "healthy" if all(result["passed"] for result in results) else "unhealthy"


def _init_status(args: argparse.Namespace, health_results: list[dict[str, Any]]) -> str:
    if args.dry_run:
        return "dry_run"
    if health_results and _health_status(health_results) != "healthy":
        return "initialized_with_failures"
    return "initialized"


def _add_init_arguments(parser: argparse.ArgumentParser) -> None:
    _add_agent_argument(parser)
    parser.add_argument("--project-id", required=True, help="Target Google Cloud project id.")
    parser.add_argument("--region", required=True, help="Primary Google Cloud region for the deployment.")
    parser.add_argument(
        "--manifest-id",
        help="Optional harness manifest id used to connect repo-local credential bindings.",
    )
    parser.add_argument(
        "--artifact-repository",
        help="Artifact Registry repository name. Defaults to the provider-layer default when omitted.",
    )
    parser.add_argument("--image-name", help="Container image name override.")
    parser.add_argument("--image-tag", help="Container image tag override.")
    parser.add_argument("--job-name", help="Cloud Run job name override.")
    parser.add_argument("--scheduler-job-name", help="Cloud Scheduler job name override.")
    parser.add_argument("--service-account-email", help="Optional Cloud Run service account email.")
    parser.add_argument("--cpu", help="Cloud Run CPU allocation, for example 1 or 2.")
    parser.add_argument("--memory", help="Cloud Run memory allocation, for example 512Mi or 1Gi.")
    parser.add_argument(
        "--task-timeout-seconds",
        type=int,
        help="Task timeout in seconds used by the Cloud Run job.",
    )
    parser.add_argument("--max-retries", type=int, help="Maximum Cloud Run task retries.")
    parser.add_argument("--parallelism", type=int, help="Parallel task limit. Omit to keep the config default.")
    parser.add_argument("--task-count", type=int, help="Number of tasks per execution.")
    parser.add_argument("--schedule-cron", help="Optional Cloud Scheduler cron expression.")
    parser.add_argument("--timezone", help="Scheduler timezone override.")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Disable prompts when syncing credentials during init.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render the init result without writing config or mutating GCP resources.",
    )
    parser.add_argument(
        "--skip-health",
        action="store_true",
        help="Skip the prerequisite validation step.",
    )
    parser.add_argument(
        "--skip-credential-sync",
        action="store_true",
        help="Skip repo-local credential synchronization during init.",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Raise on the first failed health check instead of returning the full result set.",
    )


def _add_agent_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--agent", required=True, help="Logical agent name for the saved GCP deployment config.")


def _add_help_parser(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    name: str,
    *,
    help_text: str,
    description: str | None = None,
) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(
        name,
        help=help_text,
        description=description,
    )
    parser.set_defaults(command_handler=lambda args, parser=parser: _print_help(parser))
    return parser


def _print_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


__all__ = ["register_gcloud_commands"]
