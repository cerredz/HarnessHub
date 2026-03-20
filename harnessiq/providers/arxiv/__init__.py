"""arXiv academic paper search API — transport config, client, and operation catalog."""

from .client import ArxivClient
from .operations import ArxivOperation, build_arxiv_operation_catalog, get_arxiv_operation
from harnessiq.shared.provider_configs import ArxivConfig

__all__ = [
    "ArxivClient",
    "ArxivConfig",
    "ArxivOperation",
    "build_arxiv_operation_catalog",
    "get_arxiv_operation",
]
