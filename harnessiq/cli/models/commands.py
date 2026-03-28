"""CLI commands for persisted model profiles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from harnessiq.cli.common import emit_json
from harnessiq.config import ModelProfile, ModelProfileCatalog, ModelProfileStore
from harnessiq.integrations import parse_model_spec


def register_model_commands(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("models", help="Manage reusable provider-backed model profiles")
    parser.set_defaults(command_handler=lambda args: _print_help(parser))
    models_subparsers = parser.add_subparsers(dest="models_command")

    add_parser = models_subparsers.add_parser("add", help="Add or update a persisted model profile")
    add_parser.add_argument("--name", required=True, help="Unique profile name, for example work.")
    add_parser.add_argument(
        "--model",
        required=True,
        help="Provider-backed model reference in the form provider:model_name, for example openai:gpt-5.4.",
    )
    add_parser.add_argument("--temperature", type=float, help="Optional temperature override for the profile.")
    add_parser.add_argument(
        "--max-output-tokens",
        type=int,
        help="Optional output-token cap applied by the provider-backed adapter.",
    )
    add_parser.add_argument(
        "--reasoning-effort",
        choices=("low", "medium", "high"),
        help="Optional reasoning-effort override used by providers that support it.",
    )
    add_parser.set_defaults(command_handler=_handle_add)

    list_parser = models_subparsers.add_parser("list", help="List persisted model profiles")
    list_parser.set_defaults(command_handler=_handle_list)

    show_parser = models_subparsers.add_parser("show", help="Show one persisted model profile")
    show_parser.add_argument("name", help="Persisted model profile name.")
    show_parser.set_defaults(command_handler=_handle_show)

    remove_parser = models_subparsers.add_parser("remove", help="Remove one persisted model profile")
    remove_parser.add_argument("name", help="Persisted model profile name.")
    remove_parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required confirmation flag for deleting a persisted model profile.",
    )
    remove_parser.set_defaults(command_handler=_handle_remove)

    validate_parser = models_subparsers.add_parser("validate", help="Validate a provider:model spec")
    validate_parser.add_argument("spec", help="Model spec in provider:model format.")
    validate_parser.set_defaults(command_handler=_handle_validate)

    import_parser = models_subparsers.add_parser("import", help="Import model profiles from JSON")
    import_parser.add_argument("file", help="Path to a JSON file containing an array of profile objects.")
    import_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing profiles when names collide.",
    )
    import_parser.set_defaults(command_handler=_handle_import)

    export_parser = models_subparsers.add_parser("export", help="Export model profiles as JSON")
    export_parser.add_argument(
        "--output",
        help="Optional output path. When omitted, the exported profiles are printed to stdout as JSON.",
    )
    export_parser.set_defaults(command_handler=_handle_export)


def _handle_add(args: argparse.Namespace) -> int:
    provider, model_name = parse_model_spec(args.model)
    profile = ModelProfile(
        name=args.name,
        provider=provider,
        model_name=model_name,
        temperature=args.temperature,
        max_output_tokens=args.max_output_tokens,
        reasoning_effort=args.reasoning_effort,
    )
    store = ModelProfileStore()
    config_path = store.upsert(profile)
    emit_json(
        {
            "config_path": str(config_path),
            "profile": profile.as_dict(),
            "status": "saved",
        }
    )
    return 0


def _handle_list(args: argparse.Namespace) -> int:
    del args
    store = ModelProfileStore()
    catalog = store.load()
    emit_json(
        {
            "config_path": str(store.config_path),
            "profiles": [profile.as_dict() for profile in catalog.profiles],
        }
    )
    return 0


def _handle_show(args: argparse.Namespace) -> int:
    store = ModelProfileStore()
    profile = store.load().profile_for(args.name)
    emit_json(
        {
            "config_path": str(store.config_path),
            "profile": profile.as_dict(),
        }
    )
    return 0


def _handle_remove(args: argparse.Namespace) -> int:
    if not args.confirm:
        raise ValueError("Refusing to remove a model profile without --confirm.")
    store = ModelProfileStore()
    catalog = store.load()
    profile = catalog.profile_for(args.name)
    config_path = store.save(catalog.remove(args.name))
    emit_json(
        {
            "config_path": str(config_path),
            "profile": profile.as_dict(),
            "status": "removed",
        }
    )
    return 0


def _handle_validate(args: argparse.Namespace) -> int:
    try:
        provider, model_name = parse_model_spec(args.spec)
    except Exception as exc:  # pragma: no cover - exercised by CLI tests
        emit_json({"error": str(exc), "spec": args.spec, "valid": False})
        return 1
    emit_json(
        {
            "provider": provider,
            "model_name": model_name,
            "spec": args.spec,
            "valid": True,
        }
    )
    return 0


def _handle_import(args: argparse.Namespace) -> int:
    store = ModelProfileStore()
    imported_profiles = _load_profiles_file(args.file)
    existing_catalog = store.load()
    merged_catalog = _merge_catalogs(
        existing=existing_catalog,
        imported=imported_profiles,
        overwrite=bool(args.overwrite),
    )
    config_path = store.save(merged_catalog)
    emit_json(
        {
            "config_path": str(config_path),
            "imported_profiles": [profile.as_dict() for profile in imported_profiles],
            "overwrite": bool(args.overwrite),
            "profile_count": len(merged_catalog.profiles),
            "status": "imported",
        }
    )
    return 0


def _handle_export(args: argparse.Namespace) -> int:
    store = ModelProfileStore()
    profiles = [profile.as_dict() for profile in store.load().profiles]
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json.dumps(profiles, indent=2, sort_keys=True), encoding="utf-8")
        emit_json(
            {
                "count": len(profiles),
                "output_path": str(output_path),
                "status": "exported",
            }
        )
        return 0
    print(json.dumps(profiles, indent=2, sort_keys=True))
    return 0


def _load_profiles_file(path: str) -> tuple[ModelProfile, ...]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Model profile import files must contain a JSON array.")
    profiles = tuple(ModelProfile.from_dict(item) for item in payload)
    seen: set[str] = set()
    duplicates: list[str] = []
    for profile in profiles:
        if profile.name in seen and profile.name not in duplicates:
            duplicates.append(profile.name)
        seen.add(profile.name)
    if duplicates:
        rendered = ", ".join(sorted(duplicates))
        raise ValueError(f"Model profile import files must not contain duplicate profile names: {rendered}.")
    return profiles


def _merge_catalogs(
    *,
    existing: ModelProfileCatalog,
    imported: tuple[ModelProfile, ...],
    overwrite: bool,
) -> ModelProfileCatalog:
    indexed = {profile.name: profile for profile in existing.profiles}
    for profile in imported:
        if not overwrite and profile.name in indexed:
            raise ValueError(
                f"Model profile '{profile.name}' already exists. Re-run with --overwrite to replace it."
            )
        indexed[profile.name] = profile
    return ModelProfileCatalog(profiles=tuple(indexed[name] for name in sorted(indexed)))


def _print_help(parser: argparse.ArgumentParser) -> int:
    parser.print_help()
    return 0


__all__ = ["register_model_commands"]
