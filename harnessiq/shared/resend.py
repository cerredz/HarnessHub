"""Compatibility facade for shared Resend definitions and catalog metadata."""

from __future__ import annotations

from harnessiq.shared.resend_catalog import build_resend_operation_catalog, get_resend_operation
from harnessiq.shared.resend_models import (
    DEFAULT_RESEND_BASE_URL,
    DEFAULT_RESEND_USER_AGENT,
    RESEND_REQUEST,
    ResendCredentials,
    ResendOperation,
    ResendPreparedRequest,
    _BATCH_VALIDATION_MODES,
)

# Preserve the public shared-definition ownership contract used by package tests.
ResendCredentials.__module__ = __name__
ResendOperation.__module__ = __name__
ResendPreparedRequest.__module__ = __name__

__all__ = [
    "DEFAULT_RESEND_BASE_URL",
    "DEFAULT_RESEND_USER_AGENT",
    "RESEND_REQUEST",
    "ResendCredentials",
    "ResendOperation",
    "ResendPreparedRequest",
    "build_resend_operation_catalog",
    "get_resend_operation",
    "_BATCH_VALIDATION_MODES",
]
