"""Paperclip control-plane API provider support."""

from .api import DEFAULT_BASE_URL, build_headers, url
from .client import PaperclipClient, PaperclipCredentials
from .operations import (
    PaperclipOperation,
    PaperclipPreparedRequest,
    build_paperclip_operation_catalog,
    get_paperclip_operation,
)

__all__ = [
    "DEFAULT_BASE_URL",
    "PaperclipClient",
    "PaperclipCredentials",
    "PaperclipOperation",
    "PaperclipPreparedRequest",
    "build_headers",
    "build_paperclip_operation_catalog",
    "get_paperclip_operation",
    "url",
]
