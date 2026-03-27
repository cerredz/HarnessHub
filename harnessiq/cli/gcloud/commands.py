"""Top-level argparse scaffold for the HarnessIQ Google Cloud command family."""

from __future__ import annotations

import argparse


def register_gcloud_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser(
        "gcloud",
        help="Manage Google Cloud deployment configuration and operations",
        description="Manage Google Cloud deployment configuration and operations",
    )
    parser.set_defaults(command_handler=lambda args: _print_help(parser))
    gcloud_subparsers = parser.add_subparsers(dest="gcloud_command")

    init_parser = gcloud_subparsers.add_parser("init", help="Initialize or refresh one GCP deployment config")
    init_parser.set_defaults(command_handler=lambda args: _print_help(init_parser))

    health_parser = gcloud_subparsers.add_parser("health", help="Inspect GCP deployment prerequisites")
    health_parser.set_defaults(command_handler=lambda args: _print_help(health_parser))

    credentials_parser = gcloud_subparsers.add_parser(
        "credentials",
        help="Manage repo-local to GCP credential synchronization",
    )
    credentials_parser.set_defaults(command_handler=lambda args: _print_help(credentials_parser))
    credential_subparsers = credentials_parser.add_subparsers(dest="gcloud_credentials_command")
    for command_name, help_text in (
        ("status", "Show credential sync status for one GCP config"),
        ("sync", "Sync repo-local credentials into GCP Secret Manager"),
        ("set", "Register one custom credential in GCP Secret Manager"),
        ("remove", "Remove one registered credential from the GCP config"),
        ("check", "Check local GCP authentication prerequisites"),
    ):
        subparser = credential_subparsers.add_parser(command_name, help=help_text)
        subparser.set_defaults(command_handler=lambda args, parser=subparser: _print_help(parser))

    build_parser = gcloud_subparsers.add_parser("build", help="Build and publish the configured container image")
    build_parser.set_defaults(command_handler=lambda args: _print_help(build_parser))

    deploy_parser = gcloud_subparsers.add_parser("deploy", help="Deploy or update the configured Cloud Run job")
    deploy_parser.set_defaults(command_handler=lambda args: _print_help(deploy_parser))

    schedule_parser = gcloud_subparsers.add_parser("schedule", help="Create or update the configured scheduler job")
    schedule_parser.set_defaults(command_handler=lambda args: _print_help(schedule_parser))

    execute_parser = gcloud_subparsers.add_parser("execute", help="Trigger an immediate Cloud Run job execution")
    execute_parser.set_defaults(command_handler=lambda args: _print_help(execute_parser))

    logs_parser = gcloud_subparsers.add_parser("logs", help="Read Cloud Run execution logs")
    logs_parser.set_defaults(command_handler=lambda args: _print_help(logs_parser))

    cost_parser = gcloud_subparsers.add_parser("cost", help="Estimate the configured monthly GCP deployment cost")
    cost_parser.set_defaults(command_handler=lambda args: _print_help(cost_parser))


def _print_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


__all__ = ["register_gcloud_commands"]
