"""Arcads operation catalog, tool definition, and MCP-style tool factory."""

from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Literal, Sequence

PayloadKind = Literal["none", "object"]


@dataclass(frozen=True, slots=True)
class ArcadsOperation:
    """Declarative metadata for one Arcads API operation."""

    name: str
    category: str
    method: Literal["GET", "POST", "PUT", "DELETE"]
    path_hint: str
    required_path_params: tuple[str, ...] = ()
    payload_kind: PayloadKind = "none"
    payload_required: bool = False
    allow_query: bool = False

    def summary(self) -> str:
        return f"{self.name} ({self.method} {self.path_hint})"


@dataclass(frozen=True, slots=True)
class ArcadsPreparedRequest:
    """A validated Arcads request ready for execution."""

    operation: ArcadsOperation
    method: str
    path: str
    url: str
    headers: dict[str, str]
    json_body: Any | None


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

def _op(
    name: str,
    category: str,
    method: Literal["GET", "POST", "PUT", "DELETE"],
    path_hint: str,
    *,
    required_path_params: Sequence[str] = (),
    payload_kind: PayloadKind = "none",
    payload_required: bool = False,
    allow_query: bool = False,
) -> tuple[str, ArcadsOperation]:
    return (
        name,
        ArcadsOperation(
            name=name,
            category=category,
            method=method,
            path_hint=path_hint,
            required_path_params=tuple(required_path_params),
            payload_kind=payload_kind,
            payload_required=payload_required,
            allow_query=allow_query,
        ),
    )


_ARCADS_CATALOG: OrderedDict[str, ArcadsOperation] = OrderedDict(
    (
        # Products
        _op("create_product", "Products", "POST", "/v1/products", payload_kind="object", payload_required=True),
        _op("list_products", "Products", "GET", "/v1/products"),
        # Folders
        _op("create_folder", "Folders", "POST", "/v1/folders", payload_kind="object", payload_required=True),
        _op("list_product_folders", "Folders", "GET", "/v1/products/{productId}/folders", required_path_params=("productId",)),
        # Situations
        _op("list_situations", "Situations", "GET", "/v1/situations", allow_query=True),
        # Scripts
        _op("create_script", "Scripts", "POST", "/v1/scripts", payload_kind="object", payload_required=True),
        _op("list_folder_scripts", "Scripts", "GET", "/v1/folders/{folderId}/scripts", required_path_params=("folderId",)),
        _op("update_script", "Scripts", "PUT", "/v1/scripts/{scriptId}", required_path_params=("scriptId",), payload_kind="object", payload_required=True),
        _op("generate_video", "Scripts", "POST", "/v1/scripts/{scriptId}/generate", required_path_params=("scriptId",), payload_kind="object"),
        # Videos
        _op("list_script_videos", "Videos", "GET", "/v1/scripts/{scriptId}/videos", required_path_params=("scriptId",)),
    )
)


def build_arcads_operation_catalog() -> tuple[ArcadsOperation, ...]:
    """Return the supported Arcads operation catalog in stable order."""
    return tuple(_ARCADS_CATALOG.values())


def get_arcads_operation(operation_name: str) -> ArcadsOperation:
    """Return a supported Arcads operation or raise a clear error."""
    op = _ARCADS_CATALOG.get(operation_name)
    if op is None:
        available = ", ".join(_ARCADS_CATALOG)
        raise ValueError(f"Unsupported Arcads operation '{operation_name}'. Available: {available}.")
    return op

__all__ = [
    "ArcadsOperation",
    "ArcadsPreparedRequest",
    "build_arcads_operation_catalog",
    "get_arcads_operation",
]
