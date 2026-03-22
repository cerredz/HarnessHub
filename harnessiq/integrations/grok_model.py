"""Grok (xAI) model adapter implementing the AgentModel protocol with LangSmith tracing.

Factory usage (CLI):
    --model-factory harnessiq.integrations.grok_model:create_grok_model

Environment variables read by the factory:
    XAI_API_KEY        — xAI API key (required)
    GROK_MODEL         — model name override (default: grok-4-1-fast)
    LANGSMITH_PROJECT  — LangSmith project name for trace grouping (optional)
    LANGSMITH_TRACING  — set to 'false' to disable tracing (default: enabled)
"""

from __future__ import annotations

import json
import os
from typing import Any

from harnessiq.providers.grok import GrokClient
from harnessiq.providers.langsmith import trace_model_call
from harnessiq.shared.agents import AgentModelRequest, AgentModelResponse
from harnessiq.shared.providers import ProviderMessage
from harnessiq.shared.tools import ToolCall

DEFAULT_GROK_MODEL = "grok-4-1-fast-reasoning"


class GrokAgentModel:
    """Wraps the Grok provider as an AgentModel with optional LangSmith tracing.

    Converts each AgentModelRequest into an OpenAI-compatible Grok request,
    parses the response into an AgentModelResponse, and wraps the call in a
    LangSmith 'llm' span so every turn is visible in the trace dashboard.

    Multi-turn context is reconstructed from the transcript on every call by
    converting transcript entries into alternating user/assistant messages.
    Tool calls stored as text in the transcript are embedded in assistant
    messages; tool results are sent as user messages.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str = DEFAULT_GROK_MODEL,
        max_tokens: int | None = None,
        project_name: str | None = None,
        tracing_enabled: bool = True,
    ) -> None:
        self._client = GrokClient(api_key=api_key)
        self._model_name = model_name
        self._max_tokens = max_tokens
        self._project_name = project_name
        self._tracing_enabled = tracing_enabled
        # Rebuilt each call from the request's tool definitions.
        self._name_to_key: dict[str, str] = {}

    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        """Generate one agent turn using Grok, traced as a LangSmith llm span."""
        self._name_to_key = {t.name: t.key for t in request.tools}
        messages = self._build_messages(request)
        tools = list(request.tools)

        def _call() -> Any:
            return self._client.create_chat_completion(
                model_name=self._model_name,
                system_prompt=request.system_prompt,
                messages=messages,
                tools=tools,
                max_tokens=self._max_tokens,
            )

        raw = trace_model_call(
            _call,
            provider="grok",
            model_name=self._model_name,
            system_prompt=request.system_prompt,
            messages=messages,
            tools=tools,
            project_name=self._project_name,
            enabled=self._tracing_enabled or None,
        )
        return self._parse_response(raw)

    def _build_messages(self, request: AgentModelRequest) -> list[ProviderMessage]:
        """Convert an AgentModelRequest into a Grok-compatible message list.

        The parameter block becomes the first user message. Transcript entries
        are grouped into alternating assistant/user turns so Grok sees a clean
        conversation history rather than a single monolithic prompt.
        """
        messages: list[ProviderMessage] = []
        param_block = request.render_parameter_block()
        first_user = param_block if param_block else "Begin the job search."

        messages.append({"role": "user", "content": first_user})

        if not request.transcript:
            return messages

        entries = list(request.transcript)
        i = 0
        while i < len(entries):
            entry = entries[i]

            if entry.entry_type == "assistant":
                # Collect the assistant message plus any immediately following tool_calls.
                parts: list[str] = []
                if entry.content.strip():
                    parts.append(entry.content.strip())
                i += 1
                while i < len(entries) and entries[i].entry_type == "tool_call":
                    parts.append(f"[TOOL CALL]\n{entries[i].content}")
                    i += 1
                messages.append(
                    {"role": "assistant", "content": "\n\n".join(parts) or "(continued)"}
                )

            elif entry.entry_type in ("tool_result", "summary"):
                # Collect consecutive tool results / summaries into one user turn.
                parts = []
                while i < len(entries) and entries[i].entry_type in ("tool_result", "summary"):
                    label = "[TOOL RESULT]" if entries[i].entry_type == "tool_result" else "[SUMMARY]"
                    parts.append(f"{label}\n{entries[i].content}")
                    i += 1
                messages.append({"role": "user", "content": "\n\n".join(parts)})

            else:
                # Orphaned tool_call entries should not appear, but skip defensively.
                i += 1

        # OpenAI-style APIs expect the last message to be from the user.
        if messages and messages[-1]["role"] == "assistant":
            messages.append({"role": "user", "content": "Continue."})

        return messages

    def _parse_response(self, raw: Any) -> AgentModelResponse:
        """Parse a raw Grok API response dict into an AgentModelResponse."""
        choice = raw["choices"][0]
        message = choice["message"]
        content: str = message.get("content") or ""
        raw_tool_calls: list[dict[str, Any]] = message.get("tool_calls") or []

        tool_calls: list[ToolCall] = []
        for raw_call in raw_tool_calls:
            func = raw_call["function"]
            tool_name: str = func["name"]
            # Map the tool name back to its registry key, falling back to a
            # linkedin-namespaced key so unknown tools still attempt to execute.
            tool_key = self._name_to_key.get(tool_name, f"linkedin.{tool_name}")
            arguments: dict[str, Any] = json.loads(func.get("arguments") or "{}")
            tool_calls.append(ToolCall(tool_key=tool_key, arguments=arguments))

        finish_reason: str = choice.get("finish_reason") or "stop"
        should_continue = bool(tool_calls) or finish_reason == "tool_calls"

        return AgentModelResponse(
            assistant_message=content,
            tool_calls=tuple(tool_calls),
            should_continue=should_continue,
        )


def create_grok_model() -> GrokAgentModel:
    """Factory for --model-factory CLI argument.

    Reads from environment:
        XAI_API_KEY        — required xAI API key
        GROK_MODEL         — model name (default: grok-4-1-fast)
        LANGSMITH_PROJECT  — LangSmith project name (optional)
        LANGSMITH_TRACING  — 'false' to disable tracing (default: enabled)
    """
    api_key = os.environ.get("XAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "XAI_API_KEY environment variable is required for the Grok model adapter."
        )
    model_name = os.environ.get("GROK_MODEL", DEFAULT_GROK_MODEL).strip() or DEFAULT_GROK_MODEL
    project_name = os.environ.get("LANGSMITH_PROJECT") or None
    tracing_raw = os.environ.get("LANGSMITH_TRACING", "true").strip().lower()
    tracing_enabled = tracing_raw not in ("false", "0", "no", "off")

    print(f"[GrokAgentModel] model={model_name}  tracing={tracing_enabled}  project={project_name}")
    return GrokAgentModel(
        api_key=api_key,
        model_name=model_name,
        project_name=project_name,
        tracing_enabled=tracing_enabled,
    )


__all__ = ["GrokAgentModel", "create_grok_model", "DEFAULT_GROK_MODEL"]
