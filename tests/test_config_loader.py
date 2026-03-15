"""Tests for harnessiq.config.loader and harnessiq.config.models."""

from __future__ import annotations

import os
import tempfile
import unittest

from harnessiq.config import CredentialLoader, ProviderCredentialConfig
from harnessiq.providers.http import ProviderHTTPError, _infer_provider_name


class CredentialLoaderTests(unittest.TestCase):
    # ------------------------------------------------------------------
    # Happy-path: load from a well-formed .env file
    # ------------------------------------------------------------------

    def test_load_returns_value_for_present_key(self) -> None:
        with _temp_env("API_KEY=abc123") as path:
            loader = CredentialLoader(env_path=path)
            self.assertEqual(loader.load("API_KEY"), "abc123")

    def test_load_strips_double_quotes_from_value(self) -> None:
        with _temp_env('API_KEY="quoted-value"') as path:
            self.assertEqual(CredentialLoader(env_path=path).load("API_KEY"), "quoted-value")

    def test_load_strips_single_quotes_from_value(self) -> None:
        with _temp_env("API_KEY='single-quoted'") as path:
            self.assertEqual(CredentialLoader(env_path=path).load("API_KEY"), "single-quoted")

    def test_load_does_not_strip_mismatched_quotes(self) -> None:
        with _temp_env("API_KEY=\"mismatched'") as path:
            self.assertEqual(CredentialLoader(env_path=path).load("API_KEY"), "\"mismatched'")

    def test_load_skips_blank_lines(self) -> None:
        with _temp_env("\n\nAPI_KEY=value\n\n") as path:
            self.assertEqual(CredentialLoader(env_path=path).load("API_KEY"), "value")

    def test_load_skips_comment_lines(self) -> None:
        with _temp_env("# This is a comment\nAPI_KEY=value") as path:
            self.assertEqual(CredentialLoader(env_path=path).load("API_KEY"), "value")

    def test_load_skips_indented_comment_lines(self) -> None:
        with _temp_env("  # indented comment\nAPI_KEY=value") as path:
            self.assertEqual(CredentialLoader(env_path=path).load("API_KEY"), "value")

    def test_load_handles_value_containing_equals(self) -> None:
        with _temp_env("API_KEY=abc=def=ghi") as path:
            self.assertEqual(CredentialLoader(env_path=path).load("API_KEY"), "abc=def=ghi")

    def test_load_multiple_keys(self) -> None:
        with _temp_env("FOO=foo_val\nBAR=bar_val") as path:
            loader = CredentialLoader(env_path=path)
            self.assertEqual(loader.load("FOO"), "foo_val")
            self.assertEqual(loader.load("BAR"), "bar_val")

    def test_load_all_returns_all_requested_keys(self) -> None:
        with _temp_env("X=x_val\nY=y_val\nZ=z_val") as path:
            result = CredentialLoader(env_path=path).load_all(["X", "Y", "Z"])
            self.assertEqual(result, {"X": "x_val", "Y": "y_val", "Z": "z_val"})

    def test_load_all_returns_empty_dict_for_empty_sequence(self) -> None:
        with _temp_env("X=x") as path:
            self.assertEqual(CredentialLoader(env_path=path).load_all([]), {})

    # ------------------------------------------------------------------
    # Error cases
    # ------------------------------------------------------------------

    def test_load_raises_file_not_found_when_env_missing(self) -> None:
        loader = CredentialLoader(env_path="/nonexistent/.env.missing")
        with self.assertRaises(FileNotFoundError) as ctx:
            loader.load("ANY_KEY")
        self.assertIn(".env", str(ctx.exception))

    def test_load_raises_key_error_for_absent_key(self) -> None:
        with _temp_env("EXISTING=value") as path:
            loader = CredentialLoader(env_path=path)
            with self.assertRaises(KeyError) as ctx:
                loader.load("MISSING_KEY")
            self.assertIn("MISSING_KEY", str(ctx.exception))

    def test_load_all_raises_key_error_on_first_missing(self) -> None:
        with _temp_env("PRESENT=value") as path:
            with self.assertRaises(KeyError) as ctx:
                CredentialLoader(env_path=path).load_all(["PRESENT", "ABSENT"])
            self.assertIn("ABSENT", str(ctx.exception))

    def test_load_all_raises_file_not_found_when_env_missing(self) -> None:
        with self.assertRaises(FileNotFoundError):
            CredentialLoader(env_path="/no/.env").load_all(["X"])

    # ------------------------------------------------------------------
    # Default path uses cwd
    # ------------------------------------------------------------------

    def test_default_env_path_is_dot_env_in_cwd(self) -> None:
        loader = CredentialLoader()
        self.assertTrue(loader._env_path.endswith(".env"))
        self.assertEqual(os.path.dirname(loader._env_path), os.getcwd())

    # ------------------------------------------------------------------
    # Re-reads file on each call (no caching)
    # ------------------------------------------------------------------

    def test_load_reflects_file_changes_between_calls(self) -> None:
        with _temp_env("KEY=first") as path:
            loader = CredentialLoader(env_path=path)
            self.assertEqual(loader.load("KEY"), "first")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("KEY=second\n")
            self.assertEqual(loader.load("KEY"), "second")


class ProviderCredentialConfigTests(unittest.TestCase):
    def test_provider_credential_config_is_importable(self) -> None:
        # TypedDict — verify it can be instantiated and used as a plain dict
        config: ProviderCredentialConfig = {"provider": "test"}
        self.assertEqual(config["provider"], "test")


class HttpHostnameMapTests(unittest.TestCase):
    """Verify _infer_provider_name maps all six new provider hostnames."""

    def _assert_provider(self, url: str, expected: str) -> None:
        self.assertEqual(_infer_provider_name(url), expected)

    def test_creatify_hostname(self) -> None:
        self._assert_provider("https://api.creatify.ai/api/lipsyncs/", "creatify")

    def test_arcads_hostname(self) -> None:
        self._assert_provider("https://external-api.arcads.ai/v1/products", "arcads")

    def test_instantly_hostname(self) -> None:
        self._assert_provider("https://api.instantly.ai/api/v2/campaigns", "instantly")

    def test_outreach_hostname(self) -> None:
        self._assert_provider("https://api.outreach.io/api/v2/prospects", "outreach")

    def test_lemlist_hostname(self) -> None:
        self._assert_provider("https://api.lemlist.com/api/campaigns", "lemlist")

    def test_exa_hostname(self) -> None:
        self._assert_provider("https://api.exa.ai/search", "exa")

    def test_existing_providers_unaffected(self) -> None:
        self._assert_provider("https://api.openai.com/v1/chat/completions", "openai")
        self._assert_provider("https://api.anthropic.com/v1/messages", "anthropic")
        self._assert_provider("https://api.x.ai/v1/chat/completions", "grok")
        self._assert_provider("https://generativelanguage.googleapis.com/v1beta/models", "gemini")
        self._assert_provider("https://api.resend.com/emails", "resend")

    def test_unknown_host_returns_provider(self) -> None:
        self._assert_provider("https://unknown.example.com/api", "provider")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

from contextlib import contextmanager
from typing import Generator


@contextmanager
def _temp_env(content: str) -> Generator[str, None, None]:
    """Write *content* to a temporary .env file and yield its path."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False, encoding="utf-8") as fh:
        fh.write(content)
        path = fh.name
    try:
        yield path
    finally:
        os.unlink(path)


if __name__ == "__main__":
    unittest.main()
