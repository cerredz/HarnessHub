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
PROVIDER_HYGIENE_EXCLUDED_PREFIXES = (
    Path("harnessiq/providers/gcloud"),
)


class HarnessiqPackageTests(unittest.TestCase):
    def test_top_level_package_exposes_sdk_modules(self) -> None:
        import harnessiq

        self.assertEqual(harnessiq.__version__, "0.1.0")
        self.assertTrue(hasattr(harnessiq, "agents"))
        self.assertTrue(hasattr(harnessiq, "cli"))
        self.assertTrue(hasattr(harnessiq, "config"))
        self.assertTrue(hasattr(harnessiq, "evaluations"))
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
                        "import harnessiq, harnessiq.agents, harnessiq.config, harnessiq.integrations, harnessiq.shared, harnessiq.tools, harnessiq.utils; "
                        "from harnessiq.shared.dtos import AgentInstancePayload, OpenAIChatCompletionRequestDTO, ProviderMessageDTO; "
                        "from harnessiq.providers import AnthropicMessageRequestDTO, GeminiGenerateContentRequestDTO, GrokChatCompletionRequestDTO; "
                        "from harnessiq.providers.openai import OpenAIResponseRequestDTO; "
                        "from harnessiq.cli.main import main as cli_main; "
                        "assert harnessiq.__version__ == '0.1.0'; "
                        "assert hasattr(harnessiq, 'evaluations'); "
                        "assert hasattr(harnessiq.evaluations, 'score_efficiency'); "
                        "assert hasattr(harnessiq.evaluations, 'llm_judge'); "
                        "assert hasattr(harnessiq.shared, 'dtos'); "
                        "assert AgentInstancePayload.__module__ == 'harnessiq.shared.dtos.agents'; "
                        "assert OpenAIChatCompletionRequestDTO.__module__ == 'harnessiq.shared.dtos.providers'; "
                        "assert ProviderMessageDTO.__module__ == 'harnessiq.shared.dtos.providers'; "
                        "assert AnthropicMessageRequestDTO.__module__ == 'harnessiq.shared.dtos.providers'; "
                        "assert GeminiGenerateContentRequestDTO.__module__ == 'harnessiq.shared.dtos.providers'; "
                        "assert GrokChatCompletionRequestDTO.__module__ == 'harnessiq.shared.dtos.providers'; "
                        "assert OpenAIResponseRequestDTO.__module__ == 'harnessiq.shared.dtos.providers'; "
                        "assert hasattr(harnessiq.agents, 'BaseProviderToolAgent'); "
                        "assert hasattr(harnessiq.agents, 'BaseApolloAgent'); "
                        "assert hasattr(harnessiq.agents, 'BaseExaAgent'); "
                        "assert hasattr(harnessiq.agents, 'BaseInstantlyAgent'); "
                        "assert hasattr(harnessiq.agents, 'BaseOutreachAgent'); "
                        "assert hasattr(harnessiq.agents, 'ApolloAgentRequest'); "
                        "assert hasattr(harnessiq.agents, 'ApolloAgentConfig'); "
                        "assert hasattr(harnessiq.agents, 'EmailAgentRequest'); "
                        "assert hasattr(harnessiq.agents, 'ExaAgentConfig'); "
                        "assert hasattr(harnessiq.agents, 'ExaAgentRequest'); "
                        "assert hasattr(harnessiq.agents, 'InstantlyAgentRequest'); "
                        "assert hasattr(harnessiq.agents, 'InstantlyAgentConfig'); "
                        "assert hasattr(harnessiq.agents, 'OutreachAgentRequest'); "
                        "assert hasattr(harnessiq.agents, 'OutreachAgentConfig'); "
                        "assert hasattr(harnessiq.agents, 'LinkedInJobApplierAgent'); "
                        "assert hasattr(harnessiq.agents, 'json_parameter_section'); "
                        "assert hasattr(harnessiq.agents, 'get_harness_manifest'); "
                        "assert hasattr(harnessiq.agents, 'InstagramKeywordDiscoveryAgent'); "
                        "assert hasattr(harnessiq.agents, 'GoogleMapsProspectingAgent'); "
                        "assert hasattr(harnessiq.integrations, 'create_model_from_spec'); "
                        "assert hasattr(harnessiq.toolset, 'DefaultDynamicToolSelector'); "
                        "assert hasattr(harnessiq.toolset, 'resolve_tool_profiles'); "
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
            ApolloAgentRequest,
            EmailAgentConfig,
            EmailAgentRequest,
            ExaAgentConfig,
            ExaAgentRequest,
            InstantlyAgentConfig,
            InstantlyAgentRequest,
            OutreachAgentConfig,
            OutreachAgentRequest,
        )
        from harnessiq.providers import (
            AnthropicMessageRequestDTO,
            GeminiGenerateContentRequestDTO,
            GrokChatCompletionRequestDTO,
            OpenAIChatCompletionRequestDTO,
            ProviderFormatError,
            ProviderHTTPError,
            ProviderMessageDTO,
        )
        from harnessiq.providers.arxiv import ArxivConfig
        from harnessiq.providers.arcads import ArcadsOperation
        from harnessiq.providers.openai import OpenAIResponseRequestDTO
        from harnessiq.shared.dtos import AgentInstancePayload, HarnessCommandPayloadDTO, HarnessRunSnapshotDTO
        from harnessiq.tools import ResendCredentials

        self.assertEqual(AgentInstancePayload.__module__, "harnessiq.shared.dtos.agents")
        self.assertEqual(HarnessCommandPayloadDTO.__module__, "harnessiq.shared.dtos.cli")
        self.assertEqual(HarnessRunSnapshotDTO.__module__, "harnessiq.shared.dtos.cli")
        self.assertEqual(ApolloAgentRequest.__module__, "harnessiq.shared.dtos.agents")
        self.assertEqual(ApolloAgentConfig.__module__, "harnessiq.shared.apollo_agent")
        self.assertEqual(EmailAgentRequest.__module__, "harnessiq.shared.dtos.agents")
        self.assertEqual(EmailAgentConfig.__module__, "harnessiq.shared.email")
        self.assertEqual(ExaAgentRequest.__module__, "harnessiq.shared.dtos.agents")
        self.assertEqual(ExaAgentConfig.__module__, "harnessiq.shared.exa_agent")
        self.assertEqual(InstantlyAgentRequest.__module__, "harnessiq.shared.dtos.agents")
        self.assertEqual(InstantlyAgentConfig.__module__, "harnessiq.shared.instantly_agent")
        self.assertEqual(OutreachAgentRequest.__module__, "harnessiq.shared.dtos.agents")
        self.assertEqual(OutreachAgentConfig.__module__, "harnessiq.shared.outreach_agent")
        self.assertEqual(ProviderMessageDTO.__module__, "harnessiq.shared.dtos.providers")
        self.assertEqual(OpenAIChatCompletionRequestDTO.__module__, "harnessiq.shared.dtos.providers")
        self.assertEqual(OpenAIResponseRequestDTO.__module__, "harnessiq.shared.dtos.providers")
        self.assertEqual(AnthropicMessageRequestDTO.__module__, "harnessiq.shared.dtos.providers")
        self.assertEqual(GeminiGenerateContentRequestDTO.__module__, "harnessiq.shared.dtos.providers")
        self.assertEqual(GrokChatCompletionRequestDTO.__module__, "harnessiq.shared.dtos.providers")
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
                relative_path = path.relative_to(REPO_ROOT)
                if root_name == "providers" and any(
                    relative_path.is_relative_to(prefix) for prefix in PROVIDER_HYGIENE_EXCLUDED_PREFIXES
                ):
                    continue
                tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
                for statement in tree.body:
                    if isinstance(statement, ast.ClassDef) and statement.name.endswith(SHARED_CLASS_SUFFIXES):
                        violations.append(f"{relative_path} defines class {statement.name}")
                    for name in _assigned_names(statement):
                        if not _looks_like_constant(name):
                            continue
                        if root_name == "agents" and name in AGENT_ALLOWED_LOCAL_CONSTANTS:
                            continue
                        if root_name == "providers" and name in PROVIDER_ALLOWED_LOCAL_CONSTANTS:
                            continue
                        violations.append(f"{relative_path} defines constant {name}")

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
