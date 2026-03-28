"""Dedicated CLI commands for the email campaign agent."""

from __future__ import annotations

import argparse

from harnessiq.cli.builders import EmailCliBuilder
from harnessiq.cli.common import (
    add_agent_options,
    add_model_selection_options,
    add_policy_options,
    add_text_or_file_options,
    emit_json,
    format_manifest_parameter_keys,
)
from harnessiq.cli.runners import EmailCliRunner
from harnessiq.shared.email_campaign import EMAIL_HARNESS_MANIFEST


def register_email_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    parser = subparsers.add_parser("email", help="Manage and run the email campaign agent")
    parser.set_defaults(command_handler=lambda args: _print_help(parser))
    email_subparsers = parser.add_subparsers(dest="email_command")

    prepare_parser = email_subparsers.add_parser(
        "prepare",
        help="Create or refresh an email campaign memory folder",
    )
    add_agent_options(
        prepare_parser,
        agent_help="Logical agent name used to resolve the memory folder.",
        memory_root_default="memory/email",
        memory_root_help="Root directory that holds per-agent email memory folders.",
    )
    prepare_parser.set_defaults(command_handler=_handle_prepare)

    configure_parser = email_subparsers.add_parser(
        "configure",
        help="Persist Mongo recipient source, campaign content, and runtime parameters for the email agent",
    )
    add_agent_options(
        configure_parser,
        agent_help="Logical agent name used to resolve the memory folder.",
        memory_root_default="memory/email",
        memory_root_help="Root directory that holds per-agent email memory folders.",
    )
    configure_parser.add_argument("--mongodb-uri-env", help="Env var name holding the MongoDB connection URI.")
    configure_parser.add_argument("--mongodb-database", help="MongoDB database name for the recipient source.")
    configure_parser.add_argument("--mongodb-collection", help="MongoDB collection name for the recipient source.")
    add_text_or_file_options(configure_parser, "source_filter", "MongoDB source filter JSON")
    configure_parser.add_argument(
        "--email-path",
        action="append",
        default=[],
        help="One dotted JSON path used to extract email values from MongoDB documents. Repeat as needed.",
    )
    configure_parser.add_argument(
        "--name-path",
        action="append",
        default=[],
        help="One dotted JSON path used to extract display names from MongoDB documents. Repeat as needed.",
    )
    configure_parser.add_argument("--from-address", help='Resend sender value, for example "HarnessIQ <hello@example.com>".')
    configure_parser.add_argument("--reply-to", help="Optional reply-to email address.")
    configure_parser.add_argument("--subject", help="Email subject template.")
    configure_parser.add_argument(
        "--batch-validation",
        choices=("strict", "permissive"),
        help="Optional Resend x-batch-validation mode.",
    )
    add_text_or_file_options(configure_parser, "html_body", "HTML email body")
    add_text_or_file_options(configure_parser, "text_body", "Plain-text email body")
    add_text_or_file_options(configure_parser, "agent_identity", "Agent identity")
    add_text_or_file_options(configure_parser, "additional_prompt", "Additional prompt")
    configure_parser.add_argument(
        "--runtime-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help=(
            f"Persist a runtime parameter. Supported keys: "
            f"{format_manifest_parameter_keys(EMAIL_HARNESS_MANIFEST, scope='runtime')}."
        ),
    )
    configure_parser.add_argument(
        "--custom-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Persist an open-ended custom parameter as KEY=VALUE. Values are parsed as JSON when possible.",
    )
    configure_parser.set_defaults(command_handler=_handle_configure)

    show_parser = email_subparsers.add_parser(
        "show",
        help="Render the current email campaign state as JSON",
    )
    add_agent_options(
        show_parser,
        agent_help="Logical agent name used to resolve the memory folder.",
        memory_root_default="memory/email",
        memory_root_help="Root directory that holds per-agent email memory folders.",
    )
    show_parser.set_defaults(command_handler=_handle_show)

    run_parser = email_subparsers.add_parser(
        "run",
        help="Run the email campaign agent from persisted memory",
    )
    add_agent_options(
        run_parser,
        agent_help="Logical agent name used to resolve the memory folder.",
        memory_root_default="memory/email",
        memory_root_help="Root directory that holds per-agent email memory folders.",
    )
    add_model_selection_options(run_parser)
    run_parser.add_argument(
        "--runtime-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override a persisted runtime parameter for this run only.",
    )
    run_parser.add_argument(
        "--custom-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override a persisted custom parameter for this run only.",
    )
    run_parser.add_argument("--max-cycles", type=int, help="Optional max cycle count passed to agent.run().")
    add_policy_options(run_parser)
    run_parser.set_defaults(command_handler=_handle_run)

    recipients_parser = email_subparsers.add_parser(
        "get-recipients",
        help="Return the current deduplicated unsent recipient preview for the configured email agent",
    )
    add_agent_options(
        recipients_parser,
        agent_help="Logical agent name used to resolve the memory folder.",
        memory_root_default="memory/email",
        memory_root_help="Root directory that holds per-agent email memory folders.",
    )
    recipients_parser.add_argument("--limit", type=int, help="Optional preview limit applied to returned recipients.")
    recipients_parser.set_defaults(command_handler=_handle_get_recipients)


