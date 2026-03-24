from __future__ import annotations

import argparse
import ast
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT / "artifacts"
HARNESSIQ_DIR = ROOT / "harnessiq"
CLI_DIR = HARNESSIQ_DIR / "cli"
PROVIDERS_DIR = HARNESSIQ_DIR / "providers"
SHARED_DIR = HARNESSIQ_DIR / "shared"
TOOLS_DIR = HARNESSIQ_DIR / "tools"
UTILS_DIR = HARNESSIQ_DIR / "utils"
TESTS_DIR = ROOT / "tests"


TOP_LEVEL_DIRECTORY_DESCRIPTIONS = {
    ".harnessiq": (
        "generated/cache",
        "Fallback local HarnessIQ home used by the ledger/output-sink runtime when the preferred home path is not writable.",
    ),
    ".pytest_cache": ("generated/cache", "Test runner cache; generated, not part of the source of truth."),
    "artifacts": ("repo docs", "Generated and curated repository reference artifacts."),
    "build": ("generated/cache", "Setuptools build output; generated, not part of the live source tree."),
    "docs": ("repo docs", "Focused usage and architecture notes for the package."),
    "harnessiq": ("source", "Live SDK package source."),
    "harnessiq.egg-info": ("generated/cache", "Packaging metadata emitted by local builds."),
    "memory": ("local state", "Task artifacts plus durable agent runtime state; not part of the shipped package."),
    "scripts": ("repo tooling", "Repository maintenance and generation scripts."),
    "src": ("generated/cache", "Legacy or generated residue in this checkout; not the authoritative package source."),
    "tests": ("source", "unittest coverage for runtime, CLI, providers, and tools."),
}

PACKAGE_LAYOUT = [
    (
        "harnessiq/agents/",
        "Shared runtime bases plus the concrete harness packages exported by the SDK.",
    ),
    (
        "harnessiq/cli/",
        "Argparse entrypoints and command-family modules for harness management plus ledger/output-sink operations.",
    ),
    (
        "harnessiq/config/",
        "Environment loading, credential binding, and provider-credential spec models.",
    ),
    (
        "harnessiq/integrations/",
        "Concrete external runtime adapters such as Playwright backends and model factories.",
    ),
    (
        "harnessiq/master_prompts/",
        "Packaged prompt assets and prompt registry helpers.",
    ),
    (
        "harnessiq/providers/",
        "Model-provider adapters, external service clients, output-sink transport clients, and Playwright runtime support.",
    ),
    (
        "harnessiq/shared/",
        "Shared manifests, durable memory stores, operation metadata, and package-wide types/constants.",
    ),
    (
        "harnessiq/tools/",
        "Built-in tool families, provider-backed tool factories, and domain-specific helper tools.",
    ),
    (
        "harnessiq/toolset/",
        "Static tool catalog plus registration and lookup helpers for reusable tool composition.",
    ),
    (
        "harnessiq/utils/",
        "Agent instance storage, ledger export/report helpers, and built-in output sink implementations.",
    ),
]

FOCUSED_SUBPACKAGE_DESCRIPTIONS = [
    (
        "harnessiq/cli/adapters/",
        "Manifest-driven platform CLI adapter package with one module per harness plus shared adapter primitives.",
    ),
    (
        "harnessiq/cli/adapters/utils/",
        "Shared helper modules for adapter store loading, payload shaping, factory resolution, and session-directory setup.",
    ),
    (
        "harnessiq/config/provider_credentials/",
        "Focused provider-credential spec package split into catalog, models, builders, and masking helpers.",
    ),
    (
        "harnessiq/utils/harness_manifest/",
        "Manifest coercion, validation, and registry helpers extracted from the public shared manifest modules.",
    ),
]

KEY_FILE_DESCRIPTIONS = [
    (
        "harnessiq/shared/harness_manifest.py",
        "Typed manifest primitives for runtime/custom parameters, durable memory entries, provider families, and output schemas.",
    ),
    (
        "harnessiq/shared/harness_manifests.py",
        "Registry of the built-in harness manifests in deterministic order.",
    ),
    (
        "harnessiq/cli/main.py",
        "Root argparse entrypoint that wires every top-level command family into `harnessiq`.",
    ),
    (
        "harnessiq/cli/platform_commands.py",
        "Platform-first CLI roots that synthesize manifest-driven prepare/show/run/inspect and credential management commands.",
    ),
    (
        "harnessiq/cli/adapters/base.py",
        "Abstract adapter hooks and shared store-backed adapter behavior for the platform-first CLI.",
    ),
    (
        "harnessiq/toolset/catalog_provider.py",
        "Provider-tool catalog metadata used by the toolset lookup layer.",
    ),
    (
        "harnessiq/tools/builtin.py",
        "Built-in tool registry composition for the base runtime surface.",
    ),
    (
        "harnessiq/utils/ledger_sinks.py",
        "Built-in output sink registration plus sink-construction helpers.",
    ),
    (
        "scripts/sync_repo_docs.py",
        "AST-driven repository docs generator that keeps README and architecture artifacts aligned with live source.",
    ),
]

