"""Proxycurl LinkedIn data API provider.

WARNING: Proxycurl shut down in January 2025 following a LinkedIn lawsuit.
This provider is preserved for reference only. Importing it will raise a
``DeprecationWarning``.
"""

from __future__ import annotations

import warnings

warnings.warn(
    "Proxycurl shut down in January 2025. This provider is preserved for reference only.",
    DeprecationWarning,
    stacklevel=2,
)

from .client import ProxycurlClient
from .credentials import ProxycurlCredentials
from .requests import (
    build_list_company_jobs_params,
    build_list_employees_params,
    build_lookup_person_by_email_params,
    build_personal_contacts_params,
    build_personal_emails_params,
    build_resolve_company_params,
    build_resolve_email_params,
    build_resolve_person_params,
    build_scrape_company_params,
    build_scrape_person_params,
    build_search_jobs_params,
)

__all__ = [
    "ProxycurlClient",
    "ProxycurlCredentials",
    "build_list_company_jobs_params",
    "build_list_employees_params",
    "build_lookup_person_by_email_params",
    "build_personal_contacts_params",
    "build_personal_emails_params",
    "build_resolve_company_params",
    "build_resolve_email_params",
    "build_resolve_person_params",
    "build_scrape_company_params",
    "build_scrape_person_params",
    "build_search_jobs_params",
]
