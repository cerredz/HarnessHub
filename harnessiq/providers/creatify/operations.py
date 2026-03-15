"""Creatify operation catalog, tool definition, and MCP-style tool factory."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Mapping, Sequence
from urllib.parse import quote

from harnessiq.providers.http import join_url
from harnessiq.shared.tools import RegisteredTool, ToolArguments, ToolDefinition

if TYPE_CHECKING:
    from harnessiq.providers.creatify.client import CreatifyCredentials

CREATIFY_REQUEST = "creatify.request"
PayloadKind = Literal["none", "object"]


@dataclass(frozen=True, slots=True)
class CreatifyOperation:
    """Declarative metadata for one Creatify API operation."""

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
class CreatifyPreparedRequest:
    """A validated Creatify request ready for execution."""

    operation: CreatifyOperation
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
) -> tuple[str, CreatifyOperation]:
    return (
        name,
        CreatifyOperation(
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


_CREATIFY_CATALOG: OrderedDict[str, CreatifyOperation] = OrderedDict(
    (
        # Link to Video
        _op("create_link_to_video", "Link to Video", "POST", "/api/link_to_videos/", payload_kind="object", payload_required=True),
        _op("get_link_to_video", "Link to Video", "GET", "/api/link_to_videos/{id}/", required_path_params=("id",)),
        _op("preview_link_to_video", "Link to Video", "POST", "/api/link_to_videos/{id}/preview/", required_path_params=("id",)),
        _op("render_link_to_video", "Link to Video", "POST", "/api/link_to_videos/{id}/render/", required_path_params=("id",)),
        # Aurora Avatar
        _op("create_aurora", "Aurora Avatar", "POST", "/api/aurora/", payload_kind="object", payload_required=True),
        _op("get_aurora", "Aurora Avatar", "GET", "/api/aurora/{id}/", required_path_params=("id",)),
        _op("preview_aurora", "Aurora Avatar", "POST", "/api/aurora/{id}/preview/", required_path_params=("id",)),
        _op("render_aurora", "Aurora Avatar", "POST", "/api/aurora/{id}/render/", required_path_params=("id",)),
        # AI Avatar v1 (Lipsyncs)
        _op("create_lipsync", "AI Avatar v1", "POST", "/api/lipsyncs/", payload_kind="object", payload_required=True),
        _op("get_lipsync", "AI Avatar v1", "GET", "/api/lipsyncs/{id}/", required_path_params=("id",)),
        _op("preview_lipsync", "AI Avatar v1", "POST", "/api/lipsyncs/{id}/preview/", required_path_params=("id",)),
        _op("render_lipsync", "AI Avatar v1", "POST", "/api/lipsyncs/{id}/render/", required_path_params=("id",)),
        # AI Avatar v2 (Lipsyncs v2)
        _op("create_lipsync_v2", "AI Avatar v2", "POST", "/api/lipsyncs_v2/", payload_kind="object", payload_required=True),
        _op("get_lipsync_v2", "AI Avatar v2", "GET", "/api/lipsyncs_v2/{id}/", required_path_params=("id",)),
        _op("preview_lipsync_v2", "AI Avatar v2", "POST", "/api/lipsyncs_v2/{id}/preview/", required_path_params=("id",)),
        _op("render_lipsync_v2", "AI Avatar v2", "POST", "/api/lipsyncs_v2/{id}/render/", required_path_params=("id",)),
        # AI Shorts
        _op("create_ai_short", "AI Shorts", "POST", "/api/ai-shorts/", payload_kind="object", payload_required=True),
        _op("get_ai_short", "AI Shorts", "GET", "/api/ai-shorts/{id}/", required_path_params=("id",)),
        _op("preview_ai_short", "AI Shorts", "POST", "/api/ai-shorts/{id}/preview/", required_path_params=("id",)),
        _op("render_ai_short", "AI Shorts", "POST", "/api/ai-shorts/{id}/render/", required_path_params=("id",)),
        # AI Scripts
        _op("create_ai_script", "AI Scripts", "POST", "/api/ai-scripts/", payload_kind="object", payload_required=True),
        _op("get_ai_script", "AI Scripts", "GET", "/api/ai-scripts/{id}/", required_path_params=("id",)),
        # AI Editing
        _op("create_ai_editing", "AI Editing", "POST", "/api/ai_editing/", payload_kind="object", payload_required=True),
        _op("get_ai_editing", "AI Editing", "GET", "/api/ai_editing/{id}/", required_path_params=("id",)),
        _op("preview_ai_editing", "AI Editing", "POST", "/api/ai_editing/{id}/preview/", required_path_params=("id",)),
        _op("render_ai_editing", "AI Editing", "POST", "/api/ai_editing/{id}/render/", required_path_params=("id",)),
        # Ad Clone
        _op("create_ad_clone", "Ad Clone", "POST", "/api/ad-clone/", payload_kind="object", payload_required=True),
        _op("get_ad_clone", "Ad Clone", "GET", "/api/ad-clone/{id}/", required_path_params=("id",)),
        # Asset Generator
        _op("create_asset", "Asset Generator", "POST", "/api/ai-generation/", payload_kind="object", payload_required=True),
        _op("get_asset", "Asset Generator", "GET", "/api/ai-generation/{id}/", required_path_params=("id",)),
        # Custom Templates
        _op("list_custom_templates", "Custom Templates", "GET", "/api/custom-templates/", allow_query=True),
        _op("get_custom_template", "Custom Templates", "GET", "/api/custom-templates/{id}/", required_path_params=("id",)),
        _op("create_custom_template_job", "Custom Templates", "POST", "/api/custom-template-jobs/", payload_kind="object", payload_required=True),
        _op("get_custom_template_job", "Custom Templates", "GET", "/api/custom-template-jobs/{id}/", required_path_params=("id",)),
        # IAB Images
        _op("create_iab_image", "IAB Images", "POST", "/api/iab-images/", payload_kind="object", payload_required=True),
        _op("get_iab_image", "IAB Images", "GET", "/api/iab-images/{id}/", required_path_params=("id",)),
        # Inspiration
        _op("list_inspirations", "Inspiration", "GET", "/api/inspiration/", allow_query=True),
        _op("create_inspiration", "Inspiration", "POST", "/api/inspiration/", payload_kind="object", payload_required=True),
        _op("get_inspiration", "Inspiration", "GET", "/api/inspiration/{id}/", required_path_params=("id",)),
        # Product to Video
        _op("create_product_video", "Product to Video", "POST", "/api/product_to_videos/", payload_kind="object", payload_required=True),
        _op("get_product_video", "Product to Video", "GET", "/api/product_to_videos/{id}/", required_path_params=("id",)),
        _op("preview_product_video", "Product to Video", "POST", "/api/product_to_videos/{id}/preview/", required_path_params=("id",)),
        _op("render_product_video", "Product to Video", "POST", "/api/product_to_videos/{id}/render/", required_path_params=("id",)),
        # Links
        _op("list_links", "Links", "GET", "/api/links/", allow_query=True),
        _op("create_link", "Links", "POST", "/api/links/", payload_kind="object", payload_required=True),
        _op("update_link", "Links", "PUT", "/api/links/{id}/", required_path_params=("id",), payload_kind="object", payload_required=True),
        # Music
        _op("list_music", "Music", "GET", "/api/musics/", allow_query=True),
        _op("list_music_categories", "Music", "GET", "/api/music-categories/"),
        # Custom Avatars (Personas)
        _op("list_personas", "Custom Avatars", "GET", "/api/personas/", allow_query=True),
        _op("create_persona", "Custom Avatars", "POST", "/api/personas/", payload_kind="object", payload_required=True),
        _op("delete_persona", "Custom Avatars", "DELETE", "/api/personas/{id}/", required_path_params=("id",)),
        # Text-to-Speech
        _op("create_tts", "Text-to-Speech", "POST", "/api/text_to_speech/", payload_kind="object", payload_required=True),
        _op("get_tts", "Text-to-Speech", "GET", "/api/text_to_speech/{id}/", required_path_params=("id",)),
        # Voices
        _op("list_voices", "Voices", "GET", "/api/voices/", allow_query=True),
        _op("create_voice", "Voices", "POST", "/api/voices/", payload_kind="object", payload_required=True),
        _op("delete_voice", "Voices", "DELETE", "/api/voices/{id}/", required_path_params=("id",)),
        _op("get_voice_quota", "Voices", "GET", "/api/voices/quota/"),
        # Workspace
        _op("get_remaining_credits", "Workspace", "GET", "/api/remaining-credits/"),
    )
)


def build_creatify_operation_catalog() -> tuple[CreatifyOperation, ...]:
    """Return the supported Creatify operation catalog in stable order."""
    return tuple(_CREATIFY_CATALOG.values())


def get_creatify_operation(operation_name: str) -> CreatifyOperation:
    """Return a supported Creatify operation or raise a clear error."""
    op = _CREATIFY_CATALOG.get(operation_name)
    if op is None:
        available = ", ".join(_CREATIFY_CATALOG)
        raise ValueError(
            f"Unsupported Creatify operation '{operation_name}'. Available: {available}."
        )
    return op


def build_creatify_request_tool_definition(
    *,
    allowed_operations: Sequence[str] | None = None,
) -> ToolDefinition:
    """Return the canonical tool definition for the Creatify request surface."""
    operations = _select_operations(allowed_operations)
    operation_names = [op.name for op in operations]
    return ToolDefinition(
        key=CREATIFY_REQUEST,
        name="creatify_request",
        description=_build_tool_description(operations),
        input_schema={
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": operation_names,
                    "description": "Creatify operation name.",
                },
                "path_params": {
                    "type": "object",
                    "description": "Path parameters such as the resource id.",
                    "additionalProperties": True,
                },
                "query": {
                    "type": "object",
                    "description": "Optional query parameters for list/filter operations.",
                    "additionalProperties": True,
                },
                "payload": {
                    "type": "object",
                    "description": "Optional JSON body for create/update operations.",
                },
            },
            "required": ["operation"],
            "additionalProperties": False,
        },
    )


def create_creatify_tools(
    *,
    credentials: "CreatifyCredentials | None" = None,
    client: "Any | None" = None,
    allowed_operations: Sequence[str] | None = None,
) -> tuple[RegisteredTool, ...]:
    """Return the MCP-style Creatify request tool backed by the provided client."""
    from harnessiq.providers.creatify.client import CreatifyClient

    creatify_client = _coerce_client(credentials=credentials, client=client)
    selected = _select_operations(allowed_operations)
    allowed_names = frozenset(op.name for op in selected)
    definition = build_creatify_request_tool_definition(
        allowed_operations=tuple(op.name for op in selected)
    )

    def handler(arguments: ToolArguments) -> dict[str, Any]:
        operation_name = _require_operation_name(arguments, allowed_names)
        prepared = creatify_client.prepare_request(
            operation_name,
            path_params=_optional_mapping(arguments, "path_params"),
            query=_optional_mapping(arguments, "query"),
            payload=arguments.get("payload"),
        )
        response = creatify_client.request_executor(
            prepared.method,
            prepared.url,
            headers=prepared.headers,
            json_body=prepared.json_body,
            timeout_seconds=creatify_client.credentials.timeout_seconds,
        )
        return {
            "operation": prepared.operation.name,
            "method": prepared.method,
            "path": prepared.path,
            "response": response,
        }

    return (RegisteredTool(definition=definition, handler=handler),)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_prepared_request(
    *,
    operation_name: str,
    credentials: "CreatifyCredentials",
    path_params: Mapping[str, object] | None,
    query: Mapping[str, object] | None,
    payload: Any | None,
) -> CreatifyPreparedRequest:
    from harnessiq.providers.creatify.api import build_headers

    op = get_creatify_operation(operation_name)
    normalized_params = _normalize_path_params(path_params)
    _validate_path_params(op, normalized_params)
    _validate_payload(op, payload)

    path = _render_path(op.path_hint, normalized_params)
    full_url = join_url(credentials.base_url, path, query=_normalize_query(query) if query else None)
    headers = build_headers(credentials.api_id, credentials.api_key)

    return CreatifyPreparedRequest(
        operation=op,
        method=op.method,
        path=path,
        url=full_url,
        headers=headers,
        json_body=deepcopy(payload) if payload is not None else None,
    )


def _render_path(path_hint: str, path_params: dict[str, str]) -> str:
    rendered = path_hint
    for key, value in path_params.items():
        rendered = rendered.replace(f"{{{key}}}", quote(value, safe=""))
    return rendered


def _normalize_path_params(path_params: Mapping[str, object] | None) -> dict[str, str]:
    if not path_params:
        return {}
    return {str(k): str(v) for k, v in path_params.items()}


def _normalize_query(query: Mapping[str, object]) -> dict[str, str | int | float | bool]:
    return {str(k): v for k, v in query.items()}  # type: ignore[return-value]


def _validate_path_params(op: CreatifyOperation, params: dict[str, str]) -> None:
    missing = [k for k in op.required_path_params if not params.get(k)]
    if missing:
        raise ValueError(f"Operation '{op.name}' requires path parameters: {', '.join(missing)}.")


def _validate_payload(op: CreatifyOperation, payload: Any | None) -> None:
    if op.payload_kind == "none" and payload is not None:
        raise ValueError(f"Operation '{op.name}' does not accept a payload.")
    if op.payload_required and payload is None:
        raise ValueError(f"Operation '{op.name}' requires a payload.")


def _select_operations(allowed: Sequence[str] | None) -> tuple[CreatifyOperation, ...]:
    if allowed is None:
        return build_creatify_operation_catalog()
    seen: set[str] = set()
    selected: list[CreatifyOperation] = []
    for name in allowed:
        op = get_creatify_operation(name)
        if op.name not in seen:
            seen.add(op.name)
            selected.append(op)
    return tuple(selected)


def _coerce_client(*, credentials: Any, client: Any) -> Any:
    from harnessiq.providers.creatify.client import CreatifyClient

    if client is not None:
        return client
    if credentials is None:
        raise ValueError("Either Creatify credentials or a Creatify client must be provided.")
    return CreatifyClient(credentials=credentials)


def _require_operation_name(arguments: Mapping[str, object], allowed: frozenset[str]) -> str:
    value = arguments["operation"]
    if not isinstance(value, str):
        raise ValueError("The 'operation' argument must be a string.")
    if value not in allowed:
        raise ValueError(f"Unsupported Creatify operation '{value}'.")
    return value


def _optional_mapping(arguments: Mapping[str, object], key: str) -> Mapping[str, object] | None:
    v = arguments.get(key)
    if v is None:
        return None
    if not isinstance(v, Mapping):
        raise ValueError(f"The '{key}' argument must be an object when provided.")
    return v


def _build_tool_description(operations: Sequence[CreatifyOperation]) -> str:
    grouped: OrderedDict[str, list[str]] = OrderedDict()
    for op in operations:
        grouped.setdefault(op.category, []).append(op.summary())
    lines = ["Execute authenticated Creatify AI video creation API operations."]
    for category, summaries in grouped.items():
        lines.append(f"{category}: {', '.join(summaries)}")
    lines.append("Use 'path_params' for resource ids, 'query' for list filtering, 'payload' for JSON bodies.")
    return "\n".join(lines)


__all__ = [
    "CREATIFY_REQUEST",
    "CreatifyOperation",
    "CreatifyPreparedRequest",
    "_build_prepared_request",
    "build_creatify_operation_catalog",
    "build_creatify_request_tool_definition",
    "create_creatify_tools",
    "get_creatify_operation",
]
