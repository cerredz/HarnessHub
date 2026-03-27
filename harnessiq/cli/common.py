"""Shared helper functions for JSON-oriented CLI command modules."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from harnessiq.shared.agents import AgentRuntimeConfig
from harnessiq.config import ModelProfileStore
from harnessiq.integrations import create_model_from_profile, create_model_from_spec
from harnessiq.shared.harness_manifest import HarnessManifest
from harnessiq.shared.hooks import DEFAULT_APPROVAL_POLICY, SUPPORTED_APPROVAL_POLICIES
from harnessiq.shared.tool_selection import ToolSelectionConfig
from harnessiq.utils import ConnectionsConfigStore, build_output_sinks


def add_agent_options(
    parser: argparse.ArgumentParser,
    *,
    agent_help: str,
    memory_root_default: str,
    memory_root_help: str,
) -> None:
    """Register the common ``--agent`` and ``--memory-root`` options."""
    parser.add_argument("--agent", required=True, help=agent_help)
    parser.add_argument(
        "--memory-root",
        default=memory_root_default,
        help=memory_root_help,
    )


def add_text_or_file_options(
    parser: argparse.ArgumentParser,
    field_name: str,
    label: str,
) -> None:
    """Register a mutually-exclusive ``--<field>-text`` / ``--<field>-file`` pair."""
    group = parser.add_mutually_exclusive_group()
    option_name = field_name.replace("_", "-")
    group.add_argument(f"--{option_name}-text", help=f"{label} content provided inline.")
    group.add_argument(
        f"--{option_name}-file",
        help=f"Path to a UTF-8 text file containing {label.lower()} content.",
    )


def resolve_memory_path(
    agent_name: str,
    memory_root: str,
    *,
    slugifier: Callable[[str], str] | None = None,
) -> Path:
    """Resolve the memory directory for a logical agent name."""
    normalize_name = slugifier or slugify_agent_name
    return Path(memory_root).expanduser() / normalize_name(agent_name)


def slugify_agent_name(agent_name: str) -> str:
    """Normalize a logical agent name into a filesystem-friendly directory name."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", agent_name.strip()).strip("-")
    if not cleaned:
        raise ValueError("Agent names must contain at least one alphanumeric character.")
    return cleaned


def resolve_text_argument(text_value: str | None, file_value: str | None) -> str | None:
    """Resolve a CLI value passed inline or from a UTF-8 text file."""
    if text_value is not None:
        return text_value
    if file_value is not None:
        return Path(file_value).read_text(encoding="utf-8")
    return None


def parse_generic_assignments(assignments: Sequence[str]) -> dict[str, Any]:
    """Parse ``KEY=VALUE`` pairs, decoding JSON scalars when possible."""
    parsed: dict[str, Any] = {}
    for assignment in assignments:
        key, raw_value = split_assignment(assignment)
        parsed[key] = parse_scalar(raw_value)
    return parsed


def split_assignment(assignment: str) -> tuple[str, str]:
    """Split a required ``KEY=VALUE`` assignment."""
    key, separator, value = assignment.partition("=")
    if not separator:
        raise ValueError(f"Expected KEY=VALUE assignment, received '{assignment}'.")
    normalized_key = key.strip()
    if not normalized_key:
        raise ValueError(f"Expected a non-empty key in assignment '{assignment}'.")
    return normalized_key, value


def parse_scalar(value: str) -> Any:
    """Parse a JSON-like scalar string, falling back to the original text."""
    trimmed = value.strip()
    if not trimmed:
        return ""
    try:
        return json.loads(trimmed)
    except json.JSONDecodeError:
        return value


def emit_json(payload: dict[str, Any]) -> None:
    """Render deterministic JSON for CLI command results."""
    print(json.dumps(payload, indent=2, sort_keys=True, default=_json_default))


def add_manifest_parameter_options(
    parser: argparse.ArgumentParser,
    *,
    manifest: HarnessManifest,
    scope: str,
) -> None:
    """Register manifest-driven CLI flags for one parameter scope."""
    specs = _manifest_parameter_specs(manifest, scope=scope)
    for spec in specs:
        help_parts = [spec.description]
        if spec.default is not None:
            help_parts.append(f"Default: {spec.default!r}.")
        if spec.choices:
            help_parts.append(f"Choices: {', '.join(repr(choice) for choice in spec.choices)}.")
        parser.add_argument(
            f"--{spec.key.replace('_', '-')}",
            dest=_manifest_option_dest(scope, spec.key),
            default=None,
            help=" ".join(help_parts),
        )

    if _manifest_scope_is_open_ended(manifest, scope=scope):
        parser.add_argument(
            f"--{scope}-param",
            action="append",
            default=[],
            metavar="KEY=VALUE",
            help=(
                f"Provide additional open-ended {scope} parameters as KEY=VALUE pairs. "
                "Values are parsed as JSON when possible."
            ),
        )


