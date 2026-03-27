"""Top-level argparse scaffold for the HarnessIQ Google Cloud command family."""

from __future__ import annotations

import argparse


def register_gcloud_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = _add_help_parser(
        subparsers,
        "gcloud",
        help_text="Manage Google Cloud deployment configuration and operations",
        description="Manage Google Cloud deployment configuration and operations",
    )
    gcloud_subparsers = parser.add_subparsers(dest="gcloud_command")

    _add_help_parser(
        gcloud_subparsers,
        "init",
        help_text="Initialize or refresh one GCP deployment config",
    )

    _add_help_parser(
        gcloud_subparsers,
        "health",
        help_text="Inspect GCP deployment prerequisites",
    )

    credentials_parser = _add_help_parser(
        gcloud_subparsers,
        "credentials",
        help_text="Manage repo-local to GCP credential synchronization",
    )
    credential_subparsers = credentials_parser.add_subparsers(dest="gcloud_credentials_command")
    for command_name, help_text in (
        ("status", "Show credential sync status for one GCP config"),
        ("sync", "Sync repo-local credentials into GCP Secret Manager"),
        ("set", "Register one custom credential in GCP Secret Manager"),
        ("remove", "Remove one registered credential from the GCP config"),
        ("check", "Check local GCP authentication prerequisites"),
    ):
        _add_help_parser(credential_subparsers, command_name, help_text=help_text)

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
