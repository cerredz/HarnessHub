"""Salesforge API client and request builders."""

from .client import SalesforgeClient
from .credentials import SalesforgeCredentials
from .requests import (
    build_add_contacts_to_sequence_request,
    build_add_unsubscribe_request,
    build_create_contact_request,
    build_create_sequence_request,
    build_remove_unsubscribe_request,
    build_update_contact_request,
    build_update_sequence_request,
)

__all__ = [
    "SalesforgeClient",
    "SalesforgeCredentials",
    "build_add_contacts_to_sequence_request",
    "build_add_unsubscribe_request",
    "build_create_contact_request",
    "build_create_sequence_request",
    "build_remove_unsubscribe_request",
    "build_update_contact_request",
    "build_update_sequence_request",
]
