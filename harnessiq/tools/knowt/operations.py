"""Knowt agent tool implementations for the content creation pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Mapping

from harnessiq.shared.dtos import ProviderOperationRequestDTO
from harnessiq.shared.tools import (
    FILES_CREATE_FILE,
    FILES_EDIT_FILE,
    KNOWT_CREATE_AVATAR_DESCRIPTION,
    KNOWT_CREATE_SCRIPT,
    KNOWT_CREATE_VIDEO,
    RegisteredTool,
    ToolArguments,
    ToolDefinition,
)

if TYPE_CHECKING:
    from harnessiq.providers.creatify.client import CreatifyClient, CreatifyCredentials
    from harnessiq.shared.knowt import KnowtMemoryStore


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_knowt_tools(
    *,
    memory_store: "KnowtMemoryStore",
    creatify_client: "CreatifyClient | None" = None,
    creatify_credentials: "CreatifyCredentials | None" = None,
) -> tuple[RegisteredTool, ...]:
    """Return all five Knowt content-creation tools backed by *memory_store*.

    Provide either *creatify_credentials* or an already-constructed
    *creatify_client* to enable the ``knowt.create_video`` tool. When
    neither is given, ``create_video`` is still registered but returns a
    configuration error on invocation.
    """
    resolved_client = _coerce_creatify_client(
        credentials=creatify_credentials, client=creatify_client
    )
    return (
        _build_create_script_tool(memory_store),
        _build_create_avatar_description_tool(memory_store),
        _build_create_video_tool(memory_store, resolved_client),
        _build_create_file_tool(memory_store),
        _build_edit_file_tool(memory_store),
    )


# ---------------------------------------------------------------------------
# create_script
# ---------------------------------------------------------------------------


def _build_create_script_tool(memory_store: "KnowtMemoryStore") -> RegisteredTool:
    def handler(arguments: ToolArguments) -> dict[str, Any]:
        topic = _require_string(arguments, "topic")
        angle = _require_string(arguments, "angle")
        script_text = _require_string(arguments, "script_text")

        path = memory_store.write_script(script_text)
        memory_store.append_creation_log({
            "timestamp": _utcnow(),
            "action": "create_script",
            "summary": f"Wrote script for topic '{topic}', angle '{angle}'.",
        })
        return {
            "script": script_text,
            "topic": topic,
            "angle": angle,
            "stored_to": path.name,
        }

    return RegisteredTool(
        definition=ToolDefinition(
            key=KNOWT_CREATE_SCRIPT,
            name="create_script",
            description=(
                "Finalize and store the TikTok script in agent memory. "
                "Call reason.brainstorm first to generate ideas, select the best angle, "
                "then call this tool with the final script text. "
                "Must be called before create_avatar_description and create_video."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "The subject or theme of the TikTok script.",
                    },
                    "angle": {
                        "type": "string",
                        "description": "The specific angle or hook selected from brainstorming.",
                    },
                    "script_text": {
                        "type": "string",
                        "description": "The full TikTok script text to store in agent memory.",
                    },
                },
                "required": ["topic", "angle", "script_text"],
                "additionalProperties": False,
            },
        ),
        handler=handler,
    )


# ---------------------------------------------------------------------------
# create_avatar_description
# ---------------------------------------------------------------------------


def _build_create_avatar_description_tool(memory_store: "KnowtMemoryStore") -> RegisteredTool:
    def handler(arguments: ToolArguments) -> dict[str, Any]:
        script_text = _require_string(arguments, "script_text")
        avatar_style = _require_string(arguments, "avatar_style")
        target_audience = _optional_string(arguments, "target_audience") or "general audience"
        tone = _optional_string(arguments, "tone") or "engaging and professional"

        # Build chain-of-thought reasoning block from the inputs
        keywords = _extract_keywords(script_text)
        cot_lines = [
            "[AVATAR REASONING]",
            f"Script keywords identified: {', '.join(keywords) if keywords else 'general content'}",
            f"Target audience: {target_audience}",
            f"Desired tone: {tone}",
            f"Selected style: {avatar_style}",
            "",
            f"Rationale: The script discusses {', '.join(keywords[:3]) if keywords else 'the topic'}, "
            f"which resonates best with a {avatar_style.lower()} avatar that matches "
            f"the {tone.lower()} tone expected by {target_audience}.",
        ]
        chain_of_thought = "\n".join(cot_lines)

        avatar_description = (
            f"Avatar style: {avatar_style}. "
            f"Tone: {tone}. "
            f"Target audience: {target_audience}. "
            f"The avatar should embody a {avatar_style.lower()} persona that feels authentic "
            f"to {target_audience} and delivers the script with {tone.lower()} energy."
        )

        path = memory_store.write_avatar_description(avatar_description)
        memory_store.append_creation_log({
            "timestamp": _utcnow(),
            "action": "create_avatar_description",
            "summary": f"Wrote avatar description: {avatar_style} style for {target_audience}.",
        })
        return {
            "chain_of_thought": chain_of_thought,
            "avatar_description": avatar_description,
            "stored_to": path.name,
        }

    return RegisteredTool(
        definition=ToolDefinition(
            key=KNOWT_CREATE_AVATAR_DESCRIPTION,
            name="create_avatar_description",
            description=(
                "Generate and store a semantic avatar description for the video. "
                "Outputs a chain-of-thought reasoning block followed by the final description. "
                "Must be called after create_script and before create_video."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "script_text": {
                        "type": "string",
                        "description": "The finalized script text used to inform avatar selection.",
                    },
                    "avatar_style": {
                        "type": "string",
                        "description": (
                            "Descriptive style for the avatar "
                            "(e.g., 'young professional', 'friendly educator', 'energetic coach')."
                        ),
                    },
                    "target_audience": {
                        "type": "string",
                        "description": "Optional description of the intended audience.",
                    },
                    "tone": {
                        "type": "string",
                        "description": "Optional tone descriptor (e.g., 'enthusiastic', 'calm and authoritative').",
                    },
                },
                "required": ["script_text", "avatar_style"],
                "additionalProperties": False,
            },
        ),
        handler=handler,
    )


# ---------------------------------------------------------------------------
# create_video
# ---------------------------------------------------------------------------


def _build_create_video_tool(
    memory_store: "KnowtMemoryStore",
    creatify_client: "CreatifyClient | None",
) -> RegisteredTool:
    def handler(arguments: ToolArguments) -> dict[str, Any]:
        # Memory guard — enforce pipeline order deterministically
        missing: list[str] = []
        if not memory_store.is_script_created():
            missing.append("create_script")
        if not memory_store.is_avatar_description_created():
            missing.append("create_avatar_description")
        if missing:
            return {
                "error": (
                    "create_video cannot be called before both create_script and "
                    "create_avatar_description have been completed."
                ),
                "missing": missing,
                "resolution": (
                    "Complete the missing steps in order — "
                    + " → ".join(missing)
                    + " → create_video — then retry."
                ),
            }

        if creatify_client is None:
            return {
                "error": (
                    "No Creatify client is configured. "
                    "Pass creatify_credentials or creatify_client to create_knowt_tools()."
                ),
            }

        script = _require_string(arguments, "script")
        avatar_id = _require_string(arguments, "avatar_id")
        voice_id = _require_string(arguments, "voice_id")
        aspect_ratio = _optional_string(arguments, "aspect_ratio") or "9:16"
        name = _optional_string(arguments, "name")
        background_url = _optional_string(arguments, "background_url")

        payload: dict[str, Any] = {
            "script": script,
            "avatar_id": avatar_id,
            "voice_id": voice_id,
            "aspect_ratio": aspect_ratio,
        }
        if name:
            payload["name"] = name
        if background_url:
            payload["background_url"] = background_url

        response = creatify_client.execute_operation(
            ProviderOperationRequestDTO(
                operation="create_lipsync_v2",
                payload=payload,
            )
        ).response
        memory_store.append_creation_log({
            "timestamp": _utcnow(),
            "action": "create_video",
            "summary": f"Submitted create_lipsync_v2 for avatar_id={avatar_id}.",
        })
        return {
            "operation": "create_lipsync_v2",
            "response": response,
        }

    return RegisteredTool(
        definition=ToolDefinition(
            key=KNOWT_CREATE_VIDEO,
            name="create_video",
            description=(
                "Submit a Creatify AI Avatar v2 video creation job using the finalized script "
                "and avatar configuration. Must only be called after both create_script and "
                "create_avatar_description have completed — calling earlier returns a descriptive "
                "error explaining which steps are missing. Parameters map directly to the "
                "Creatify create_lipsync_v2 API payload."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                        "description": "Voiceover script text for the AI avatar.",
                    },
                    "avatar_id": {
                        "type": "string",
                        "description": "Creatify avatar ID to use for the video.",
                    },
                    "voice_id": {
                        "type": "string",
                        "description": "Creatify voice ID for the text-to-speech audio.",
                    },
                    "aspect_ratio": {
                        "type": "string",
                        "description": "Video aspect ratio. Defaults to '9:16' for TikTok.",
                    },
                    "name": {
                        "type": "string",
                        "description": "Optional name for the video job in Creatify.",
                    },
                    "background_url": {
                        "type": "string",
                        "description": "Optional URL for a background image or video.",
                    },
                },
                "required": ["script", "avatar_id", "voice_id"],
                "additionalProperties": False,
            },
        ),
        handler=handler,
    )


# ---------------------------------------------------------------------------
# create_file
# ---------------------------------------------------------------------------


def _build_create_file_tool(memory_store: "KnowtMemoryStore") -> RegisteredTool:
    def handler(arguments: ToolArguments) -> dict[str, Any]:
        filename = _require_string(arguments, "filename")
        content = arguments.get("content", "")
        if not isinstance(content, str):
            raise ValueError("'content' must be a string.")
        path = memory_store.write_file(filename, content)
        return {"filename": filename, "path": str(path), "action": "created"}

    return RegisteredTool(
        definition=ToolDefinition(
            key=FILES_CREATE_FILE,
            name="create_file",
            description=(
                "Create or overwrite a file inside the agent's memory directory. "
                "Use for persisting notes, draft content, or any text artifact needed "
                "across the content creation pipeline."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Filename relative to the agent memory directory (e.g., 'notes.md').",
                    },
                    "content": {
                        "type": "string",
                        "description": "Text content to write to the file.",
                    },
                },
                "required": ["filename", "content"],
                "additionalProperties": False,
            },
        ),
        handler=handler,
    )


# ---------------------------------------------------------------------------
# edit_file
# ---------------------------------------------------------------------------


def _build_edit_file_tool(memory_store: "KnowtMemoryStore") -> RegisteredTool:
    def handler(arguments: ToolArguments) -> dict[str, Any]:
        filename = _require_string(arguments, "filename")
        content = arguments.get("content", "")
        if not isinstance(content, str):
            raise ValueError("'content' must be a string.")
        path = memory_store.edit_file(filename, content)
        return {"filename": filename, "path": str(path), "action": "edited"}

    return RegisteredTool(
        definition=ToolDefinition(
            key=FILES_EDIT_FILE,
            name="edit_file",
            description=(
                "Overwrite the content of an existing file inside the agent's memory directory. "
                "Use to update notes, drafts, or any previously created text artifact."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Filename relative to the agent memory directory.",
                    },
                    "content": {
                        "type": "string",
                        "description": "New text content to write to the file.",
                    },
                },
                "required": ["filename", "content"],
                "additionalProperties": False,
            },
        ),
        handler=handler,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _coerce_creatify_client(
    *,
    credentials: "CreatifyCredentials | None",
    client: "CreatifyClient | None",
) -> "CreatifyClient | None":
    if client is not None:
        return client
    if credentials is not None:
        from harnessiq.providers.creatify.client import CreatifyClient
        return CreatifyClient(credentials=credentials)
    return None


def _require_string(arguments: Mapping[str, Any], key: str) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{key}' must be a non-empty string.")
    return value.strip()


def _optional_string(arguments: Mapping[str, Any], key: str) -> str:
    value = arguments.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"'{key}' must be a string when provided.")
    return value.strip()


def _extract_keywords(text: str, max_keywords: int = 5) -> list[str]:
    """Extract simple keyword tokens from text for CoT generation."""
    import re
    # Keep only alphabetic words, 4+ chars, skip common stopwords
    stopwords = {"that", "this", "with", "have", "will", "from", "they", "your", "more"}
    words = re.findall(r"\b[a-zA-Z]{4,}\b", text)
    seen: set[str] = set()
    keywords: list[str] = []
    for word in words:
        lower = word.lower()
        if lower not in stopwords and lower not in seen:
            seen.add(lower)
            keywords.append(lower)
        if len(keywords) >= max_keywords:
            break
    return keywords


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = ["create_knowt_tools"]