def add_policy_options(parser: argparse.ArgumentParser) -> None:
    """Register shared approval and allowlist flags for run commands."""
    parser.add_argument(
        "--approval",
        dest="approval_policy",
        choices=SUPPORTED_APPROVAL_POLICIES,
        default=DEFAULT_APPROVAL_POLICY,
        help=(
            "Approval policy for tool execution. "
            f"Choices: {', '.join(SUPPORTED_APPROVAL_POLICIES)}."
        ),
    )
    parser.add_argument(
        "--allowed-tools",
        action="append",
        default=[],
        metavar="PATTERN[,PATTERN...]",
        help=(
            "Allow only matching tool keys or families. Repeat the flag or provide comma-delimited values. "
            "Examples: filesystem, filesystem.*, context.select.checkpoint."
        ),
    )
    parser.add_argument(
        "--dynamic-tools",
        action="store_true",
        help="Enable dynamic tool selection for this run. Disabled by default.",
    )
    parser.add_argument(
        "--dynamic-tool-candidates",
        action="append",
        default=[],
        metavar="PATTERN[,PATTERN...]",
        help=(
            "Restrict dynamic selection to matching tool keys or families. "
            "Repeat the flag or provide comma-delimited values."
        ),
    )
    parser.add_argument(
        "--dynamic-tool-top-k",
        type=int,
        default=5,
        help="Number of retrieved tools to expose each turn when dynamic selection is enabled.",
    )
    parser.add_argument(
        "--dynamic-tool-embedding-model",
        help="Optional embedding model spec in provider:model form for dynamic tool selection.",
    )


def add_model_selection_options(
    parser: argparse.ArgumentParser,
    *,
    required: bool = True,
) -> None:
    """Register one mutually-exclusive model-selection surface for run commands."""
    group = parser.add_mutually_exclusive_group(required=required)
    group.add_argument(
        "--model",
        help="Provider-backed model reference in the form provider:model_name, for example openai:gpt-5.4.",
    )
    group.add_argument(
        "--profile",
        dest="model_profile",
        help="Name of a persisted model profile created with `harnessiq models add`.",
    )
    group.add_argument(
        "--model-factory",
        help="Import path in the form module:callable that returns an AgentModel instance.",
    )


def format_manifest_parameter_keys(
    manifest: HarnessManifest,
    *,
    scope: str,
) -> str:
    """Return a comma-delimited key list for one manifest parameter scope."""
    if scope == "runtime":
        keys = manifest.runtime_parameter_names
    elif scope == "custom":
        keys = manifest.custom_parameter_names
    else:
        raise ValueError(f"Unsupported manifest parameter scope '{scope}'.")
    return ", ".join(keys)


def parse_manifest_parameter_assignments(
    assignments: Sequence[str],
    *,
    manifest: HarnessManifest,
    scope: str,
) -> dict[str, Any]:
    """Parse CLI assignments and coerce them using a harness manifest."""
    parsed = parse_generic_assignments(assignments)
    if scope == "runtime":
        return manifest.coerce_runtime_parameters(parsed)
    if scope == "custom":
        return manifest.coerce_custom_parameters(parsed)
    raise ValueError(f"Unsupported manifest parameter scope '{scope}'.")


def collect_manifest_parameter_values(
    args: argparse.Namespace,
    *,
    manifest: HarnessManifest,
    scope: str,
) -> dict[str, Any]:
    """Collect manifest-driven parameter values from parsed argparse state."""
    values: dict[str, Any] = {}
    for spec in _manifest_parameter_specs(manifest, scope=scope):
        option_value = getattr(args, _manifest_option_dest(scope, spec.key), None)
        if option_value is None:
            continue
        values[spec.key] = option_value
    assignment_values = getattr(args, f"{scope}_param", ())
    if assignment_values:
        values.update(parse_manifest_parameter_assignments(assignment_values, manifest=manifest, scope=scope))
    if not values:
        return {}
    if scope == "runtime":
        return manifest.coerce_runtime_parameters(values)
    if scope == "custom":
        return manifest.coerce_custom_parameters(values)
    raise ValueError(f"Unsupported manifest parameter scope '{scope}'.")


def load_factory(spec: str):
    """Import a callable from ``module:attribute`` notation."""
    module_name, separator, attribute_path = spec.partition(":")
    if not separator or not module_name or not attribute_path:
        raise ValueError(f"Factory import paths must use the form module:callable. Received '{spec}'.")
    module = importlib.import_module(module_name)
    target: Any = module
    for attribute_name in attribute_path.split("."):
        target = getattr(target, attribute_name)
    if not callable(target):
        raise TypeError(f"Imported object '{spec}' is not callable.")
    return target


