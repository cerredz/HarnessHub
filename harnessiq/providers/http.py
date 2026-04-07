"""Shared HTTP transport helpers for provider client wrappers."""

from __future__ import annotations

import json
from typing import Any, Mapping
from urllib import error, parse, request

from harnessiq.shared.http import ProviderHTTPError, RequestExecutor
from harnessiq.shared.strings import ProviderName


class ProviderHTTP:
    """Static HTTP transport helpers for provider client wrappers.

    All methods are ``@staticmethod`` — instantiation is never required.
    Module-level aliases (``join_url``, ``request_json``, ``_infer_provider_name``)
    are preserved below for backward compatibility with existing importers.
    """

    @staticmethod
    def join_url(
        base_url: str,
        path: str,
        *,
        query: Mapping[str, str | int | float | bool] | None = None,
    ) -> str:
        """Join a base URL, path, and optional query parameters."""
        base = base_url.rstrip("/")
        normalized_path = path if path.startswith("/") else f"/{path}"
        url = f"{base}{normalized_path}"
        if not query:
            return url
        encoded_query = parse.urlencode({key: value for key, value in query.items()})
        return f"{url}?{encoded_query}"

    @staticmethod
    def request_json(
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        json_body: Any | None = None,
        timeout_seconds: float = 60.0,
    ) -> Any:
        """Execute a JSON request with stdlib networking primitives."""
        request_headers = dict(headers or {})
        request_headers.setdefault("Accept", "application/json")
        if json_body is not None:
            request_headers.setdefault("Content-Type", "application/json")
            data = json.dumps(json_body).encode("utf-8")
        else:
            data = None

        http_request = request.Request(url=url, data=data, method=method.upper())
        for header_name, header_value in request_headers.items():
            http_request.add_header(header_name, header_value)

        try:
            with request.urlopen(http_request, timeout=timeout_seconds) as response:
                return ProviderHTTP._decode_response(response.read())
        except error.HTTPError as exc:
            body = ProviderHTTP._decode_response(exc.read())
            message = ProviderHTTP._extract_error_message(body) or exc.reason or "HTTP error"
            raise ProviderHTTPError(
                provider=ProviderHTTP._infer_provider_name(url),
                message=message,
                status_code=exc.code,
                url=url,
                body=body,
            ) from exc
        except error.URLError as exc:
            reason = str(exc.reason)
            raise ProviderHTTPError(
                provider=ProviderHTTP._infer_provider_name(url),
                message=reason,
                url=url,
            ) from exc

    @staticmethod
    def _decode_response(raw_body: bytes) -> Any:
        if not raw_body:
            return None
        text = raw_body.decode("utf-8")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    @staticmethod
    def _extract_error_message(body: Any) -> str | None:
        if isinstance(body, dict):
            error_payload = body.get("error")
            if isinstance(error_payload, dict):
                message = error_payload.get("message")
                if isinstance(message, str):
                    return message
            message = body.get("message")
            if isinstance(message, str):
                return message
        if isinstance(body, str):
            return body
        return None

    @staticmethod
    def _infer_provider_name(url: str) -> ProviderName:
        """Infer the provider family name from a request URL."""
        parsed = parse.urlparse(url)
        host = parsed.netloc.lower()
        if "openai" in host:
            return ProviderName.OPENAI
        if "anthropic" in host or "claude" in host:
            return ProviderName.ANTHROPIC
        if "x.ai" in host:
            return ProviderName.GROK
        if "googleapis" in host or "generativelanguage" in host:
            return ProviderName.GEMINI
        if "resend" in host:
            return ProviderName.RESEND
        if "apollo" in host:
            return ProviderName.APOLLO
        if "browser-use" in host or "browseruse" in host:
            return ProviderName.BROWSER_USE
        if "snov.io" in host or "snovio" in host:
            return ProviderName.SNOVIO
        if "leadiq" in host:
            return ProviderName.LEADIQ
        if "salesforge" in host:
            return ProviderName.SALESFORGE
        if "phantombuster" in host:
            return ProviderName.PHANTOMBUSTER
        if "zoominfo" in host:
            return ProviderName.ZOOMINFO
        if "peopledatalabs" in host:
            return ProviderName.PEOPLEDATALABS
        if "nubela" in host or "proxycurl" in host:
            return ProviderName.PROXYCURL
        if "coresignal" in host:
            return ProviderName.CORESIGNAL
        if "creatify" in host:
            return ProviderName.CREATIFY
        if "arcads" in host:
            return ProviderName.ARCADS
        if "hunter.io" in host:
            return ProviderName.HUNTER
        if "instantly" in host:
            return ProviderName.INSTANTLY
        if "outreach" in host:
            return ProviderName.OUTREACH
        if "lemlist" in host:
            return ProviderName.LEMLIST
        if "exa.ai" in host:
            return ProviderName.EXA
        if "arxiv" in host:
            return ProviderName.ARXIV
        return ProviderName.UNKNOWN


# ---------------------------------------------------------------------------
# Backward-compatible module-level aliases
# All existing importers (70+ provider client files and tests) reference these
# names directly; the aliases preserve that contract without modification.
# ---------------------------------------------------------------------------

join_url = ProviderHTTP.join_url
request_json = ProviderHTTP.request_json
_infer_provider_name = ProviderHTTP._infer_provider_name


__all__ = [
    "ProviderHTTP",
    "ProviderHTTPError",
    "RequestExecutor",
    "join_url",
    "request_json",
]
