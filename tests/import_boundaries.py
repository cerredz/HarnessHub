"""AST-based import-boundary checks for the Harnessiq package graph."""

from __future__ import annotations

import ast
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

_SHARED_FORBIDDEN_TOP_LEVEL_IMPORTS = frozenset({"agents", "cli", "providers", "tools"})
_CLI_FORBIDDEN_TOP_LEVEL_IMPORTS = frozenset({"providers", "tools", "toolset"})


@dataclass(frozen=True, slots=True)
class ImportReference:
    importer_path: Path
    importer_top_level: str
    imported_module: str
    imported_top_level: str
    lineno: int

    def render(self) -> str:
        return f"{self.importer_path.as_posix()}:{self.lineno}"


def find_import_boundary_violations(package_root: Path) -> list[str]:
    references = discover_import_references(package_root)
    tool_seam_families = discover_provider_tool_seam_families(package_root)
    violations: list[str] = []

    for reference in references:
        if reference.importer_top_level == "shared" and reference.imported_top_level in _SHARED_FORBIDDEN_TOP_LEVEL_IMPORTS:
            violations.append(
                f"{reference.render()} shared must not import {reference.imported_module}"
            )
        if reference.importer_top_level == "agents" and _uses_provider_tool_seam(reference, tool_seam_families):
            violations.append(
                f"{reference.render()} agents must use the tool seam instead of importing {reference.imported_module}"
            )
        if reference.importer_top_level == "cli" and reference.imported_top_level in _CLI_FORBIDDEN_TOP_LEVEL_IMPORTS:
            violations.append(
                f"{reference.render()} cli must stay above provider/tool/toolset internals, not import {reference.imported_module}"
            )

    for cycle in find_top_level_package_cycles(package_root):
        rendered_cycle = " -> ".join([*cycle, cycle[0]])
        violations.append(f"top-level package cycle detected: {rendered_cycle}")

    return sorted(violations)


def discover_import_references(package_root: Path) -> list[ImportReference]:
    top_level_packages = discover_top_level_packages(package_root)
    references: list[ImportReference] = []

    for path in sorted(package_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        importer_path = path.relative_to(package_root)
        importer_top_level = importer_path.parts[0]
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name
                    if not module.startswith("harnessiq."):
                        continue
                    resolved = _build_reference(
                        importer_path=importer_path,
                        importer_top_level=importer_top_level,
                        imported_module=module,
                        lineno=node.lineno,
                    )
                    if resolved is not None:
                        references.append(resolved)
            elif isinstance(node, ast.ImportFrom):
                module = _resolve_import_from_module(
                    importer_path=importer_path,
                    node=node,
                    top_level_packages=top_level_packages,
                )
                if module is None:
                    continue
                resolved = _build_reference(
                    importer_path=importer_path,
                    importer_top_level=importer_top_level,
                    imported_module=module,
                    lineno=node.lineno,
                )
                if resolved is not None:
                    references.append(resolved)

    return references


def discover_top_level_packages(package_root: Path) -> tuple[str, ...]:
    packages = [
        path.name
        for path in sorted(package_root.iterdir())
        if path.is_dir() and path.name != "__pycache__"
    ]
    return tuple(packages)


def discover_provider_tool_seam_families(package_root: Path) -> frozenset[str]:
    providers_root = package_root / "providers"
    tools_root = package_root / "tools"
    families = {
        path.name
        for path in providers_root.iterdir()
        if path.is_dir() and (tools_root / path.name).is_dir()
    }
    return frozenset(families)


def find_top_level_package_cycles(package_root: Path) -> list[tuple[str, ...]]:
    graph: dict[str, set[str]] = defaultdict(set)
    for reference in discover_import_references(package_root):
        if reference.imported_top_level == reference.importer_top_level:
            continue
        graph[reference.importer_top_level].add(reference.imported_top_level)

    index = 0
    stack: list[str] = []
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    on_stack: set[str] = set()
    strongly_connected_components: list[tuple[str, ...]] = []

    def strongconnect(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for neighbor in sorted(graph.get(node, ())):
            if neighbor not in indices:
                strongconnect(neighbor)
                lowlinks[node] = min(lowlinks[node], lowlinks[neighbor])
            elif neighbor in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[neighbor])

        if lowlinks[node] != indices[node]:
            return

        component: list[str] = []
        while stack:
            candidate = stack.pop()
            on_stack.remove(candidate)
            component.append(candidate)
            if candidate == node:
                break
        if len(component) > 1:
            strongly_connected_components.append(tuple(sorted(component)))

    for node in discover_top_level_packages(package_root):
        if node not in indices:
            strongconnect(node)

    return sorted(set(strongly_connected_components))


def _build_reference(
    *,
    importer_path: Path,
    importer_top_level: str,
    imported_module: str,
    lineno: int,
) -> ImportReference | None:
    parts = imported_module.split(".")
    if len(parts) < 2:
        return None
    imported_top_level = parts[1]
    return ImportReference(
        importer_path=importer_path,
        importer_top_level=importer_top_level,
        imported_module=imported_module,
        imported_top_level=imported_top_level,
        lineno=lineno,
    )


def _resolve_import_from_module(
    *,
    importer_path: Path,
    node: ast.ImportFrom,
    top_level_packages: tuple[str, ...],
) -> str | None:
    if node.module and node.module.startswith("harnessiq."):
        return node.module

    if node.level <= 0:
        return None

    package_parts = list(importer_path.parts[:-1])
    parent_index = len(package_parts) - (node.level - 1)
    if parent_index < 0:
        return None
    resolved_parts = package_parts[:parent_index]
    if node.module:
        resolved_parts.extend(node.module.split("."))
    if not resolved_parts or resolved_parts[0] not in top_level_packages:
        return None
    return f"harnessiq.{'.'.join(resolved_parts)}"


def _uses_provider_tool_seam(reference: ImportReference, tool_seam_families: frozenset[str]) -> bool:
    parts = reference.imported_module.split(".")
    if len(parts) < 3 or parts[1] != "providers":
        return False
    return parts[2] in tool_seam_families
