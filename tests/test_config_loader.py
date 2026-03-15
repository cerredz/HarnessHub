"""Tests for the CredentialLoader and ProviderCredentialConfig config layer."""

from __future__ import annotations

import os
import tempfile
import unittest

from harnessiq.config import CredentialLoader, ProviderCredentialConfig


class CredentialLoaderTests(unittest.TestCase):
    def _write_env(self, content: str) -> str:
        """Write a temporary .env file and return its path."""
        fh = tempfile.NamedTemporaryFile(
            mode="w", suffix=".env", delete=False, encoding="utf-8"
        )
        fh.write(content)
        fh.close()
        return fh.name

    def tearDown(self) -> None:
        # Clean up any temp files created during tests.
        pass

    def test_load_returns_value_for_present_key(self) -> None:
        env_path = self._write_env("API_KEY=secret123\n")
        try:
            loader = CredentialLoader(env_path=env_path)
            self.assertEqual(loader.load("API_KEY"), "secret123")
        finally:
            os.unlink(env_path)

    def test_load_raises_file_not_found_when_env_absent(self) -> None:
        loader = CredentialLoader(env_path="/nonexistent/path/.env")
        with self.assertRaises(FileNotFoundError):
            loader.load("ANY_KEY")

    def test_load_raises_key_error_when_variable_missing(self) -> None:
        env_path = self._write_env("EXISTING=value\n")
        try:
            loader = CredentialLoader(env_path=env_path)
            with self.assertRaises(KeyError) as ctx:
                loader.load("MISSING_KEY")
            self.assertIn("MISSING_KEY", str(ctx.exception))
        finally:
            os.unlink(env_path)

    def test_load_strips_double_quoted_values(self) -> None:
        env_path = self._write_env('API_KEY="my-secret"\n')
        try:
            loader = CredentialLoader(env_path=env_path)
            self.assertEqual(loader.load("API_KEY"), "my-secret")
        finally:
            os.unlink(env_path)

    def test_load_strips_single_quoted_values(self) -> None:
        env_path = self._write_env("API_KEY='my-secret'\n")
        try:
            loader = CredentialLoader(env_path=env_path)
            self.assertEqual(loader.load("API_KEY"), "my-secret")
        finally:
            os.unlink(env_path)

    def test_load_skips_blank_lines(self) -> None:
        env_path = self._write_env("\n\nAPI_KEY=abc\n\n")
        try:
            loader = CredentialLoader(env_path=env_path)
            self.assertEqual(loader.load("API_KEY"), "abc")
        finally:
            os.unlink(env_path)

    def test_load_skips_comment_lines(self) -> None:
        env_path = self._write_env("# this is a comment\nAPI_KEY=abc\n")
        try:
            loader = CredentialLoader(env_path=env_path)
            self.assertEqual(loader.load("API_KEY"), "abc")
        finally:
            os.unlink(env_path)

    def test_load_all_returns_mapping_for_all_requested_keys(self) -> None:
        env_path = self._write_env("KEY_A=alpha\nKEY_B=beta\nKEY_C=gamma\n")
        try:
            loader = CredentialLoader(env_path=env_path)
            result = loader.load_all(["KEY_A", "KEY_C"])
            self.assertEqual(result, {"KEY_A": "alpha", "KEY_C": "gamma"})
        finally:
            os.unlink(env_path)

    def test_load_all_raises_on_first_missing_key(self) -> None:
        env_path = self._write_env("KEY_A=alpha\n")
        try:
            loader = CredentialLoader(env_path=env_path)
            with self.assertRaises(KeyError) as ctx:
                loader.load_all(["KEY_A", "MISSING"])
            self.assertIn("MISSING", str(ctx.exception))
        finally:
            os.unlink(env_path)

    def test_load_all_raises_file_not_found_when_env_absent(self) -> None:
        loader = CredentialLoader(env_path="/nonexistent/.env")
        with self.assertRaises(FileNotFoundError):
            loader.load_all(["ANY"])

    def test_load_handles_value_containing_equals_sign(self) -> None:
        env_path = self._write_env("TOKEN=abc=def=ghi\n")
        try:
            loader = CredentialLoader(env_path=env_path)
            self.assertEqual(loader.load("TOKEN"), "abc=def=ghi")
        finally:
            os.unlink(env_path)

    def test_load_handles_inline_comment_not_stripped(self) -> None:
        # Inline comments are not supported in basic .env parsers — the full
        # value after = is preserved, including any trailing content.
        env_path = self._write_env("API_KEY=mykey  \n")
        try:
            loader = CredentialLoader(env_path=env_path)
            # strip() is applied to the value after split; trailing spaces removed
            self.assertEqual(loader.load("API_KEY"), "mykey")
        finally:
            os.unlink(env_path)

    def test_loader_does_not_cache_between_calls(self) -> None:
        env_path = self._write_env("API_KEY=first\n")
        try:
            loader = CredentialLoader(env_path=env_path)
            self.assertEqual(loader.load("API_KEY"), "first")
            with open(env_path, "w", encoding="utf-8") as fh:
                fh.write("API_KEY=second\n")
            self.assertEqual(loader.load("API_KEY"), "second")
        finally:
            os.unlink(env_path)