FILE_INDEX_STANDARDS = [
    "Treat `harnessiq/` as the only authoritative runtime source tree. `build/`, `src/`, caches, and packaging metadata are generated or residue directories.",
    "Concrete harness metadata belongs in the shared manifest layer under `harnessiq/shared/`, and CLI behavior should consume that metadata instead of duplicating typed parameter rules.",
    "Agents orchestrate. Tools execute deterministic operations. Providers wrap external systems. Utilities own cross-cutting runtime infrastructure like the ledger and output sinks.",
    "Durable memory is a first-class design constraint: harnesses are expected to persist state that survives resets and restarts.",
    "Provider-backed integrations should flow through `harnessiq/providers/` and `harnessiq/tools/`, not through ad hoc HTTP logic embedded in harness modules.",
    "Output sinks are post-run exports only. They do not participate in the model loop or mutate the transcript.",
    "This file and the companion CLI/README docs are generated by `python scripts/sync_repo_docs.py`; update the source tree and rerun the generator instead of hand-editing the artifacts.",
]

README_DOC_LINKS = [
    ("docs/agent-runtime.md", "Runtime loop, manifests, and durable parameter sections."),
    ("docs/tools.md", "Tool registry composition and provider-backed tool usage."),
    ("docs/output-sinks.md", "Ledger/output-sink injection and sink connection commands."),
    ("docs/linkedin-agent.md", "LinkedIn harness usage and browser session workflow."),
    ("docs/leads-agent.md", "Leads harness memory model and CLI workflow."),
    ("artifacts/file_index.md", "Generated architecture map for the live repository."),
    ("artifacts/commands.md", "Generated CLI command catalog."),
    ("artifacts/live_inventory.json", "Machine-readable source of truth for generated repo docs."),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Regenerate repo docs from live source files.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify that generated outputs match the committed files without writing them.",
    )
    return parser.parse_args()


def read_ast(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))


def relative_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def get_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def get_call_keyword(call: ast.Call, keyword_name: str) -> ast.AST | None:
    for keyword in call.keywords:
        if keyword.arg == keyword_name:
            return keyword.value
    return None


def get_call_arg(call: ast.Call, index: int, keyword_name: str) -> ast.AST | None:
    if len(call.args) > index:
        return call.args[index]
    return get_call_keyword(call, keyword_name)


def resolve_import_source(current_path: Path, module_name: str | None, level: int) -> Path | None:
    if level:
        base = current_path.parent
        for _ in range(level - 1):
            base = base.parent
        if module_name:
            base = base / Path(*module_name.split("."))
    else:
        if not module_name:
            return None
        base = ROOT / Path(*module_name.split("."))

    file_path = base.with_suffix(".py")
    if file_path.exists():
        return file_path
    init_path = base / "__init__.py"
    if init_path.exists():
        return init_path
    return None


def eval_simple(node: ast.AST, constants: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return constants.get(node.id, node.id)
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant):
                parts.append(str(value.value))
            elif isinstance(value, ast.FormattedValue):
                parts.append(str(eval_simple(value.value, constants)))
        return "".join(parts)
    if isinstance(node, ast.Tuple):
        return tuple(eval_simple(item, constants) for item in node.elts)
    if isinstance(node, ast.List):
        return [eval_simple(item, constants) for item in node.elts]
    if isinstance(node, ast.Dict):
        return {
            eval_simple(key, constants): eval_simple(value, constants)
            for key, value in zip(node.keys, node.values, strict=True)
        }
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = eval_simple(node.left, constants)
        right = eval_simple(node.right, constants)
        if isinstance(left, str) and isinstance(right, str):
            return left + right
    if isinstance(node, ast.Call):
        func_name = get_name(node.func)
        if func_name == "sorted" and len(node.args) == 1:
            payload = eval_simple(node.args[0], constants)
            if isinstance(payload, dict):
                return sorted(payload)
            if isinstance(payload, (list, tuple, set, frozenset)):
                return sorted(payload)
        if func_name in {"tuple", "list", "frozenset"} and len(node.args) == 1:
            payload = eval_simple(node.args[0], constants)
            if isinstance(payload, dict):
                payload = payload.keys()
            if isinstance(payload, (list, tuple, set, frozenset)) or hasattr(payload, "__iter__"):
                constructor = {"tuple": tuple, "list": list, "frozenset": frozenset}[func_name]
                return constructor(payload)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -eval_simple(node.operand, constants)
    return ast.unparse(node)


def collect_constants_from_path(
    path: Path,
    *,
    cache: dict[Path, dict[str, Any]] | None = None,
    stack: set[Path] | None = None,
) -> dict[str, Any]:
    resolved_path = path.resolve()
    cache = {} if cache is None else cache
    stack = set() if stack is None else stack
    if resolved_path in cache:
        return cache[resolved_path]
    if resolved_path in stack:
        return {}

    stack.add(resolved_path)
    module = read_ast(resolved_path)
    constants: dict[str, Any] = {}
    for statement in module.body:
        if not isinstance(statement, ast.ImportFrom):
            continue
        imported_path = resolve_import_source(resolved_path, statement.module, statement.level)
        if imported_path is None:
            continue
        imported_constants = collect_constants_from_path(imported_path, cache=cache, stack=stack)
        for alias in statement.names:
            imported_name = alias.asname or alias.name
            if not imported_name.isupper():
                continue
            if alias.name in imported_constants:
                constants[imported_name] = imported_constants[alias.name]

    for statement in module.body:
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name):
            try:
                constants[statement.targets[0].id] = eval_simple(statement.value, constants)
            except Exception:
                continue
        elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name) and statement.value is not None:
            try:
                constants[statement.target.id] = eval_simple(statement.value, constants)
            except Exception:
                continue
    stack.remove(resolved_path)
    cache[resolved_path] = constants
    return constants


def parse_supported_model_providers() -> list[str]:
    constants = collect_constants_from_path(SHARED_DIR / "providers.py")
    providers = constants.get("SUPPORTED_PROVIDERS", ())
    return [str(value) for value in providers]


