"""CLI commands for bundled master prompt discovery and retrieval."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from harnessiq.agents import AgentRuntimeConfig
from harnessiq.cli.common import emit_json, load_factory, resolve_repo_root
from harnessiq.master_prompts import get_prompt, get_prompt_text, list_prompt_keys, list_prompts
from harnessiq.master_prompts.session_injection import (
    activate_prompt_session,
    clear_prompt_session,
    get_active_prompt_session,
)
from harnessiq.shared.harness_manifests import get_harness_manifest


def register_master_prompt_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    prompts_parser = subparsers.add_parser("prompts", help="Inspect bundled master prompts")
    prompts_parser.set_defaults(command_handler=lambda args: _print_help(prompts_parser))
    prompts_subparsers = prompts_parser.add_subparsers(dest="prompts_command")

    list_parser = prompts_subparsers.add_parser("list", help="List bundled master prompts")
    list_parser.set_defaults(command_handler=_handle_list)

    search_parser = prompts_subparsers.add_parser("search", help="Search bundled master prompts")
    search_parser.add_argument("query", help="Case-insensitive substring matched against key, title, and description.")
    search_parser.set_defaults(command_handler=_handle_search)

    show_parser = prompts_subparsers.add_parser("show", help="Render one bundled master prompt as JSON")
    show_parser.add_argument("key", help="Prompt key, derived from the prompt filename.")
    show_parser.set_defaults(command_handler=_handle_show)

    text_parser = prompts_subparsers.add_parser("text", help="Print the raw prompt text for one prompt")
    text_parser.add_argument("key", help="Prompt key, derived from the prompt filename.")
    text_parser.set_defaults(command_handler=_handle_text)

    activate_parser = prompts_subparsers.add_parser(
        "activate",
        help="Activate one bundled prompt as always-on project session context for Claude Code and Codex",
    )
    activate_parser.add_argument("key", help="Prompt key, derived from the prompt filename.")
    activate_parser.add_argument(
        "--repo-root",
        default=".",
        help="Project path used to resolve the repo root for generated instruction files.",
    )
    activate_parser.set_defaults(command_handler=_handle_activate)

    current_parser = prompts_subparsers.add_parser(
        "current",
        help="Show the currently active project-scoped master prompt, if any",
    )
    current_parser.add_argument(
        "--repo-root",
        default=".",
        help="Project path used to resolve the repo root for generated instruction files.",
    )
    current_parser.set_defaults(command_handler=_handle_current)

    clear_parser = prompts_subparsers.add_parser(
        "clear",
        help="Remove generated Claude Code and Codex prompt injection overlays",
    )
    clear_parser.add_argument(
        "--repo-root",
        default=".",
        help="Project path used to resolve the repo root for generated instruction files.",
    )
    clear_parser.set_defaults(command_handler=_handle_clear)

    build_parser = prompts_subparsers.add_parser(
        "build",
        help="Build the complete assembled prompt for a configured harness",
    )
    build_parser.add_argument(
        "--agent",
        required=True,
        help="Harness manifest id, runtime agent name, or CLI command (for example leads or research-sweep).",
    )
    add_prompt_render_arguments(build_parser)
    build_parser.add_argument(
        "--out",
        help="Write the rendered prompt bundle to a file instead of stdout.",
    )
    build_parser.add_argument(
        "--memory-path",
        help="Optional memory path used to load an existing configured harness state.",
    )
    build_parser.set_defaults(command_handler=_handle_build_prompt)


def _handle_list(args: argparse.Namespace) -> int:
    del args
    prompts = list_prompts()
    emit_json(
        {
            "count": len(prompts),
            "keys": list_prompt_keys(),
            "prompts": [_prompt_payload(prompt) for prompt in prompts],
        }
    )
    return 0


def _handle_search(args: argparse.Namespace) -> int:
    needle = args.query.strip().lower()
    prompts = [
        prompt
        for prompt in list_prompts()
        if needle in prompt.key.lower()
        or needle in prompt.title.lower()
        or needle in prompt.description.lower()
    ]
    emit_json(
        {
            "count": len(prompts),
            "keys": [prompt.key for prompt in prompts],
            "prompts": [_prompt_payload(prompt) for prompt in prompts],
            "query": args.query,
        }
    )
    return 0


def _handle_show(args: argparse.Namespace) -> int:
    prompt = get_prompt(args.key)
    emit_json(
        {
            "prompt": {
                "key": prompt.key,
                "title": prompt.title,
                "description": prompt.description,
                "prompt": prompt.prompt,
            }
        }
    )
    return 0


def _handle_text(args: argparse.Namespace) -> int:
    print(get_prompt_text(args.key))
    return 0


def _handle_activate(args: argparse.Namespace) -> int:
    activation = activate_prompt_session(args.key, repo_root=resolve_repo_root(args.repo_root))
    emit_json(activation.to_payload())
    return 0


def _handle_current(args: argparse.Namespace) -> int:
    repo_root = resolve_repo_root(args.repo_root)
    activation = get_active_prompt_session(repo_root=repo_root)
    if activation is None:
        emit_json(
            {
                "active": False,
                "prompt": None,
                "files": {
                    "claude": repo_root / ".claude" / "CLAUDE.md",
                    "codex": repo_root / "AGENTS.override.md",
                    "state": repo_root / ".harnessiq" / "master_prompt_session" / "active_prompt.json",
                },
            }
        )
        return 0
    emit_json(activation.to_payload())
    return 0


def _handle_clear(args: argparse.Namespace) -> int:
    emit_json(clear_prompt_session(repo_root=resolve_repo_root(args.repo_root)))
    return 0


def _handle_build_prompt(args: argparse.Namespace) -> int:
    manifest = get_harness_manifest(args.agent)
    out_path = getattr(args, "out", None)
    output = render_prompt_bundle_for_manifest(
        manifest=manifest,
        memory_path=getattr(args, "memory_path", None),
        args=args,
    )
    if out_path:
        Path(out_path).write_text(output, encoding="utf-8")
        print(f"Written to {out_path}")
        return 0
    print(output)
    return 0


def _print_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


def _prompt_payload(prompt) -> dict[str, str]:
    return {
        "key": prompt.key,
        "title": prompt.title,
        "description": prompt.description,
    }


def build_prompt_bundle_for_manifest(
    *,
    manifest,
    memory_path: str | None = None,
    template: bool = False,
):
    """Instantiate one harness in prompt-inspection mode and build its bundle."""
    agent = _build_prompt_agent(manifest=manifest, memory_path=memory_path)
    return agent.build_master_prompt(template=template)


def render_prompt_bundle_for_manifest(
    *,
    manifest,
    memory_path: str | None,
    args: argparse.Namespace,
) -> str:
    """Build and render one prompt bundle for a configured harness."""
    bundle = build_prompt_bundle_for_manifest(
        manifest=manifest,
        memory_path=memory_path,
        template=getattr(args, "template", False),
    )
    return format_prompt_bundle_output(bundle=bundle, args=args)


def add_prompt_render_arguments(parser: argparse.ArgumentParser) -> None:
    """Register shared CLI flags for prompt rendering surfaces."""
    parser.add_argument(
        "--format",
        choices=("text", "json", "markdown"),
        default="text",
        help="Output format for the assembled prompt bundle.",
    )
    parser.add_argument(
        "--template",
        action="store_true",
        help="Replace live runtime values with structural placeholders.",
    )
    parser.add_argument(
        "--no-labels",
        action="store_true",
        help="Render parameter sections without visible section headers.",
    )
    parser.add_argument(
        "--system-only",
        action="store_true",
        help="Print only the system prompt component.",
    )
    parser.add_argument(
        "--sections-only",
        action="store_true",
        help="Print only the parameter sections component.",
    )


def format_prompt_bundle_output(*, bundle, args: argparse.Namespace) -> str:
    """Render one built prompt bundle according to CLI flags."""
    fmt = getattr(args, "format", "text")
    system_only = bool(getattr(args, "system_only", False))
    sections_only = bool(getattr(args, "sections_only", False))
    no_labels = bool(getattr(args, "no_labels", False))

    if fmt == "json":
        payload: dict[str, Any] = {
            "agent_name": bundle.agent_name,
            "layer_count": bundle.layer_count,
            "built_at_reset": bundle.built_at_reset,
            "is_template": bundle.is_template,
        }
        if not sections_only:
            payload["system_prompt"] = bundle.system_prompt
        if not system_only:
            payload["parameter_sections"] = [
                {"title": section.title, "content": section.content}
                for section in bundle.parameter_sections
            ]
        return json.dumps(payload, indent=2)

    if system_only:
        return bundle.render_system_prompt_only()
    if sections_only:
        return bundle.render_parameter_block()
    return bundle.render(labeled=not no_labels)


def _build_prompt_agent(*, manifest, memory_path: str | None = None):
    agent_factory = load_factory(manifest.import_path)
    runtime_config = AgentRuntimeConfig(include_default_output_sink=False)
    kwargs: dict[str, Any] = {
        "model": _null_model(),
        "runtime_config": runtime_config,
    }
    if memory_path is not None:
        kwargs["memory_path"] = memory_path
    kwargs.update(_prompt_dependency_overrides(manifest.manifest_id))
    from_memory = getattr(agent_factory, "from_memory", None)
    try:
        if callable(from_memory):
            return from_memory(**kwargs)
        return agent_factory(**kwargs)
    except Exception as exc:
        location_hint = f" at '{memory_path}'" if memory_path else ""
        raise ValueError(
            f"Unable to build a prompt-inspection agent for harness '{manifest.manifest_id}'{location_hint}: {exc}"
        ) from exc


def _prompt_dependency_overrides(manifest_id: str) -> dict[str, Any]:
    if manifest_id == "instagram":
        return {"search_backend": _NullInstagramSearchBackend()}
    if manifest_id == "email":
        return {"resend_credentials": {"prompt_inspection": True}}
    return {}


def _null_model():
    from harnessiq.shared.agents import AgentModelResponse

    class NullModel:
        def generate_turn(self, request) -> AgentModelResponse:
            del request
            return AgentModelResponse(
                assistant_message="(null model - prompt inspection only)",
                should_continue=False,
            )

    return NullModel()


class _NullInstagramSearchBackend:
    def search_keyword(self, *, keyword: str, max_results: int):
        from harnessiq.shared.instagram import InstagramSearchExecution, InstagramSearchRecord

        del keyword, max_results
        return InstagramSearchExecution(
            search_record=InstagramSearchRecord(
                keyword="prompt-inspection",
                query="prompt-inspection",
                searched_at="1970-01-01T00:00:00Z",
            ),
            leads=(),
        )


__all__ = [
    "add_prompt_render_arguments",
    "build_prompt_bundle_for_manifest",
    "format_prompt_bundle_output",
    "render_prompt_bundle_for_manifest",
    "register_master_prompt_commands",
]