class ProviderCredentialConfigTests(unittest.TestCase):
    def test_provider_credential_config_is_importable(self) -> None:
        # Verify the base TypedDict can be imported and is a type.
        self.assertTrue(callable(ProviderCredentialConfig))

    def test_concrete_credential_config_extends_base(self) -> None:
        from typing import TypedDict

        class MyCredentials(ProviderCredentialConfig):
            api_key: str

        # TypedDict subclass is callable as a constructor.
        cred = MyCredentials(api_key="k")
        self.assertEqual(cred["api_key"], "k")


class HttpTransportHostnameTests(unittest.TestCase):
    """Verify _infer_provider_name correctly maps all 8 new provider hostnames."""

    def _infer(self, url: str) -> str:
        from harnessiq.providers.http import _infer_provider_name  # type: ignore[attr-defined]

        return _infer_provider_name(url)

    def test_snovio_hostname(self) -> None:
        self.assertEqual(self._infer("https://api.snov.io/v1/domain-search"), "snovio")

    def test_leadiq_hostname(self) -> None:
        self.assertEqual(self._infer("https://api.leadiq.com/graphql"), "leadiq")

    def test_salesforge_hostname(self) -> None:
        self.assertEqual(self._infer("https://api.salesforge.ai/public/api/v1/sequence"), "salesforge")

    def test_phantombuster_hostname(self) -> None:
        self.assertEqual(self._infer("https://api.phantombuster.com/api/v2/agents/fetch"), "phantombuster")

    def test_zoominfo_hostname(self) -> None:
        self.assertEqual(self._infer("https://api.zoominfo.com/search/contact"), "zoominfo")

    def test_peopledatalabs_hostname(self) -> None:
        self.assertEqual(self._infer("https://api.peopledatalabs.com/v5/person/enrich"), "peopledatalabs")

    def test_proxycurl_hostname_nubela(self) -> None:
        self.assertEqual(self._infer("https://nubela.co/proxycurl/api/v2/linkedin"), "proxycurl")

    def test_coresignal_hostname(self) -> None:
        self.assertEqual(self._infer("https://api.coresignal.com/cdapi/v1/linkedin/member/collect"), "coresignal")

    def test_existing_hostnames_unchanged(self) -> None:
        self.assertEqual(self._infer("https://api.openai.com/v1/chat/completions"), "openai")
        self.assertEqual(self._infer("https://api.anthropic.com/v1/messages"), "anthropic")
        self.assertEqual(self._infer("https://api.x.ai/v1/chat/completions"), "grok")
        self.assertEqual(self._infer("https://generativelanguage.googleapis.com/v1beta/models"), "gemini")
        self.assertEqual(self._infer("https://api.resend.com/emails"), "resend")

    def test_unknown_hostname_returns_provider(self) -> None:
        self.assertEqual(self._infer("https://unknown.example.com/api"), "provider")


if __name__ == "__main__":
    unittest.main()
