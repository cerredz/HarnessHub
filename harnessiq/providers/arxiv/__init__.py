"""arXiv academic paper search API — transport config, client, and operation catalog."""

from .client import ArxivClient, ArxivConfig
from .operations import ArxivOperation, build_arxiv_operation_catalog, get_arxiv_operation

__all__ = [
    "ArxivClient",
    "ArxivConfig",
    "ArxivOperation",
    "build_arxiv_operation_catalog",
    "get_arxiv_operation",
]