def parse_manifest_sources() -> list[tuple[str, Path]]:
    registry_path = SHARED_DIR / "harness_manifests.py"
    module = read_ast(registry_path)
    import_map: dict[str, Path] = {}
    ordered: list[tuple[str, Path]] = []

    for statement in module.body:
        if isinstance(statement, ast.ImportFrom) and statement.module and statement.module.startswith("harnessiq.shared"):
            source_path = ROOT / Path(statement.module.replace(".", "/") + ".py")
            for alias in statement.names:
                imported_name = alias.asname or alias.name
                if imported_name.endswith("_HARNESS_MANIFEST"):
                    import_map[imported_name] = source_path

    for statement in module.body:
        targets: list[ast.expr] = []
        value: ast.AST | None = None
        if isinstance(statement, ast.Assign):
            targets = statement.targets
            value = statement.value
        elif isinstance(statement, ast.AnnAssign):
            targets = [statement.target]
            value = statement.value
        if not targets or value is None:
            continue
        if not any(isinstance(target, ast.Name) and target.id == "_BUILTIN_HARNESS_MANIFESTS" for target in targets):
            continue
        if isinstance(value, (ast.Tuple, ast.List)):
            for item in value.elts:
                if isinstance(item, ast.Name) and item.id in import_map:
                    ordered.append((item.id, import_map[item.id]))
        break

    return ordered


def parse_parameter_specs(node: ast.AST | None, constants: dict[str, Any]) -> list[dict[str, Any]]:
    if node is None or not isinstance(node, (ast.Tuple, ast.List)):
        return []
    specs: list[dict[str, Any]] = []
    for item in node.elts:
        if not isinstance(item, ast.Call) or get_name(item.func) != "HarnessParameterSpec":
            continue
        key = get_call_arg(item, 0, "key")
        value_type = get_call_arg(item, 1, "value_type")
        description = get_call_arg(item, 2, "description")
        nullable = get_call_keyword(item, "nullable")
        specs.append(
            {
                "key": str(eval_simple(key, constants)) if key is not None else "",
                "value_type": str(eval_simple(value_type, constants)) if value_type is not None else "",
                "description": str(eval_simple(description, constants)) if description is not None else "",
                "nullable": bool(eval_simple(nullable, constants)) if nullable is not None else False,
            }
        )
    return specs


def parse_memory_specs(node: ast.AST | None, constants: dict[str, Any]) -> list[dict[str, Any]]:
    if node is None or not isinstance(node, (ast.Tuple, ast.List)):
        return []
    specs: list[dict[str, Any]] = []
    for item in node.elts:
        if not isinstance(item, ast.Call) or get_name(item.func) != "HarnessMemoryFileSpec":
            continue
        key = get_call_arg(item, 0, "key")
        relative_path = get_call_arg(item, 1, "relative_path")
        description = get_call_arg(item, 2, "description")
        kind = get_call_keyword(item, "kind")
        format_value = get_call_keyword(item, "format")
        specs.append(
            {
                "key": str(eval_simple(key, constants)) if key is not None else "",
                "relative_path": str(eval_simple(relative_path, constants)) if relative_path is not None else "",
                "description": str(eval_simple(description, constants)) if description is not None else "",
                "kind": str(eval_simple(kind, constants)) if kind is not None else "file",
                "format": str(eval_simple(format_value, constants)) if format_value is not None else "other",
            }
        )
    return specs


def parse_output_fields(node: ast.AST | None, constants: dict[str, Any]) -> list[str]:
    if node is None:
        return []
    try:
        payload = eval_simple(node, constants)
    except Exception:
        return []
    if not isinstance(payload, dict):
        return []
    properties = payload.get("properties")
    if not isinstance(properties, dict):
        return []
    return sorted(str(key) for key in properties)


