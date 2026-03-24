"""Packaging smoke tests for the Harnessiq SDK."""

from __future__ import annotations

import ast
import io
import logging
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from setuptools.build_meta import build_sdist, build_wheel


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT_ALLOWED_LOCAL_CONSTANTS = {
    "_PROMPTS_DIR",
    "_MASTER_PROMPT_PATH",
    "_DEFAULT_MEMORY_PATH",
    "_CONTEXT_STATE_FILENAME",
    "_CONTEXT_MEMORY_SECTION_TITLE",
    "_DIRECTIVE_PRIORITY_ORDER",
}
PROVIDER_ALLOWED_LOCAL_CONSTANTS = {
    "P",
    "R",
    "SHORTCUT_MIME_TYPE",
    "_DEFAULT_FILE_FIELDS",
    "_DEFAULT_PERMISSION_FIELDS",
}
SHARED_CLASS_SUFFIXES = ("Config", "Credentials", "Operation", "PreparedRequest", "Error")


class HarnessiqPackageTests(unittest.TestCase):
    def test_top_level_package_exposes_sdk_modules(self) -> None:
        import harnessiq

        self.assertEqual(harnessiq.__version__, "0.1.0")
        self.assertTrue(hasattr(harnessiq, "agents"))
        self.assertTrue(hasattr(harnessiq, "cli"))
        self.assertTrue(hasattr(harnessiq, "config"))
        self.assertTrue(hasattr(harnessiq, "integrations"))
        self.assertTrue(hasattr(harnessiq, "tools"))
        self.assertTrue(hasattr(harnessiq, "providers"))

    def test_package_builds_wheel_and_sdist_and_imports_from_wheel(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            build_output = io.StringIO()
            previous_disable_level = logging.root.manager.disable
            logging.disable(logging.CRITICAL)
            try:
                with redirect_stdout(build_output), redirect_stderr(build_output):
                    sdist_name = build_sdist(str(temp_path))
                    wheel_name = build_wheel(str(temp_path))
            finally:
                logging.disable(previous_disable_level)
            wheel_path = temp_path / wheel_name

            self.assertTrue((temp_path / sdist_name).exists())
            self.assertTrue(wheel_path.exists())

            smoke = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        f"import sys; sys.path.insert(0, r'{wheel_path}'); "
                        "import harnessiq, harnessiq.agents, harnessiq.config, harnessiq.integrations, harnessiq.tools, harnessiq.utils; "
                        "from harnessiq.cli.main import main as cli_main; "
                        "assert harnessiq.__version__ == '0.1.0'; "
                        "assert hasattr(harnessiq.agents, 'BaseProviderToolAgent'); "
                        "assert hasattr(harnessiq.agents, 'BaseApolloAgent'); "
                        "assert hasattr(harnessiq.agents, 'BaseExaAgent'); "
                        "assert hasattr(harnessiq.agents, 'BaseInstantlyAgent'); "
                        "assert hasattr(harnessiq.agents, 'BaseOutreachAgent'); "
                        "assert hasattr(harnessiq.agents, 'ApolloAgentConfig'); "
                        "assert hasattr(harnessiq.agents, 'ExaAgentConfig'); "
                        "assert hasattr(harnessiq.agents, 'InstantlyAgentConfig'); "
                        "assert hasattr(harnessiq.agents, 'OutreachAgentConfig'); "
                        "assert hasattr(harnessiq.agents, 'LinkedInJobApplierAgent'); "
                        "assert hasattr(harnessiq.agents, 'json_parameter_section'); "
                        "assert hasattr(harnessiq.agents, 'get_harness_manifest'); "
                        "assert hasattr(harnessiq.agents, 'InstagramKeywordDiscoveryAgent'); "
                        "assert hasattr(harnessiq.agents, 'GoogleMapsProspectingAgent'); "
                        "assert hasattr(harnessiq.integrations, 'create_model_from_spec'); "
                        "assert callable(cli_main); "
                        "assert hasattr(harnessiq.config, 'CredentialsConfigStore'); "
                        "assert hasattr(harnessiq.tools, 'create_builtin_registry'); "
                        "assert hasattr(harnessiq.tools, 'create_tool_registry'); "
                        "assert hasattr(harnessiq.utils, 'register_output_sink')"
                    ),
                ],
                check=True,
                cwd=temp_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertEqual(smoke.returncode, 0)

    def test_cli_module_help_executes(self) -> None:
        help_run = subprocess.run(
            [sys.executable, "-m", "harnessiq.cli", "--help"],
            check=True,
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        self.assertIn("linkedin", help_run.stdout)
        self.assertIn("instagram", help_run.stdout)
        self.assertIn("models", help_run.stdout)
        self.assertIn("prospecting", help_run.stdout)
        self.assertEqual(help_run.returncode, 0)

    def test_shared_definition_exports_originate_from_shared_modules(self) -> None:
        from harnessiq.agents import (
            ApolloAgentConfig,
            EmailAgentConfig,
            ExaAgentConfig,
            InstantlyAgentConfig,
            OutreachAgentConfig,
        )
        from harnessiq.providers import ProviderFormatError, ProviderHTTPError
        from harnessiq.providers.arxiv import ArxivConfig
        from harnessiq.providers.arcads import ArcadsOperation
        from harnessiq.tools import ResendCredentials

        self.assertEqual(ApolloAgentConfig.__module__, "harnessiq.shared.apollo_agent")
        self.assertEqual(EmailAgentConfig.__module__, "harnessiq.shared.email")
        self.assertEqual(ExaAgentConfig.__module__, "harnessiq.shared.exa_agent")
        self.assertEqual(InstantlyAgentConfig.__module__, "harnessiq.shared.instantly_agent")
        self.assertEqual(OutreachAgentConfig.__module__, "harnessiq.shared.outreach_agent")
        self.assertEqual(ProviderFormatError.__module__, "harnessiq.shared.providers")
        self.assertEqual(ProviderHTTPError.__module__, "harnessiq.shared.http")
        self.assertEqual(ArxivConfig.__module__, "harnessiq.shared.provider_configs")
        self.assertEqual(ArcadsOperation.__module__, "harnessiq.shared.arcads")
        self.assertEqual(ResendCredentials.__module__, "harnessiq.shared.resend")

    def test_provider_base_exports_resolve_from_documented_modules(self) -> None:
        from harnessiq.agents import (
            BaseApolloAgent,
            BaseExaAgent,
            BaseInstantlyAgent,
            BaseOutreachAgent,
            BaseProviderToolAgent,
        )

        self.assertEqual(BaseProviderToolAgent.__module__, "harnessiq.agents.provider_base.agent")
        self.assertEqual(BaseApolloAgent.__module__, "harnessiq.agents.apollo.agent")
        self.assertEqual(BaseExaAgent.__module__, "harnessiq.agents.exa.agent")
        self.assertEqual(BaseInstantlyAgent.__module__, "harnessiq.agents.instantly.agent")
        self.assertEqual(BaseOutreachAgent.__module__, "harnessiq.agents.outreach.agent")

    def test_agents_and_providers_keep_shared_definitions_out_of_local_modules(self) -> None:
        violations: list[str] = []
        for root_name, root_path in (
            ("agents", REPO_ROOT / "harnessiq" / "agents"),
            ("providers", REPO_ROOT / "harnessiq" / "providers"),
        ):
            for path in root_path.rglob("*.py"):
                tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
                for statement in tree.body:
                    if isinstance(statement, ast.ClassDef) and statement.name.endswith(SHARED_CLASS_SUFFIXES):
                        violations.append(f"{path.relative_to(REPO_ROOT)} defines class {statement.name}")
                    for name in _assigned_names(statement):
                        if not _looks_like_constant(name):
                            continue
                        if root_name == "agents" and name in AGENT_ALLOWED_LOCAL_CONSTANTS:
                            continue
                        if root_name == "providers" and name in PROVIDER_ALLOWED_LOCAL_CONSTANTS:
                            continue
                        violations.append(f"{path.relative_to(REPO_ROOT)} defines constant {name}")

        self.assertEqual(violations, [])


def _assigned_names(statement: ast.stmt) -> list[str]:
    if isinstance(statement, ast.Assign):
        return [target.id for target in statement.targets if isinstance(target, ast.Name)]
    if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
        return [statement.target.id]
    return []


def _looks_like_constant(name: str) -> bool:
    if name == "__all__":
        return False
    if name.isupper():
        return True
    return name.startswith("_") and name[1:].isupper()


if __name__ == "__main__":
    unittest.main()
