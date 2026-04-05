"""Architecture tests for import-boundary enforcement."""

from __future__ import annotations

import textwrap
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from tests.import_boundaries import (
    discover_provider_tool_seam_families,
    find_import_boundary_violations,
    find_top_level_package_cycles,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


class ImportBoundaryTests(unittest.TestCase):
    def test_repo_has_no_import_boundary_violations(self) -> None:
        violations = find_import_boundary_violations(REPO_ROOT / "harnessiq")
        self.assertEqual(violations, [])

    def test_detects_shared_importing_tools(self) -> None:
        with TemporaryDirectory() as temp_dir:
            package_root = _build_minimal_package(Path(temp_dir))
            _write(
                package_root / "shared" / "example.py",
                """
                from harnessiq.tools.resend import ResendClient
                """,
            )

            violations = find_import_boundary_violations(package_root)

            self.assertIn(
                "shared/example.py:1 shared must not import harnessiq.tools.resend",
                violations,
            )

    def test_detects_agents_reaching_into_provider_family_with_tool_seam(self) -> None:
        with TemporaryDirectory() as temp_dir:
            package_root = _build_minimal_package(Path(temp_dir))
            _write(package_root / "providers" / "exa" / "__init__.py", "")
            _write(package_root / "tools" / "exa" / "__init__.py", "")
            _write(
                package_root / "agents" / "example.py",
                """
                from harnessiq.providers.exa.client import ExaClient
                """,
            )

            violations = find_import_boundary_violations(package_root)

            self.assertIn(
                "agents/example.py:1 agents must use the tool seam instead of importing harnessiq.providers.exa.client",
                violations,
            )

    def test_allows_agents_importing_provider_surface_without_tool_seam(self) -> None:
        with TemporaryDirectory() as temp_dir:
            package_root = _build_minimal_package(Path(temp_dir))
            _write(package_root / "providers" / "output_sinks.py", "")
            _write(
                package_root / "agents" / "example.py",
                """
                from harnessiq.providers.output_sinks import extract_model_metadata
                """,
            )

            violations = find_import_boundary_violations(package_root)

            self.assertEqual(violations, [])

    def test_detects_cli_reaching_into_tool_layer(self) -> None:
        with TemporaryDirectory() as temp_dir:
            package_root = _build_minimal_package(Path(temp_dir))
            _write(
                package_root / "cli" / "example.py",
                """
                from harnessiq.tools.filesystem import create_filesystem_tools
                """,
            )

            violations = find_import_boundary_violations(package_root)

            self.assertIn(
                "cli/example.py:1 cli must stay above provider/tool/toolset internals, not import harnessiq.tools.filesystem",
                violations,
            )

    def test_detects_top_level_package_cycles(self) -> None:
        with TemporaryDirectory() as temp_dir:
            package_root = _build_minimal_package(Path(temp_dir))
            _write(
                package_root / "shared" / "cycle.py",
                """
                from harnessiq.utils.state import read_state
                """,
            )
            _write(
                package_root / "utils" / "state.py",
                """
                from harnessiq.shared.types import SharedType
                """,
            )

            cycles = find_top_level_package_cycles(package_root)

            self.assertEqual(cycles, [("shared", "utils")])

    def test_discovers_provider_tool_seam_families_from_matching_directories(self) -> None:
        with TemporaryDirectory() as temp_dir:
            package_root = _build_minimal_package(Path(temp_dir))
            _write(package_root / "providers" / "exa" / "__init__.py", "")
            _write(package_root / "tools" / "exa" / "__init__.py", "")
            _write(package_root / "providers" / "output_sinks.py", "")

            seam_families = discover_provider_tool_seam_families(package_root)

            self.assertEqual(seam_families, frozenset({"exa"}))


def _build_minimal_package(root: Path) -> Path:
    package_root = root / "harnessiq"
    for name in ("agents", "cli", "config", "providers", "shared", "tools", "toolset", "utils"):
        (package_root / name).mkdir(parents=True, exist_ok=True)
        _write(package_root / name / "__init__.py", "")
    return package_root


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