def parse_harness_manifest(manifest_name: str, source_path: Path) -> dict[str, Any]:
    module = read_ast(source_path)
    constants = collect_constants_from_path(source_path)

    manifest_call: ast.Call | None = None
    for statement in module.body:
        targets: list[ast.expr] = []
        value: ast.AST | None = None
        if isinstance(statement, ast.Assign):
            targets = statement.targets
            value = statement.value
        elif isinstance(statement, ast.AnnAssign):
            targets = [statement.target]
            value = statement.value
        if not targets or value is None:
            continue
        if any(isinstance(target, ast.Name) and target.id == manifest_name for target in targets):
            if isinstance(value, ast.Call) and get_name(value.func) == "HarnessManifest":
                manifest_call = value
                break

    if manifest_call is None:
        raise ValueError(f"Could not locate {manifest_name} in {source_path}.")

    keyword_map = {keyword.arg: keyword.value for keyword in manifest_call.keywords if keyword.arg}
    manifest_id = str(eval_simple(keyword_map["manifest_id"], constants))
    cli_command_node = keyword_map.get("cli_command")
    cli_command_value = eval_simple(cli_command_node, constants) if cli_command_node is not None else None
    cli_value = None if cli_command_value is None else str(cli_command_value)
    default_memory_root = keyword_map.get("default_memory_root")
    memory_root_value = (
        str(eval_simple(default_memory_root, constants))
        if default_memory_root is not None
        else f"memory/{cli_value or manifest_id}"
    )
    provider_families = eval_simple(keyword_map.get("provider_families", ast.Tuple(elts=[], ctx=ast.Load())), constants)
    if not isinstance(provider_families, tuple):
        provider_families = tuple(provider_families) if isinstance(provider_families, list) else ()

    return {
        "manifest_id": manifest_id,
        "agent_name": str(eval_simple(keyword_map["agent_name"], constants)),
        "display_name": str(eval_simple(keyword_map["display_name"], constants)),
        "module_path": str(eval_simple(keyword_map["module_path"], constants)),
        "class_name": str(eval_simple(keyword_map["class_name"], constants)),
        "cli_command": cli_value,
        "cli_adapter_path": (
            str(eval_simple(keyword_map["cli_adapter_path"], constants))
            if "cli_adapter_path" in keyword_map
            else None
        ),
        "default_memory_root": memory_root_value,
        "prompt_path": (
            str(eval_simple(keyword_map["prompt_path"], constants))
            if "prompt_path" in keyword_map
            else None
        ),
        "runtime_parameters": parse_parameter_specs(keyword_map.get("runtime_parameters"), constants),
        "custom_parameters": parse_parameter_specs(keyword_map.get("custom_parameters"), constants),
        "runtime_parameters_open_ended": bool(
            eval_simple(keyword_map["runtime_parameters_open_ended"], constants)
        ) if "runtime_parameters_open_ended" in keyword_map else False,
        "custom_parameters_open_ended": bool(
            eval_simple(keyword_map["custom_parameters_open_ended"], constants)
        ) if "custom_parameters_open_ended" in keyword_map else False,
        "memory_files": parse_memory_specs(keyword_map.get("memory_files"), constants),
        "provider_families": [str(value) for value in provider_families],
        "output_fields": parse_output_fields(keyword_map.get("output_schema"), constants),
        "source_file": relative_path(source_path),
    }


def parse_harnesses() -> list[dict[str, Any]]:
    manifests: list[dict[str, Any]] = []
    for manifest_name, source_path in parse_manifest_sources():
        manifests.append(parse_harness_manifest(manifest_name, source_path))
    return manifests


def extract_catalog_count(path: Path) -> int | None:
    module = read_ast(path)
    for statement in module.body:
        value: ast.AST | None = None
        target_name: str | None = None
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name):
            target_name = statement.targets[0].id
            value = statement.value
        elif isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
            target_name = statement.target.id
            value = statement.value
        if value is None or target_name is None or "CATALOG" not in target_name.upper():
            continue
        if isinstance(value, ast.Call) and get_name(value.func) == "OrderedDict" and value.args:
            sequence = value.args[0]
            if isinstance(sequence, (ast.Tuple, ast.List)):
                return len(sequence.elts)
    return None


def parse_builtin_sink_types() -> list[str]:
    module = read_ast(UTILS_DIR / "ledger_sinks.py")
    for statement in module.body:
        if not isinstance(statement, ast.FunctionDef) or statement.name != "_register_builtin_sinks":
            continue
        for inner in statement.body:
            if not isinstance(inner, ast.Expr) or not isinstance(inner.value, ast.Call):
                continue
            call = inner.value
            if not isinstance(call.func, ast.Attribute) or call.func.attr != "update":
                continue
            if get_name(call.func.value) != "_BUILTIN_SINK_FACTORIES" or not call.args:
                continue
            payload = call.args[0]
            if not isinstance(payload, ast.Dict):
                continue
            sink_types: list[str] = []
            for key in payload.keys:
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    sink_types.append(key.value)
            return sorted(sink_types)
    return []


