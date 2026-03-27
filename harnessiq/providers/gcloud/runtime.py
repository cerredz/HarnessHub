"""Generic Cloud Run runtime wrapper for manifest-backed HarnessIQ harnesses."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from harnessiq.cli._langsmith import seed_cli_environment
from harnessiq.cli.common import build_runtime_config, emit_json, resolve_agent_model
from harnessiq.cli.commands.command_helpers import (
    _ResolvedRunRequest,
    _base_payload,
    _build_adapter,
    _build_context,
    _persist_run_snapshot,
)
from harnessiq.shared.harness_manifests import get_harness_manifest
from harnessiq.utils.path_serialization import deserialize_repo_path

from .context import GcpContext


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m harnessiq.providers.gcloud.runtime",
        description="Run one manifest-backed HarnessIQ harness inside a GCP runtime wrapper.",
    )
    parser.add_argument("--agent", required=True, help="Logical HarnessIQ agent name.")
    parser.add_argument("--manifest-id", required=True, help="Harness manifest id to execute.")
    parser.add_argument(
        "--memory-path",
        required=True,
        help="Repo-root-relative memory directory serialized into the deploy spec.",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root used to resolve serialized memory paths. Defaults to the current directory.",
    )
    return parser


def run_runtime(
    *,
    agent_name: str,
    manifest_id: str,
    memory_path: str,
    repo_root: Path | str = ".",
    gcp_context: GcpContext | None = None,
) -> dict[str, Any]:
    resolved_repo_root = Path(repo_root).expanduser().resolve()
    ctx = gcp_context or GcpContext.from_config(agent_name)
    config = ctx.config
    if config.agent_name != agent_name:
        raise ValueError(
            f"GCP config belongs to agent '{config.agent_name}', not '{agent_name}'."
        )
    if config.manifest_id is not None and config.manifest_id != manifest_id:
        raise ValueError(
            f"GCP config manifest '{config.manifest_id}' does not match runtime manifest '{manifest_id}'."
        )

    config.manifest_id = manifest_id
    config.memory_path = memory_path.strip()
    if not config.memory_path:
        raise ValueError("memory_path must not be blank.")

    local_memory_path = deserialize_repo_path(config.memory_path, repo_root=resolved_repo_root)
    synced_from_gcs = ctx.storage.sync_memory_from_gcs(config.memory_path, local_memory_path)
    execution_error: Exception | None = None
    sync_error: Exception | None = None
    result_payload: dict[str, Any] | None = None
    try:
        manifest = get_harness_manifest(config.manifest_id)
        adapter = _build_adapter(manifest)
        deploy_spec = ctx.derive_deploy_spec(repo_root=resolved_repo_root)
        if deploy_spec.manifest_id != manifest.manifest_id:
            raise ValueError(
                f"Derived deploy spec manifest '{deploy_spec.manifest_id}' does not match runtime manifest '{manifest.manifest_id}'."
            )
        if deploy_spec.memory_path != config.memory_path:
            raise ValueError(
                f"Derived deploy spec memory path '{deploy_spec.memory_path}' does not match runtime memory path '{config.memory_path}'."
            )

        context = _build_context(
            manifest=manifest,
            adapter=adapter,
            agent_name=config.agent_name,
            memory_path=local_memory_path,
            incoming_runtime=config.runtime_parameters,
            incoming_custom=config.custom_parameters,
            persist_profile=True,
        )
        run_request = _ResolvedRunRequest(
            model_factory=deploy_spec.model_selection.model_factory,
            model=deploy_spec.model_selection.model,
            model_profile=deploy_spec.model_selection.model_profile,
            sink_specs=deploy_spec.sink_specs,
            max_cycles=deploy_spec.max_cycles,
            adapter_arguments=deploy_spec.adapter_arguments,
        )
        context = _persist_run_snapshot(context, run_request)
        seed_cli_environment(context.repo_root)
        model = resolve_agent_model(
            model_factory=run_request.model_factory,
            model_spec=run_request.model,
            profile_name=run_request.model_profile,
        )
        runtime_config = build_runtime_config(sink_specs=run_request.sink_specs)
        args = _build_runtime_args(adapter=adapter, run_request=run_request)
        result_payload = (
            _base_payload(context)
            .with_extra(
                remote_command=list(deploy_spec.remote_command),
                runtime={
                    "memory_uri": ctx.storage.runtime_state_uri(config.memory_path),
                    "synced_from_gcs": synced_from_gcs,
                    "synced_to_gcs": False,
                },
            )
            .merge_response(
                adapter.run(
                    args=args,
                    context=context,
                    model=model,
                    runtime_config=runtime_config,
                )
            )
            .with_status("completed")
            .to_dict()
        )
    except Exception as exc:  # pragma: no cover - exercised by tests with assertions on side effects
        execution_error = exc

    try:
        synced_to_gcs = ctx.storage.sync_memory_to_gcs(config.memory_path, local_memory_path)
    except Exception as exc:  # pragma: no cover - exercised by tests with assertions on side effects
        synced_to_gcs = False
        sync_error = exc
    if result_payload is not None:
        result_payload["runtime"]["synced_to_gcs"] = synced_to_gcs
    if execution_error is not None:
        if sync_error is not None:
            raise RuntimeError(
                f"Runtime execution failed with '{execution_error}' and sync-back failed with '{sync_error}'."
            ) from execution_error
        raise execution_error
    if sync_error is not None:
        raise sync_error
    if result_payload is None:  # pragma: no cover - defensive
        raise RuntimeError("Runtime wrapper completed without a result payload.")
    return result_payload


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        emit_json(
            run_runtime(
                agent_name=args.agent,
                manifest_id=args.manifest_id,
                memory_path=args.memory_path,
                repo_root=args.repo_root,
            )
        )
    except Exception as exc:
        emit_json(
            {
                "agent": args.agent,
                "error": str(exc),
                "manifest_id": args.manifest_id,
                "memory_path": args.memory_path,
                "status": "error",
            }
        )
        return 1
    return 0


def _build_runtime_args(*, adapter, run_request: _ResolvedRunRequest) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    adapter.register_run_arguments(parser)
    payload = vars(parser.parse_args([]))
    payload.update(dict(run_request.adapter_arguments))
    payload["max_cycles"] = run_request.max_cycles
    return argparse.Namespace(**payload)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