def _handle_prepare(args: argparse.Namespace) -> int:
    emit_json(
        EmailCliBuilder().prepare(
            agent_name=args.agent,
            memory_root=args.memory_root,
        )
    )
    return 0


def _handle_configure(args: argparse.Namespace) -> int:
    emit_json(
        EmailCliBuilder().configure(
            agent_name=args.agent,
            memory_root=args.memory_root,
            mongodb_uri_env=args.mongodb_uri_env,
            mongodb_database=args.mongodb_database,
            mongodb_collection=args.mongodb_collection,
            source_filter_text=getattr(args, "source_filter_text", None),
            source_filter_file=getattr(args, "source_filter_file", None),
            email_paths=args.email_path,
            name_paths=args.name_path,
            from_address=args.from_address,
            reply_to=args.reply_to,
            subject=args.subject,
            batch_validation=args.batch_validation,
            html_body_text=getattr(args, "html_body_text", None),
            html_body_file=getattr(args, "html_body_file", None),
            text_body_text=getattr(args, "text_body_text", None),
            text_body_file=getattr(args, "text_body_file", None),
            agent_identity_text=getattr(args, "agent_identity_text", None),
            agent_identity_file=getattr(args, "agent_identity_file", None),
            additional_prompt_text=getattr(args, "additional_prompt_text", None),
            additional_prompt_file=getattr(args, "additional_prompt_file", None),
            runtime_assignments=args.runtime_param,
            custom_assignments=args.custom_param,
        )
    )
    return 0


def _handle_show(args: argparse.Namespace) -> int:
    emit_json(
        EmailCliBuilder().show(
            agent_name=args.agent,
            memory_root=args.memory_root,
        )
    )
    return 0


def _handle_run(args: argparse.Namespace) -> int:
    runner = EmailCliRunner()
    emit_json(
        runner.run(
            agent_name=args.agent,
            memory_root=args.memory_root,
            model_factory=args.model_factory,
            model=args.model,
            model_profile=args.model_profile,
            runtime_overrides=runner.parse_runtime_assignments(args.runtime_param),
            custom_overrides=runner.parse_custom_assignments(args.custom_param),
            max_cycles=args.max_cycles,
            approval_policy=args.approval_policy,
            allowed_tools=args.allowed_tools,
            dynamic_tools=args.dynamic_tools,
            dynamic_tool_candidates=args.dynamic_tool_candidates,
            dynamic_tool_top_k=args.dynamic_tool_top_k,
            dynamic_tool_embedding_model=args.dynamic_tool_embedding_model,
        )
    )
    return 0


def _handle_get_recipients(args: argparse.Namespace) -> int:
    emit_json(
        EmailCliBuilder().get_recipients(
            agent_name=args.agent,
            memory_root=args.memory_root,
            limit=args.limit,
        )
    )
    return 0


def _print_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


__all__ = ["register_email_commands"]
