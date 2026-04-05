"""Compatibility facade for shared HTTP transport helpers."""

from __future__ import annotations

from harnessiq.shared.http import (
    ProviderHTTPError,
    RequestExecutor,
    _infer_provider_name,
    join_url,
    request_json,
)
