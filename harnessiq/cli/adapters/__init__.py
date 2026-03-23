"""Platform-first CLI adapters for manifest-backed harnesses."""

from .base import BaseHarnessCliAdapter, HarnessCliAdapter, StoreBackedHarnessCliAdapter
from .context import HarnessAdapterContext
from .exa_outreach import ExaOutreachHarnessCliAdapter
from .instagram import InstagramHarnessCliAdapter
from .knowt import KnowtHarnessCliAdapter
from .leads import LeadsHarnessCliAdapter
from .linkedin import LinkedInHarnessCliAdapter
from .prospecting import ProspectingHarnessCliAdapter

__all__ = [
    "BaseHarnessCliAdapter",
    "ExaOutreachHarnessCliAdapter",
    "HarnessAdapterContext",
    "HarnessCliAdapter",
    "InstagramHarnessCliAdapter",
    "KnowtHarnessCliAdapter",
    "LeadsHarnessCliAdapter",
    "LinkedInHarnessCliAdapter",
    "ProspectingHarnessCliAdapter",
    "StoreBackedHarnessCliAdapter",
]
