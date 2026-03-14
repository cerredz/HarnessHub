"""Tests for the repo-local credential config layer."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harnessiq.config import (
    AgentCredentialBinding,
    AgentCredentialsNotConfiguredError,
    CredentialEnvReference,
    CredentialsConfig,
    CredentialsConfigStore,
    DotEnvFileNotFoundError,
    MissingEnvironmentVariableError,
    parse_dotenv_file,
)


class CredentialsConfigTests(unittest.TestCase):
    def test_store_round_trips_bindings_and_resolves_env_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            store = CredentialsConfigStore(repo_root=repo_root)
            binding = AgentCredentialBinding(
                agent_name="email_agent",
                references=(
                    CredentialEnvReference(field_name="resend_api_key", env_var="RESEND_API_KEY"),
                    CredentialEnvReference(field_name="langsmith_api_key", env_var="LANGSMITH_API_KEY"),
                ),
                description="Email and tracing credentials.",
            )

            saved_path = store.save(CredentialsConfig(bindings=(binding,)))
            repo_root.joinpath(".env").write_text(
                'export RESEND_API_KEY="re_test_123"\nLANGSMITH_API_KEY=ls_test_456 # inline comment\n',
                encoding="utf-8",
            )

            reloaded = store.load()
            resolved = store.resolve_agent("email_agent")

            self.assertEqual(saved_path, store.config_path)
            self.assertEqual(reloaded.binding_for("email_agent"), binding)
            self.assertEqual(resolved.require("resend_api_key"), "re_test_123")
            self.assertEqual(resolved.as_dict()["langsmith_api_key"], "ls_test_456")

    def test_resolve_agent_raises_when_env_file_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = CredentialsConfigStore(repo_root=temp_dir)
            store.upsert(
                AgentCredentialBinding(
                    agent_name="email_agent",
                    references=(CredentialEnvReference(field_name="resend_api_key", env_var="RESEND_API_KEY"),),
                )
            )

            with self.assertRaises(DotEnvFileNotFoundError):
                store.resolve_agent("email_agent")

    def test_resolve_agent_raises_when_required_env_var_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir)
            store = CredentialsConfigStore(repo_root=repo_root)
            store.upsert(
                AgentCredentialBinding(
                    agent_name="email_agent",
                    references=(
                        CredentialEnvReference(field_name="resend_api_key", env_var="RESEND_API_KEY"),
                        CredentialEnvReference(field_name="langsmith_api_key", env_var="LANGSMITH_API_KEY"),
                    ),
                )
            )
            repo_root.joinpath(".env").write_text("RESEND_API_KEY=re_test_123\n", encoding="utf-8")

            with self.assertRaises(MissingEnvironmentVariableError) as context:
                store.resolve_agent("email_agent")

            self.assertIn("LANGSMITH_API_KEY", str(context.exception))
            self.assertIn("email_agent", str(context.exception))

    def test_load_returns_empty_config_and_unknown_agent_raises_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = CredentialsConfigStore(repo_root=temp_dir)

            self.assertEqual(store.load(), CredentialsConfig())
            with self.assertRaises(AgentCredentialsNotConfiguredError):
                store.resolve_agent("missing_agent")

    def test_parse_dotenv_file_supports_single_and_double_quoted_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir, ".env")
            env_path.write_text("SINGLE='value one'\nDOUBLE=\"line\\nvalue\"\n", encoding="utf-8")

            parsed = parse_dotenv_file(env_path)

            self.assertEqual(parsed["SINGLE"], "value one")
            self.assertEqual(parsed["DOUBLE"], "line\nvalue")

    def test_config_models_accept_list_inputs_and_normalize_storage(self) -> None:
        binding = AgentCredentialBinding(
            agent_name="email_agent",
            references=[CredentialEnvReference(field_name="resend_api_key", env_var="RESEND_API_KEY")],
        )
        config = CredentialsConfig(bindings=[binding])

        self.assertIsInstance(binding.references, tuple)
        self.assertIsInstance(config.bindings, tuple)


if __name__ == "__main__":
    unittest.main()