def resolve_agent_model(
    *,
    model_factory: str | None = None,
    model_spec: str | None = None,
    profile_name: str | None = None,
    home_dir: str | Path | None = None,
):
    """Construct an AgentModel from one shared CLI selection surface."""
    selected_count = sum(
        1
        for value in (model_factory, model_spec, profile_name)
        if isinstance(value, str) and value.strip()
    )
    if selected_count != 1:
        raise ValueError(
            "Exactly one of --model, --profile, or --model-factory must be provided."
        )
    if model_factory:
        model = load_factory(model_factory)()
    elif model_spec:
        model = create_model_from_spec(model_spec)
    else:
        profile = ModelProfileStore(home_dir=home_dir).load().profile_for(str(profile_name))
        model = create_model_from_profile(profile)
    if not hasattr(model, "generate_turn"):
        raise TypeError("Model selection must resolve to an object that implements generate_turn(request).")
    return model


def resolve_agent_model_from_args(
    args: argparse.Namespace,
    *,
    home_dir: str | Path | None = None,
):
    """Construct an AgentModel from parsed argparse state."""
    return resolve_agent_model(
        model_factory=getattr(args, "model_factory", None),
        model_spec=getattr(args, "model", None),
        profile_name=getattr(args, "model_profile", None),
        home_dir=home_dir,
    )


def resolve_repo_root(path: str | Path) -> Path:
    """Resolve the nearest repo root for a CLI path, falling back to the path itself."""
    resolved = Path(path).expanduser().resolve()
    for candidate in (resolved, *resolved.parents):
        if (candidate / ".git").exists():
            return candidate
    return resolved


def parse_allowed_tool_values(values: Sequence[str]) -> tuple[str, ...]:
    """Normalize repeatable/comma-delimited allowlist values."""
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        for part in str(raw_value).split(","):
            candidate = part.strip()
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            normalized.append(candidate)
    return tuple(normalized)


def build_runtime_config(
    *,
    sink_specs: Sequence[str] = (),
    approval_policy: str | None = None,
    allowed_tools: Sequence[str] = (),
    dynamic_tools_enabled: bool = False,
    dynamic_tool_candidates: Sequence[str] = (),
    dynamic_tool_top_k: int = 5,
    dynamic_tool_embedding_model: str | None = None,
) -> AgentRuntimeConfig:
    """Build one runtime config from shared CLI surfaces."""
    output_sinks = ()
    if sink_specs:
        connections = ConnectionsConfigStore().load().enabled_connections()
        output_sinks = build_output_sinks(connections=connections, sink_specs=sink_specs)
    tool_selection = ToolSelectionConfig(
        enabled=dynamic_tools_enabled,
        embedding_model=dynamic_tool_embedding_model,
        top_k=dynamic_tool_top_k,
        candidate_tool_keys=parse_allowed_tool_values(dynamic_tool_candidates),
    )
    return AgentRuntimeConfig(
        approval_policy=approval_policy or DEFAULT_APPROVAL_POLICY,
        allowed_tools=parse_allowed_tool_values(allowed_tools),
        tool_selection=tool_selection,
        output_sinks=output_sinks,
    )


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return os.fspath(value)
    return str(value)


def _manifest_parameter_specs(
    manifest: HarnessManifest,
    *,
    scope: str,
):
    if scope == "runtime":
        return manifest.runtime_parameters
    if scope == "custom":
        return manifest.custom_parameters
    raise ValueError(f"Unsupported manifest parameter scope '{scope}'.")


def _manifest_scope_is_open_ended(manifest: HarnessManifest, *, scope: str) -> bool:
    if scope == "runtime":
        return manifest.runtime_parameters_open_ended
    if scope == "custom":
        return manifest.custom_parameters_open_ended
    raise ValueError(f"Unsupported manifest parameter scope '{scope}'.")


def _manifest_option_dest(scope: str, key: str) -> str:
    return f"{scope}_param__{key}"


__all__ = [
    "add_agent_options",
    "add_manifest_parameter_options",
    "add_policy_options",
    "add_model_selection_options",
    "add_text_or_file_options",
    "build_runtime_config",
    "collect_manifest_parameter_values",
    "emit_json",
    "format_manifest_parameter_keys",
    "load_factory",
    "parse_allowed_tool_values",
    "parse_manifest_parameter_assignments",
    "parse_generic_assignments",
    "parse_scalar",
    "resolve_repo_root",
    "resolve_memory_path",
    "resolve_agent_model",
    "resolve_agent_model_from_args",
    "resolve_text_argument",
    "slugify_agent_name",
    "split_assignment",
]
