"""Prepared store builders shared by platform CLI adapters."""

from __future__ import annotations

from pathlib import Path

from harnessiq.shared.exa_outreach import ExaOutreachMemoryStore
from harnessiq.shared.instagram import InstagramMemoryStore
from harnessiq.shared.knowt import KnowtMemoryStore
from harnessiq.shared.leads import LeadsMemoryStore
from harnessiq.shared.linkedin import LinkedInMemoryStore
from harnessiq.shared.prospecting import ProspectingMemoryStore
from harnessiq.shared.research_sweep import ResearchSweepMemoryStore


def load_linkedin_store(memory_path: Path) -> LinkedInMemoryStore:
    """Build and prepare the LinkedIn memory store for one adapter operation."""
    store = LinkedInMemoryStore(memory_path=memory_path)
    store.prepare()
    return store


def load_instagram_store(memory_path: Path) -> InstagramMemoryStore:
    """Build and prepare the Instagram memory store for one adapter operation."""
    store = InstagramMemoryStore(memory_path=memory_path)
    store.prepare()
    return store


def load_prospecting_store(memory_path: Path) -> ProspectingMemoryStore:
    """Build and prepare the prospecting memory store for one adapter operation."""
    store = ProspectingMemoryStore(memory_path=memory_path)
    store.prepare()
    return store


def load_leads_store(memory_path: Path) -> LeadsMemoryStore:
    """Build and prepare the leads memory store for one adapter operation."""
    store = LeadsMemoryStore(memory_path=memory_path)
    store.prepare()
    return store


def load_knowt_store(memory_path: Path) -> KnowtMemoryStore:
    """Build and prepare the Knowt memory store for one adapter operation."""
    store = KnowtMemoryStore(memory_path=memory_path)
    store.prepare()
    return store


def load_exa_store(memory_path: Path) -> ExaOutreachMemoryStore:
    """Build and prepare the Exa Outreach memory store for one adapter operation."""
    store = ExaOutreachMemoryStore(memory_path=memory_path)
    store.prepare()
    return store


def load_research_sweep_store(memory_path: Path) -> ResearchSweepMemoryStore:
    """Build and prepare the research sweep memory store for one adapter operation."""
    store = ResearchSweepMemoryStore(memory_path=memory_path)
    store.prepare()
    return store


__all__ = [
    "load_exa_store",
    "load_instagram_store",
    "load_knowt_store",
    "load_leads_store",
    "load_linkedin_store",
    "load_prospecting_store",
    "load_research_sweep_store",
]
