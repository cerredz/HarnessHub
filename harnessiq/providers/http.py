"""Shared HTTP transport helpers for provider client wrappers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Protocol
from urllib import error, parse, request


class RequestExecutor(Protocol):
    """Callable contract for executing JSON HTTP requests."""

    def __call__(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        json_body: Any | None = None,
        timeout_seconds: float = 60.0,
    ) -> Any:
        """Execute an HTTP request and return the decoded JSON payload."""


@dataclass(frozen=True, slots=True)
class ProviderHTTPError(RuntimeError):
    """Raised when a provider HTTP request fails."""

    provider: str
    message: str
    status_code: int | None = None
    url: str | None = None
    body: Any | None = None

    def __str__(self) -> str:
        prefix = f"{self.provider} request failed"
        if self.status_code is not None:
            prefix = f"{prefix} ({self.status_code})"
        return f"{prefix}: {self.message}"


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
            return _decode_response(response.read())
    except error.HTTPError as exc:
        body = _decode_response(exc.read())
        message = _extract_error_message(body) or exc.reason or "HTTP error"
        raise ProviderHTTPError(
            provider=_infer_provider_name(url),
            message=message,
            status_code=exc.code,
            url=url,
            body=body,
        ) from exc
    except error.URLError as exc:
        reason = str(exc.reason)
        raise ProviderHTTPError(
            provider=_infer_provider_name(url),
            message=reason,
            url=url,
        ) from exc


def _decode_response(raw_body: bytes) -> Any:
    if not raw_body:
        return None
    text = raw_body.decode("utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


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


def _infer_provider_name(url: str) -> str:
    parsed = parse.urlparse(url)
    host = parsed.netloc.lower()
    if "openai" in host:
        return "openai"
    if "anthropic" in host or "claude" in host:
        return "anthropic"
    if "x.ai" in host:
        return "grok"
    if "googleapis" in host or "generativelanguage" in host:
        return "gemini"
    if "resend" in host:
        return "resend"
    if "apollo" in host:
        return "apollo"
    if "snov.io" in host or "snovio" in host:
        return "snovio"
    if "leadiq" in host:
        return "leadiq"
    if "salesforge" in host:
        return "salesforge"
    if "phantombuster" in host:
        return "phantombuster"
    if "zoominfo" in host:
        return "zoominfo"
    if "peopledatalabs" in host:
        return "peopledatalabs"
    if "nubela" in host or "proxycurl" in host:
        return "proxycurl"
    if "coresignal" in host:
        return "coresignal"
    if "creatify" in host:
        return "creatify"
    if "arcads" in host:
        return "arcads"
    if "instantly" in host:
        return "instantly"
    if "outreach" in host:
        return "outreach"
    if "lemlist" in host:
        return "lemlist"
    if "exa.ai" in host:
        return "exa"
    return "provider"
