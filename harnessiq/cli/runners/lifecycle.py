"""Shared lifecycle runners for manifest-backed CLI flows."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any

from harnessiq.agents import AgentRuntimeConfig
from harnessiq.cli._langsmith import seed_cli_environment
from harnessiq.cli.adapters.context import HarnessAdapterContext
from harnessiq.cli.common import emit_json, parse_allowed_tool_values, resolve_agent_model
from harnessiq.config import HarnessProfile, HarnessRunSnapshot
from harnessiq.shared.hooks import DEFAULT_APPROVAL_POLICY
from harnessiq.utils import ConnectionsConfigStore, build_output_sinks

_UNSET = object()


@dataclass(frozen=True, slots=True)
class ResolvedRunRequest:
    """Resolved execution request for one CLI lifecycle run/resume action."""

    model_factory: str | None
    model: str | None
    model_profile: str | None
    sink_specs: tuple[str, ...]
    max_cycles: int | None
    adapter_arguments: dict[str, Any]


class HarnessCliLifecycleRunner:
    """Resolve run requests and execute one lifecycle run against a harness adapter."""

    def resolve_run_request(
        self,
        *,
        args: argparse.Namespace,
        profile: HarnessProfile,
        resume_requested: bool,
        resume_snapshot: HarnessRunSnapshot | None,
        requested_run_number: int | None,
        run_argument_defaults: dict[str, Any],
        adapter_argument_names: tuple[str, ...],
        run_argument_overrides: dict[str, Any],
    ) -> ResolvedRunRequest:
        normalized_run_number = self._normalize_resume_run_number(requested_run_number)
        if normalized_run_number is not None and not resume_requested:
            raise ValueError("--run requires --resume when used with 'run <harness>'.")
        snapshot = resume_snapshot if resume_snapshot is not None else profile.last_run
        if resume_requested and snapshot is None:
            raise ValueError(
                f"Harness profile '{profile.agent_name}' does not have a previously persisted run payload to resume."
            )

        if resume_requested:
            model_factory, model, model_profile = self._merge_model_selection(
                snapshot=snapshot,
                override_model_factory=getattr(args, "model_factory", None),
                override_model=getattr(args, "model", None),
                override_model_profile=getattr(args, "model_profile", None),
            )
            sink_specs = tuple(args.sink) if args.sink else snapshot.sink_specs
            max_cycles = args.max_cycles if args.max_cycles is not None else snapshot.max_cycles
            adapter_arguments = dict(snapshot.adapter_arguments)
            for argument_name in adapter_argument_names:
                explicit_value = self._explicit_run_argument_value(args, argument_name, run_argument_defaults)
                if explicit_value is not _UNSET:
                    adapter_arguments[argument_name] = explicit_value
            adapter_arguments.update(run_argument_overrides)
            return ResolvedRunRequest(
                model_factory=model_factory,
                model=model,
                model_profile=model_profile,
                sink_specs=tuple(sink_specs),
                max_cycles=max_cycles,
                adapter_arguments=adapter_arguments,
            )

        model_factory, model, model_profile = self._collect_model_selection(
            model_factory=getattr(args, "model_factory", None),
            model=getattr(args, "model", None),
            model_profile=getattr(args, "model_profile", None),
            required=True,
        )
        adapter_arguments = {argument_name: getattr(args, argument_name) for argument_name in adapter_argument_names}
        adapter_arguments.update(run_argument_overrides)
        return ResolvedRunRequest(
            model_factory=model_factory,
            model=model,
            model_profile=model_profile,
            sink_specs=tuple(args.sink),
            max_cycles=args.max_cycles,
            adapter_arguments=adapter_arguments,
        )

    def resolve_resume_request_from_snapshot(
        self,
        *,
        snapshot: HarnessRunSnapshot | None,
        model_factory: str | None,
        model: str | None,
        model_profile: str | None,
        sink_specs: list[str],
        max_cycles: int | None,
        run_argument_overrides: dict[str, Any],
    ) -> ResolvedRunRequest:
        if snapshot is None:
            raise ValueError("The selected profile has no persisted run payload to resume.")
        resolved_model_factory, resolved_model, resolved_model_profile = self._merge_model_selection(
            snapshot=snapshot,
            override_model_factory=model_factory,
            override_model=model,
            override_model_profile=model_profile,
        )
        resolved_sink_specs = tuple(sink_specs) if sink_specs else snapshot.sink_specs
        resolved_max_cycles = max_cycles if max_cycles is not None else snapshot.max_cycles
        adapter_arguments = dict(snapshot.adapter_arguments)
        adapter_arguments.update(run_argument_overrides)
        return ResolvedRunRequest(
            model_factory=resolved_model_factory,
            model=resolved_model,
            model_profile=resolved_model_profile,
            sink_specs=tuple(resolved_sink_specs),
            max_cycles=resolved_max_cycles,
            adapter_arguments=adapter_arguments,
        )

    def execute_run(
        self,
        *,
        adapter,
        args: argparse.Namespace,
        context: HarnessAdapterContext,
        run_request: ResolvedRunRequest,
        base_payload: dict[str, Any],
        source_snapshot: HarnessRunSnapshot | None = None,
    ) -> int:
        seed_cli_environment(context.repo_root)
        model = resolve_agent_model(
            model_factory=run_request.model_factory,
            model_spec=run_request.model,
            profile_name=run_request.model_profile,
        )
        runtime_config = self.build_runtime_config(
            run_request.sink_specs,
            approval_policy=getattr(args, "approval_policy", None),
            allowed_tools=getattr(args, "allowed_tools", ()),
        )
        payload = dict(base_payload)
        payload["resume"] = self._resume_payload(run_request=run_request, source_snapshot=source_snapshot)
        payload.update(
            adapter.run(
                args=args,
                context=context,
                model=model,
                runtime_config=runtime_config,
            )
        )
        emit_json(payload)
        return 0

    def build_runtime_config(
        self,
        sink_specs: tuple[str, ...] | list[str],
        *,
        approval_policy: str | None = None,
        allowed_tools: tuple[str, ...] | list[str] = (),
    ) -> AgentRuntimeConfig:
        connections = ConnectionsConfigStore().load().enabled_connections()
        return AgentRuntimeConfig(
            approval_policy=approval_policy or DEFAULT_APPROVAL_POLICY,
            allowed_tools=parse_allowed_tool_values(allowed_tools),
            output_sinks=build_output_sinks(connections=connections, sink_specs=list(sink_specs)),
        )

    def _resume_payload(
        self,
        *,
        run_request: ResolvedRunRequest,
        source_snapshot: HarnessRunSnapshot | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "adapter_arguments": dict(run_request.adapter_arguments),
            "max_cycles": run_request.max_cycles,
            "sink_specs": list(run_request.sink_specs),
        }
        if run_request.model_factory is not None:
            payload["model_factory"] = run_request.model_factory
        if run_request.model is not None:
            payload["model"] = run_request.model
        if run_request.model_profile is not None:
            payload["profile"] = run_request.model_profile
        if source_snapshot is not None:
            payload["source_recorded_at"] = source_snapshot.recorded_at
            payload["source_run_number"] = source_snapshot.run_number
        return payload

    def _collect_model_selection(
        self,
        *,
        model_factory: str | None,
        model: str | None,
        model_profile: str | None,
        required: bool,
    ) -> tuple[str | None, str | None, str | None]:
        normalized_model_factory = self._normalize_optional_string(model_factory)
        normalized_model = self._normalize_optional_string(model)
        normalized_model_profile = self._normalize_optional_string(model_profile)
        selected_count = sum(
            1
            for value in (
                normalized_model_factory,
                normalized_model,
                normalized_model_profile,
            )
            if value is not None
        )
        if required and selected_count != 1:
            raise ValueError("Exactly one of --model, --profile, or --model-factory must be provided.")
        if not required and selected_count > 1:
            raise ValueError("Exactly one of --model, --profile, or --model-factory may be provided.")
        return normalized_model_factory, normalized_model, normalized_model_profile

    def _merge_model_selection(
        self,
        *,
        snapshot: HarnessRunSnapshot,
        override_model_factory: str | None,
        override_model: str | None,
        override_model_profile: str | None,
    ) -> tuple[str | None, str | None, str | None]:
        model_factory, model, model_profile = self._collect_model_selection(
            model_factory=override_model_factory,
            model=override_model,
            model_profile=override_model_profile,
            required=False,
        )
        if any(value is not None for value in (model_factory, model, model_profile)):
            return model_factory, model, model_profile
        return snapshot.model_factory, snapshot.model, snapshot.model_profile

    def _normalize_optional_string(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def _normalize_resume_run_number(self, run_number: int | None) -> int | None:
        if run_number is None:
            return None
        if run_number < 1:
            raise ValueError("--run must be greater than or equal to 1.")
        return run_number

    def _explicit_run_argument_value(
        self,
        args: argparse.Namespace,
        name: str,
        run_argument_defaults: dict[str, Any],
    ) -> Any:
        if not hasattr(args, name):
            return _UNSET
        value = getattr(args, name)
        default = run_argument_defaults.get(name)
        if value == default:
            return _UNSET
        return value


__all__ = ["HarnessCliLifecycleRunner", "ResolvedRunRequest"]
