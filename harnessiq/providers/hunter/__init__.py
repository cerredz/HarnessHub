"""Hunter.io provider client and operation metadata."""

from .api import DEFAULT_BASE_URL as HUNTER_BASE_URL
from .client import HunterClient, HunterCredentials
from .operations import (
    HUNTER_REQUEST,
    HunterOperation,
    HunterPreparedRequest,
    build_hunter_operation_catalog,
    get_hunter_operation,
)

__all__ = [
    "HUNTER_REQUEST",
    "HUNTER_BASE_URL",
    "HunterClient",
    "HunterCredentials",
    "HunterOperation",
    "HunterPreparedRequest",
    "build_hunter_operation_catalog",
    "get_hunter_operation",
]
