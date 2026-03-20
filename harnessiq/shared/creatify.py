"""Creatify shared operation metadata."""

from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Literal, Sequence

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

__all__ = [
    "CreatifyOperation",
    "CreatifyPreparedRequest",
    "build_creatify_operation_catalog",
    "get_creatify_operation",
]
