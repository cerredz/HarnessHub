"""Tests for shared provider helpers and HTTP transport."""

from __future__ import annotations

import io
import json
import unittest
from urllib import error, request

from harnessiq.providers import (
    ProviderFormatError,
    ProviderHTTPError,
    SUPPORTED_PROVIDERS,
    normalize_messages,
    omit_none_values,
    request_json,
)


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


class ProviderBaseTests(unittest.TestCase):
    def test_supported_providers_are_stable(self) -> None:
        self.assertEqual(SUPPORTED_PROVIDERS, ("anthropic", "openai", "grok", "gemini"))

    def test_normalize_messages_rejects_unknown_roles(self) -> None:
        with self.assertRaises(ProviderFormatError):
            normalize_messages([{"role": "tool", "content": "nope"}])

    def test_normalize_messages_rejects_inline_system_when_disallowed(self) -> None:
        with self.assertRaises(ProviderFormatError):
            normalize_messages([{"role": "system", "content": "dup"}], allow_system=False)

    def test_omit_none_values_drops_none_entries(self) -> None:
        payload = omit_none_values({"model": "gpt-4.1", "temperature": None, "nested": {"value": 1}})
        self.assertEqual(payload, {"model": "gpt-4.1", "nested": {"value": 1}})

    def test_request_json_encodes_body_and_sets_default_headers(self) -> None:
        captured: dict[str, object] = {}

        def fake_urlopen(http_request: request.Request, timeout: float) -> _FakeResponse:
            captured["method"] = http_request.get_method()
            captured["url"] = http_request.full_url
            captured["timeout"] = timeout
            captured["headers"] = dict(http_request.header_items())
            captured["body"] = json.loads(http_request.data.decode("utf-8"))
            return _FakeResponse({"ok": True})

        original_urlopen = request.urlopen
        request.urlopen = fake_urlopen
        try:
            response = request_json(
                "POST",
                "https://api.openai.com/v1/responses",
                headers={"Authorization": "Bearer test"},
                json_body={"model": "gpt-4.1"},
                timeout_seconds=12.0,
            )
        finally:
            request.urlopen = original_urlopen

        self.assertEqual(response, {"ok": True})
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["url"], "https://api.openai.com/v1/responses")
        self.assertEqual(captured["timeout"], 12.0)
        self.assertEqual(captured["body"], {"model": "gpt-4.1"})
        self.assertEqual(captured["headers"]["Accept"], "application/json")
        self.assertEqual(captured["headers"]["Content-type"], "application/json")

    def test_request_json_raises_provider_http_error_for_http_failure(self) -> None:
        def fake_urlopen(http_request: request.Request, timeout: float) -> _FakeResponse:
            error_body = io.BytesIO(json.dumps({"error": {"message": "bad request"}}).encode("utf-8"))
            raise error.HTTPError(http_request.full_url, 400, "Bad Request", hdrs={}, fp=error_body)

        original_urlopen = request.urlopen
        request.urlopen = fake_urlopen
        try:
            with self.assertRaises(ProviderHTTPError) as raised:
                request_json(
                    "POST",
                    "https://api.openai.com/v1/responses",
                    headers={"Authorization": "Bearer test"},
                    json_body={"model": "gpt-4.1"},
                )
        finally:
            request.urlopen = original_urlopen

        self.assertEqual(raised.exception.provider, "openai")
        self.assertEqual(raised.exception.status_code, 400)
        self.assertEqual(raised.exception.url, "https://api.openai.com/v1/responses")
        self.assertEqual(raised.exception.body, {"error": {"message": "bad request"}})
        self.assertIn("bad request", str(raised.exception))

    def test_request_json_raises_provider_http_error_for_url_failure(self) -> None:
        def fake_urlopen(http_request: request.Request, timeout: float) -> _FakeResponse:
            raise error.URLError("network down")

        original_urlopen = request.urlopen
        request.urlopen = fake_urlopen
        try:
            with self.assertRaises(ProviderHTTPError) as raised:
                request_json(
                    "GET",
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": "Bearer test"},
                )
        finally:
            request.urlopen = original_urlopen

        self.assertEqual(raised.exception.provider, "openai")
        self.assertIsNone(raised.exception.status_code)
        self.assertEqual(raised.exception.url, "https://api.openai.com/v1/models")
        self.assertIn("network down", str(raised.exception))

    def test_request_json_labels_resend_failures_with_resend_provider_name(self) -> None:
        def fake_urlopen(http_request: request.Request, timeout: float) -> _FakeResponse:
            raise error.URLError("resend down")

        original_urlopen = request.urlopen
        request.urlopen = fake_urlopen
        try:
            with self.assertRaises(ProviderHTTPError) as raised:
                request_json(
                    "POST",
                    "https://api.resend.com/emails",
                    headers={"Authorization": "Bearer test"},
                    json_body={"subject": "hello"},
                )
        finally:
            request.urlopen = original_urlopen

        self.assertEqual(raised.exception.provider, "resend")
        self.assertIn("resend down", str(raised.exception))

    def test_provider_http_error_allows_traceback_assignment(self) -> None:
        try:
            raise ProviderHTTPError(provider="grok", message="Forbidden", status_code=403)
        except ProviderHTTPError as exc:
            exc.__traceback__ = exc.__traceback__
            self.assertEqual(exc.provider, "grok")
            self.assertEqual(exc.status_code, 403)
            self.assertEqual(str(exc), "grok request failed (403): Forbidden")


if __name__ == "__main__":
    unittest.main()