def parse_service_providers(model_providers: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    provider_dirs = sorted(
        directory.name for directory in PROVIDERS_DIR.iterdir() if directory.is_dir() and not directory.name.startswith("__")
    )
    service_families = [family for family in provider_dirs if family not in set(model_providers) | {"playwright"}]

    service_rows: list[dict[str, Any]] = []
    for family in service_families:
        shared_catalog_path = SHARED_DIR / f"{family}.py"
        provider_catalog_path = PROVIDERS_DIR / family / "operations.py"
        catalog_source = shared_catalog_path if shared_catalog_path.exists() else provider_catalog_path
        service_rows.append(
            {
                "family": family,
                "operations": extract_catalog_count(catalog_source),
                "provider_path": relative_path(PROVIDERS_DIR / family),
                "tool_path": relative_path(TOOLS_DIR / family / "operations.py"),
                "catalog_path": relative_path(catalog_source),
            }
        )

    model_rows = [
        {
            "family": family,
            "provider_path": f"harnessiq/providers/{family}/",
        }
        for family in model_providers
    ]
    return model_rows, service_rows


def parse_tool_only_surfaces() -> list[dict[str, Any]]:
    resend_catalog_path = SHARED_DIR / "resend_catalog.py"
    return [
        {
            "family": "resend",
            "operations": extract_catalog_count(resend_catalog_path),
            "tool_path": "harnessiq/tools/resend.py",
            "catalog_path": relative_path(resend_catalog_path),
        }
    ]


def parse_tests() -> dict[str, Any]:
    test_files = sorted(TESTS_DIR.glob("test_*.py"))
    grouped: dict[str, list[str]] = defaultdict(list)
    for path in test_files:
        name = path.name
        if name.endswith("_provider.py"):
            group = "providers"
        elif name.endswith("_cli.py"):
            group = "cli"
        elif "agent" in name or "harness_manifests" in name:
            group = "agents"
        elif "tool" in name or "tools" in name or "toolset" in name:
            group = "tools"
        elif "ledger" in name or "output_sinks" in name:
            group = "ledger"
        else:
            group = "support"
        grouped[group].append(name)

    return {
        "count": len(test_files),
        "groups": [
            {
                "name": group,
                "count": len(files),
                "examples": files[:3],
            }
            for group, files in sorted(grouped.items())
        ],
    }


def parse_string_sequence(node: ast.AST | None, constants: dict[str, Any]) -> list[str]:
    if node is None:
        return []
    payload = eval_simple(node, constants)
    if isinstance(payload, str):
        return [payload]
    if isinstance(payload, (list, tuple, set, frozenset)):
        return [str(item) for item in payload]
    return []


def append_command(
    commands: list[dict[str, Any]],
    seen: set[tuple[str, ...]],
    *,
    path: tuple[str, ...],
    help_text: str,
    source_file: str,
    aliases: list[str] | None = None,
) -> None:
    if path in seen:
        return
    seen.add(path)
    commands.append(
        {
            "command": "harnessiq " + " ".join(path),
            "segments": list(path),
            "help": help_text,
            "source_file": source_file,
            "aliases": sorted(set(aliases or [])),
        }
    )


def append_platform_commands(
    commands: list[dict[str, Any]],
    seen: set[tuple[str, ...]],
    harnesses: list[dict[str, Any]],
) -> None:
    source_file = "harnessiq/cli/platform_commands.py"
    platform_roots = [
        ("prepare", "Prepare and persist generic config for a harness"),
        ("show", "Show persisted platform config and harness state"),
        ("run", "Run a harness through the platform-first CLI"),
        ("inspect", "Inspect one harness manifest and generated CLI surface"),
    ]
    for root, help_text in platform_roots:
        append_command(commands, seen, path=(root,), help_text=help_text, source_file=source_file)
        for harness in harnesses:
            aliases = [harness["cli_command"]] if harness["cli_command"] and harness["cli_command"] != harness["manifest_id"] else []
            append_command(
                commands,
                seen,
                path=(root, harness["manifest_id"]),
                help_text=f"{root} {harness['display_name']}",
                source_file=source_file,
                aliases=aliases,
            )

    append_command(
        commands,
        seen,
        path=("credentials",),
        help_text="Manage persisted harness credential bindings",
        source_file=source_file,
    )
    for action in ("bind", "show", "test"):
        append_command(
            commands,
            seen,
            path=("credentials", action),
            help_text=f"{action.title()} harness credentials",
            source_file=source_file,
        )
        for harness in harnesses:
            aliases = [harness["cli_command"]] if harness["cli_command"] and harness["cli_command"] != harness["manifest_id"] else []
            append_command(
                commands,
                seen,
                path=("credentials", action, harness["manifest_id"]),
                help_text=f"{action} {harness['display_name']}",
                source_file=source_file,
                aliases=aliases,
            )


def parse_cli_commands(harnesses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []
    seen: set[tuple[str, ...]] = set()

    for commands_file in sorted(CLI_DIR.glob("*/commands.py")):
        module = read_ast(commands_file)
        constants = collect_constants_from_path(commands_file)
        for statement in module.body:
            if not isinstance(statement, ast.FunctionDef) or not statement.name.startswith("register_"):
                continue
            if not statement.args.args:
                continue
            root_subparsers_name = statement.args.args[0].arg
            parser_paths: dict[str, tuple[str, ...]] = {}
            subparser_paths: dict[str, tuple[str, ...]] = {root_subparsers_name: ()}

            for inner in statement.body:
                if isinstance(inner, ast.Assign) and len(inner.targets) == 1 and isinstance(inner.targets[0], ast.Name) and isinstance(inner.value, ast.Call):
                    target_name = inner.targets[0].id
                    call = inner.value
                    if isinstance(call.func, ast.Attribute) and call.func.attr == "add_parser":
                        base_name = get_name(call.func.value)
                        if base_name not in subparser_paths:
                            continue
                        parser_name = get_call_arg(call, 0, "name")
                        help_value = get_call_keyword(call, "help")
                        aliases_value = get_call_keyword(call, "aliases")
                        if parser_name is None:
                            continue
                        segment = str(eval_simple(parser_name, constants))
                        path = subparser_paths[base_name] + (segment,)
                        parser_paths[target_name] = path
                        append_command(
                            commands,
                            seen,
                            path=path,
                            help_text=str(eval_simple(help_value, constants)) if help_value is not None else "",
                            source_file=relative_path(commands_file),
                            aliases=parse_string_sequence(aliases_value, constants),
                        )
                    elif isinstance(call.func, ast.Attribute) and call.func.attr == "add_subparsers":
                        base_name = get_name(call.func.value)
                        if base_name in parser_paths:
                            subparser_paths[target_name] = parser_paths[base_name]

                if isinstance(inner, ast.Expr) and isinstance(inner.value, ast.Call):
                    call = inner.value
                    if get_name(call.func) != "_register_connect_command" or len(call.args) < 2:
                        continue
                    base_name = get_name(call.args[0])
                    if base_name not in subparser_paths:
                        continue
                    segment = str(eval_simple(call.args[1], constants))
                    path = subparser_paths[base_name] + (segment,)
                    append_command(
                        commands,
                        seen,
                        path=path,
                        help_text=f"Configure a global {segment} sink",
                        source_file=relative_path(commands_file),
                    )

    append_platform_commands(commands, seen, harnesses)
    commands.sort(key=lambda item: item["segments"])
    return commands


def build_inventory() -> dict[str, Any]:
    harnesses = parse_harnesses()
    commands = parse_cli_commands(harnesses)
    model_providers = parse_supported_model_providers()
    model_provider_rows, service_provider_rows = parse_service_providers(model_providers)
    tool_only_rows = parse_tool_only_surfaces()
    sink_types = parse_builtin_sink_types()
    tests = parse_tests()

    top_level_dirs: list[dict[str, Any]] = []
    for directory in sorted(path for path in ROOT.iterdir() if path.is_dir() and path.name != ".git"):
        kind, description = TOP_LEVEL_DIRECTORY_DESCRIPTIONS.get(
            directory.name,
            ("other", "Repository directory not yet classified in the generated file index."),
        )
        top_level_dirs.append(
            {
                "name": directory.name,
                "path": f"{directory.name}/",
                "kind": kind,
                "description": description,
            }
        )

    package_layout_rows: list[dict[str, Any]] = []
    for package_path, description in PACKAGE_LAYOUT:
        directory = ROOT / package_path
        children = sorted(child.name for child in directory.iterdir() if child.is_dir() and not child.name.startswith("__"))
        package_layout_rows.append(
            {
                "path": package_path,
                "description": description,
                "children": children,
            }
        )

    focused_subpackage_rows = [
        {
            "path": path,
            "description": description,
        }
        for path, description in FOCUSED_SUBPACKAGE_DESCRIPTIONS
        if (ROOT / path).exists()
    ]

    top_level_commands = [command for command in commands if len(command["segments"]) == 1]
    direct_subcommands: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for command in commands:
        if len(command["segments"]) >= 2:
            direct_subcommands[command["segments"][0]].append(command)

    return {
        "counts": {
            "harnesses": len(harnesses),
            "top_level_commands": len(top_level_commands),
            "command_paths": 1 + sum(1 + len(command["aliases"]) for command in commands),
            "model_providers": len(model_provider_rows),
            "service_provider_packages": len(service_provider_rows),
            "tool_only_external_surfaces": len(tool_only_rows),
            "sink_types": len(sink_types),
            "test_modules": tests["count"],
        },
        "top_level_directories": top_level_dirs,
        "package_layout": package_layout_rows,
        "focused_subpackages": focused_subpackage_rows,
        "key_files": [
            {
                "path": path,
                "description": description,
            }
            for path, description in KEY_FILE_DESCRIPTIONS
            if (ROOT / path).exists()
        ],
        "harnesses": harnesses,
        "cli": {
            "commands": commands,
            "top_level": top_level_commands,
            "direct_subcommands": {
                root: sorted(items, key=lambda entry: entry["segments"])
                for root, items in sorted(direct_subcommands.items())
            },
        },
        "providers": {
            "model_providers": model_provider_rows,
            "service_providers": service_provider_rows,
            "tool_only_surfaces": tool_only_rows,
            "sink_types": sink_types,
        },
        "tests": tests,
    }


def format_cell(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, list):
        if not value:
            return "-"
        return ", ".join(format_cell(item) for item in value)
    if isinstance(value, tuple):
        if not value:
            return "-"
        return ", ".join(format_cell(item) for item in value)
    rendered = str(value).replace("|", "\\|").replace("\n", " ")
    return rendered or "-"


def make_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(format_cell(item) for item in row) + " |")
    return "\n".join(lines)


def render_counts_table(inventory: dict[str, Any]) -> str:
    counts = inventory["counts"]
    rows = [
        ["Concrete harness manifests", counts["harnesses"]],
        ["Top-level CLI commands", counts["top_level_commands"]],
        ["Registered CLI command paths", counts["command_paths"]],
        ["Model providers", counts["model_providers"]],
        ["Service provider packages", counts["service_provider_packages"]],
        ["Tool-only external service surfaces", counts["tool_only_external_surfaces"]],
        ["Built-in sink types", counts["sink_types"]],
        ["Test modules", counts["test_modules"]],
    ]
    return make_table(["Metric", "Count"], rows)


def format_direct_subcommand_labels(commands: list[dict[str, Any]]) -> list[str]:
    labels: list[str] = []
    for command in commands:
        segment = command["segments"][-1]
        aliases = command.get("aliases", [])
        if aliases:
            labels.append(f"{segment} ({', '.join(aliases)})")
            continue
        labels.append(segment)
    return labels


def render_readme(inventory: dict[str, Any]) -> str:
    counts = inventory["counts"]
    top_level_rows = []
    direct_subcommands = inventory["cli"]["direct_subcommands"]
    for command in inventory["cli"]["top_level"]:
        root = command["segments"][0]
        children = format_direct_subcommand_labels(
            [entry for entry in direct_subcommands.get(root, []) if len(entry["segments"]) == 2]
        )
        top_level_rows.append([command["command"], children, command["help"]])

    harness_rows = []
    for harness in inventory["harnesses"]:
        harness_rows.append(
            [
                harness["display_name"],
                f"`{harness['cli_command']}`" if harness["cli_command"] else "-",
                f"`{harness['module_path']}:{harness['class_name']}`",
                f"`{harness['default_memory_root']}`",
                format_parameter_surface(
                    harness["runtime_parameters"],
                    open_ended=harness.get("runtime_parameters_open_ended", False),
                ),
                format_parameter_surface(
                    harness["custom_parameters"],
                    open_ended=harness.get("custom_parameters_open_ended", False),
                ),
                harness["provider_families"],
            ]
        )

    provider_rows = []
    for provider in inventory["providers"]["service_providers"]:
        provider_rows.append(
            [
                provider["family"],
                provider["operations"],
                f"`{provider['provider_path']}`",
                f"`{provider['tool_path']}`",
            ]
        )

    tool_only_rows = []
    for provider in inventory["providers"]["tool_only_surfaces"]:
        tool_only_rows.append([provider["family"], provider["operations"], f"`{provider['tool_path']}`"])

    model_rows = [
        [provider["family"], f"`{provider['provider_path']}`"]
        for provider in inventory["providers"]["model_providers"]
    ]

    lines = [
        "# Harnessiq",
        "",
        "Harnessiq is a Python SDK for building durable, tool-using agents with manifest-backed harnesses, provider-backed tool factories, and a scriptable CLI.",
        "",
        "The agent, provider, and CLI tables below are generated from live repository code by `python scripts/sync_repo_docs.py`.",
        "",
        "## Install",
        "",
        "```bash",
        "pip install harnessiq",
        "```",
        "",
        "For local development from this repository:",
        "",
        "```bash",
        "pip install -e .",
        "```",
        "",
        "## Quick Start",
        "",
        "```python",
        "from harnessiq.tools import ECHO_TEXT, create_builtin_registry",
        "",
        "registry = create_builtin_registry()",
        "result = registry.execute(ECHO_TEXT, {\"text\": \"hello\"})",
        "print(result.output)",
        "```",
        "",
        "## Live Snapshot",
        "",
        render_counts_table(inventory),
        "",
        "## Agent Matrix",
        "",
        make_table(
            ["Harness", "CLI", "Import", "Memory Root", "Runtime Params", "Custom Params", "Providers"],
            harness_rows,
        ),
        "",
        "## Provider Surface",
        "",
        (
            f"Harnessiq currently ships {counts['model_providers']} model-provider adapters, "
            f"{counts['service_provider_packages']} service provider packages under `harnessiq/providers/`, "
            f"and {counts['tool_only_external_surfaces']} tool-only external service surface"
            f"{'' if counts['tool_only_external_surfaces'] == 1 else 's'} "
            f"outside the provider package tree."
        ),
        "",
        "### Model Providers",
        "",
        make_table(["Provider", "Package"], model_rows),
        "",
        "### Service Providers",
        "",
        make_table(["Family", "Ops", "Provider Package", "Tool Factory"], provider_rows),
        "",
        "### Tool-Only External Surfaces",
        "",
        make_table(["Family", "Ops", "Tool Surface"], tool_only_rows),
        "",
        "## CLI",
        "",
        "The generated command catalog lives at `artifacts/commands.md`. Use it as the high-signal reference for the live command tree.",
        "",
        make_table(["Command", "Direct Subcommands", "Description"], top_level_rows),
        "",
        "## Repo Docs",
        "",
    ]
    for path, description in README_DOC_LINKS:
        lines.append(f"- `{path}`: {description}")
    return "\n".join(lines)


def render_commands_artifact(inventory: dict[str, Any]) -> str:
    lines = [
        "# Harnessiq CLI Reference",
        "",
        "This artifact is generated from the live `harnessiq/cli/` source tree by `python scripts/sync_repo_docs.py`.",
        "",
        "## Snapshot",
        "",
        make_table(
            ["Metric", "Count"],
            [
                ["Top-level commands", inventory["counts"]["top_level_commands"]],
                ["Registered command paths", inventory["counts"]["command_paths"]],
            ],
        ),
        "",
        "Alias paths are included in the registered command total. Canonical commands list aliases where they exist.",
        "",
        "## Top-Level Commands",
        "",
    ]

    top_level_rows = []
    direct_subcommands = inventory["cli"]["direct_subcommands"]
    for command in inventory["cli"]["top_level"]:
        root = command["segments"][0]
        children = format_direct_subcommand_labels(
            [entry for entry in direct_subcommands.get(root, []) if len(entry["segments"]) == 2]
        )
        top_level_rows.append([command["command"], children, command["help"], f"`{command['source_file']}`"])
    lines.append(make_table(["Command", "Direct Subcommands", "Description", "Source"], top_level_rows))
    lines.append("")

    for command in inventory["cli"]["top_level"]:
        root = command["segments"][0]
        children = [entry for entry in direct_subcommands.get(root, []) if len(entry["segments"]) >= 2]
        if not children:
            continue
        has_aliases = any(entry["aliases"] for entry in children)
        section_headers = ["Command", "Aliases", "Description", "Source"] if has_aliases else ["Command", "Description", "Source"]
        section_rows: list[list[Any]] = []
        for entry in children:
            if has_aliases:
                section_rows.append(
                    [
                        entry["command"],
                        entry["aliases"],
                        entry["help"],
                        f"`{entry['source_file']}`",
                    ]
                )
            else:
                section_rows.append([entry["command"], entry["help"], f"`{entry['source_file']}`"])
        lines.extend(
            [
                f"## `{command['command']}`",
                "",
                make_table(section_headers, section_rows),
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def render_file_index(inventory: dict[str, Any]) -> str:
    top_level_rows = [[f"`{entry['path']}`", entry["kind"], entry["description"]] for entry in inventory["top_level_directories"]]
    package_rows = [[f"`{entry['path']}`", entry["children"], entry["description"]] for entry in inventory["package_layout"]]
    focused_subpackage_rows = [[f"`{entry['path']}`", entry["description"]] for entry in inventory["focused_subpackages"]]
    key_file_rows = [[f"`{entry['path']}`", entry["description"]] for entry in inventory["key_files"]]

    harness_rows = []
    for harness in inventory["harnesses"]:
        harness_rows.append(
            [
                harness["manifest_id"],
                harness["display_name"],
                f"`{harness['module_path']}:{harness['class_name']}`",
                f"`{harness['default_memory_root']}`",
                format_parameter_surface(
                    harness["runtime_parameters"],
                    open_ended=harness.get("runtime_parameters_open_ended", False),
                ),
                format_parameter_surface(
                    harness["custom_parameters"],
                    open_ended=harness.get("custom_parameters_open_ended", False),
                ),
                [item["relative_path"] for item in harness["memory_files"]],
                harness["provider_families"],
                harness["output_fields"],
            ]
        )

    cli_rows = []
    direct_subcommands = inventory["cli"]["direct_subcommands"]
    for command in inventory["cli"]["top_level"]:
        root = command["segments"][0]
        children = format_direct_subcommand_labels(
            [entry for entry in direct_subcommands.get(root, []) if len(entry["segments"]) == 2]
        )
        cli_rows.append([command["command"], children, command["help"], f"`{command['source_file']}`"])

    model_rows = [[provider["family"], f"`{provider['provider_path']}`"] for provider in inventory["providers"]["model_providers"]]
    provider_rows = [
        [provider["family"], provider["operations"], f"`{provider['provider_path']}`", f"`{provider['tool_path']}`", f"`{provider['catalog_path']}`"]
        for provider in inventory["providers"]["service_providers"]
    ]
    tool_only_rows = [
        [provider["family"], provider["operations"], f"`{provider['tool_path']}`", f"`{provider['catalog_path']}`"]
        for provider in inventory["providers"]["tool_only_surfaces"]
    ]
    test_rows = [
        [group["name"], group["count"], [f"`tests/{name}`" for name in group["examples"]]]
        for group in inventory["tests"]["groups"]
    ]

    lines = [
        "# Repository File Index",
        "",
        "This artifact is generated from the live repository tree and source files by `python scripts/sync_repo_docs.py`.",
        "",
        "It is intentionally high-signal rather than exhaustive: the goal is to explain the active architectural shape of the repo, show where major responsibilities live, and make drift visible when the source tree changes.",
        "",
        "## Snapshot",
        "",
        render_counts_table(inventory),
        "",
        "## Codebase Standards",
        "",
    ]
    for item in FILE_INDEX_STANDARDS:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Top-Level Directories",
            "",
            make_table(["Path", "Kind", "Responsibility"], top_level_rows),
            "",
            "## Package Layout",
            "",
            make_table(["Path", "Live Subpackages", "Responsibility"], package_rows),
            "",
            "## Focused Subpackages",
            "",
            make_table(["Path", "Responsibility"], focused_subpackage_rows),
            "",
            "## Key Files",
            "",
            make_table(["Path", "Responsibility"], key_file_rows),
            "",
            "## Harness Registry",
            "",
            make_table(["Manifest", "Display Name", "Import", "Memory Root", "Runtime Params", "Custom Params", "Memory Entries", "Providers", "Output Fields"], harness_rows),
            "",
            "## CLI Architecture",
            "",
            make_table(["Command", "Direct Subcommands", "Description", "Source"], cli_rows),
            "",
            "## Provider Surfaces",
            "",
            "### Model Providers",
            "",
            make_table(["Provider", "Package"], model_rows),
            "",
            "### Service Provider Packages",
            "",
            make_table(["Family", "Ops", "Provider Package", "Tool Surface", "Catalog Source"], provider_rows),
            "",
            "### Tool-Only External Service Surfaces",
            "",
            make_table(["Family", "Ops", "Tool Surface", "Catalog Source"], tool_only_rows),
            "",
            "### Built-In Output Sink Types",
            "",
            make_table(["Sink Type"], [[f"`{sink_type}`"] for sink_type in inventory["providers"]["sink_types"]]),
            "",
            "## Test Surface",
            "",
            f"`tests/` currently contains {inventory['tests']['count']} test modules. The table below groups them by dominant responsibility.",
            "",
            make_table(["Area", "Count", "Examples"], test_rows),
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_inventory_json(inventory: dict[str, Any]) -> str:
    return json.dumps(inventory, indent=2, sort_keys=True) + "\n"


def format_parameter_surface(
    parameters: list[dict[str, Any]],
    *,
    open_ended: bool,
) -> list[str] | str:
    keys = [item["key"] for item in parameters]
    if keys and open_ended:
        return [*keys, "open-ended"]
    if keys:
        return keys
    if open_ended:
        return "open-ended"
    return "-"


def expected_outputs() -> dict[Path, str]:
    inventory = build_inventory()
    return {
        ARTIFACTS_DIR / "live_inventory.json": render_inventory_json(inventory),
        ARTIFACTS_DIR / "commands.md": render_commands_artifact(inventory),
        ARTIFACTS_DIR / "file_index.md": render_file_index(inventory),
        ROOT / "README.md": render_readme(inventory).rstrip() + "\n",
    }


def write_outputs(outputs: dict[Path, str]) -> None:
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def check_outputs(outputs: dict[Path, str]) -> list[str]:
    drifted: list[str] = []
    for path, content in outputs.items():
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            drifted.append(relative_path(path))
    return drifted


def main() -> int:
    args = parse_args()
    outputs = expected_outputs()
    if args.check:
        drifted = check_outputs(outputs)
        if drifted:
            print("The following generated docs are out of date:")
            for item in drifted:
                print(f"- {item}")
            return 1
        print("Generated docs are in sync.")
        return 0

    write_outputs(outputs)
    print("Updated generated docs:")
    for path in outputs:
        print(f"- {relative_path(path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
