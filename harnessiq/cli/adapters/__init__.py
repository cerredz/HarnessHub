"""Platform-first CLI adapters for manifest-backed harnesses."""

from .base import BaseHarnessCliAdapter, HarnessCliAdapter, StoreBackedHarnessCliAdapter
from .context import HarnessAdapterContext
from .email import EmailHarnessCliAdapter
from .exa_outreach import ExaOutreachHarnessCliAdapter
from .instagram import InstagramHarnessCliAdapter
from .knowt import KnowtHarnessCliAdapter
from .leads import LeadsHarnessCliAdapter
from .linkedin import LinkedInHarnessCliAdapter
from .prospecting import ProspectingHarnessCliAdapter
from .research_sweep import ResearchSweepHarnessCliAdapter

__all__ = [
    "BaseHarnessCliAdapter",
    "EmailHarnessCliAdapter",
    "ExaOutreachHarnessCliAdapter",
    "HarnessAdapterContext",
    "HarnessCliAdapter",
    "InstagramHarnessCliAdapter",
    "KnowtHarnessCliAdapter",
    "LeadsHarnessCliAdapter",
    "LinkedInHarnessCliAdapter",
    "ProspectingHarnessCliAdapter",
    "ResearchSweepHarnessCliAdapter",
    "StoreBackedHarnessCliAdapter",
]
