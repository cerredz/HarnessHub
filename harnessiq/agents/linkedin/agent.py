"""LinkedIn-specific agent harness and durable memory helpers."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib import request

from harnessiq.agents.base import BaseAgent
from harnessiq.shared.agents import (
    DEFAULT_AGENT_MAX_TOKENS,
    DEFAULT_AGENT_RESET_THRESHOLD,
    AgentModel,
    AgentParameterSection,
    AgentPauseSignal,
    AgentRuntimeConfig,
    json_parameter_section,
)
from harnessiq.shared.linkedin import (
    DEFAULT_AGENT_IDENTITY,
    DEFAULT_LINKEDIN_ACTION_LOG_WINDOW,
    DEFAULT_LINKEDIN_NOTIFY_ON_PAUSE,
    DEFAULT_LINKEDIN_START_URL,
    LinkedInMemoryStore,
    SUPPORTED_LINKEDIN_RUNTIME_PARAMETERS,
    ActionLogEntry,
    JobApplicationRecord,
    LinkedInAgentConfig,
    LinkedInManagedFile,
    ScreenshotPersistor,
    normalize_linkedin_runtime_parameters,
)
from harnessiq.shared.tools import RegisteredTool, ToolDefinition
from harnessiq.tools.registry import create_tool_registry

# Default memory location: the `memory/` folder inside this agent's subdirectory.
# Users can override this by passing an explicit `memory_path` argument.
_DEFAULT_MEMORY_PATH = Path(__file__).parent / "memory"

# System prompt template loaded from disk so it can be updated without touching Python source.
_MASTER_PROMPT_PATH = Path(__file__).parent / "prompts" / "master_prompt.md"


class LinkedInJobApplierAgent(BaseAgent):
    """Concrete agent harness matching the LinkedIn job application specification."""

    def __init__(
        self,
        *,
        model: AgentModel,
        memory_path: str | Path | None = None,
        browser_tools: Iterable[RegisteredTool] = (),
        tools: Sequence[RegisteredTool] | None = None,
        screenshot_persistor: ScreenshotPersistor | None = None,
        max_tokens: int = DEFAULT_AGENT_MAX_TOKENS,
        reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD,
        action_log_window: int = DEFAULT_LINKEDIN_ACTION_LOG_WINDOW,
        linkedin_start_url: str = DEFAULT_LINKEDIN_START_URL,
        notify_on_pause: bool = DEFAULT_LINKEDIN_NOTIFY_ON_PAUSE,
        pause_webhook: str | None = None,
        runtime_config: AgentRuntimeConfig | None = None,
    ) -> None:
        # Store all params needed by build_instance_payload() before calling super().__init__().
        self._candidate_memory_path = Path(memory_path) if memory_path is not None else None
        self._payload_max_tokens = max_tokens
        self._payload_reset_threshold = reset_threshold
        self._payload_action_log_window = action_log_window
        self._payload_linkedin_start_url = linkedin_start_url
        self._payload_notify_on_pause = notify_on_pause
        self._payload_pause_webhook = pause_webhook
        self._screenshot_persistor = screenshot_persistor

        merged_runtime_config = AgentRuntimeConfig(
            max_tokens=max_tokens,
            reset_threshold=reset_threshold,
            output_sinks=runtime_config.output_sinks if runtime_config is not None else (),
            include_default_output_sink=(
                runtime_config.include_default_output_sink if runtime_config is not None else True
            ),
            prune_progress_interval=(
                runtime_config.prune_progress_interval if runtime_config is not None else None
            ),
            prune_token_limit=(
                runtime_config.prune_token_limit if runtime_config is not None else None
            ),
            langsmith_tracing_enabled=(
                runtime_config.langsmith_tracing_enabled if runtime_config is not None else True
            ),
            langsmith_api_key=(
                runtime_config.langsmith_api_key if runtime_config is not None else None
            ),
            langsmith_project=(
                runtime_config.langsmith_project if runtime_config is not None else None
            ),
            langsmith_api_url=(
                runtime_config.langsmith_api_url if runtime_config is not None else None
            ),
        )
        super().__init__(
            name="linkedin_job_applier",
            model=model,
            tool_executor=create_tool_registry(create_linkedin_browser_stub_tools()),
            runtime_config=merged_runtime_config,
            memory_path=self._candidate_memory_path,
            repo_root=_find_repo_root(self._candidate_memory_path),
        )
        resolved_memory_path = self.memory_path
        self._config = LinkedInAgentConfig(
            memory_path=resolved_memory_path,
            max_tokens=max_tokens,
            reset_threshold=reset_threshold,
            action_log_window=action_log_window,
            linkedin_start_url=linkedin_start_url,
            notify_on_pause=notify_on_pause,
            pause_webhook=pause_webhook,
        )
        self._memory_store = LinkedInMemoryStore(
            memory_path=resolved_memory_path,
            action_log_window=self._config.action_log_window,
        )
        self._tool_executor = create_tool_registry(
            create_linkedin_browser_stub_tools(),
            self._build_internal_tools(),
            tuple(browser_tools),
            tuple(tools or ()),
        )

    def build_instance_payload(self) -> dict[str, Any]:
        return _build_linkedin_instance_payload(
            memory_path=self._candidate_memory_path,
            max_tokens=self._payload_max_tokens,
            reset_threshold=self._payload_reset_threshold,
            action_log_window=self._payload_action_log_window,
            linkedin_start_url=self._payload_linkedin_start_url,
            notify_on_pause=self._payload_notify_on_pause,
            pause_webhook=self._payload_pause_webhook,
        )

    @property
    def config(self) -> LinkedInAgentConfig:
        return self._config

    @property
    def memory_store(self) -> LinkedInMemoryStore:
        return self._memory_store

    @classmethod
    def from_memory(
        cls,
        *,
        model: AgentModel,
        memory_path: str | Path | None = None,
        browser_tools: Iterable[RegisteredTool] = (),
        tools: Sequence[RegisteredTool] | None = None,
        screenshot_persistor: ScreenshotPersistor | None = None,
        runtime_overrides: Mapping[str, Any] | None = None,
        runtime_config: AgentRuntimeConfig | None = None,
    ) -> "LinkedInJobApplierAgent":
        resolved_path = _resolve_memory_path(memory_path)
        memory_store = LinkedInMemoryStore(memory_path=resolved_path)
        memory_store.prepare()
        runtime_parameters = memory_store.read_runtime_parameters()
        if runtime_overrides:
            runtime_parameters.update(runtime_overrides)
        return cls(
            model=model,
            memory_path=resolved_path,
            browser_tools=browser_tools,
            tools=tools,
            screenshot_persistor=screenshot_persistor,
            runtime_config=runtime_config,
            **normalize_linkedin_runtime_parameters(runtime_parameters),
        )

    def prepare(self) -> None:
        self._memory_store.prepare()

    def build_system_prompt(self) -> str:
        template = _MASTER_PROMPT_PATH.read_text(encoding="utf-8")
        identity = self._memory_store.read_agent_identity() or DEFAULT_AGENT_IDENTITY
        tool_lines = "\n".join(f"- {tool.name}: {tool.description}" for tool in self.available_tools())
        return (
            template
            .replace("{{AGENT_IDENTITY}}", identity)
            .replace("{{TOOL_LIST}}", tool_lines)
            .replace("{{ACTION_LOG_WINDOW}}", str(self._config.action_log_window))
        )

    def load_parameter_sections(self) -> Sequence[AgentParameterSection]:
        recent_actions = self._memory_store.read_recent_actions()
        recent_actions_text = "\n".join(json.dumps(entry.as_dict(), sort_keys=True) for entry in recent_actions)
        sections: list[AgentParameterSection] = [
            AgentParameterSection(
                title="Job Preferences",
                content=_or_placeholder(self._memory_store.read_job_preferences(), "(job preferences not set)"),
            ),
            AgentParameterSection(
                title="User Profile",
                content=_or_placeholder(self._memory_store.read_user_profile(), "(user profile not set)"),
            ),
            AgentParameterSection(
                title="Jobs Already Applied To",
                content=_or_placeholder(self._memory_store.read_applied_jobs_raw(), "(no applications recorded yet)"),
            ),
            AgentParameterSection(
                title=f"Recent Actions (last {self._config.action_log_window})",
                content=_or_placeholder(recent_actions_text, "(no recent actions recorded yet)"),
            ),
        ]
        runtime_parameters = self._memory_store.read_runtime_parameters()
        if runtime_parameters:
            sections.append(json_parameter_section("Runtime Parameters", runtime_parameters))
        custom_parameters = self._memory_store.read_custom_parameters()
        if custom_parameters:
            sections.append(json_parameter_section("Custom Parameters", custom_parameters))
        additional_prompt = self._memory_store.read_additional_prompt()
        if additional_prompt:
            sections.append(AgentParameterSection(title="Additional Prompt Data", content=additional_prompt))
        managed_files = [entry.as_dict() for entry in self._memory_store.read_managed_files()]
        if managed_files:
            sections.append(json_parameter_section("Managed Files", managed_files))
        return tuple(sections)

    def build_ledger_outputs(self) -> dict[str, Any]:
        return {
            "jobs_applied": [record.as_dict() for record in self._memory_store.read_applied_jobs()],
            "managed_files": [record.as_dict() for record in self._memory_store.read_managed_files()],
            "recent_actions": [record.as_dict() for record in self._memory_store.read_recent_actions()],
        }

    def build_ledger_tags(self) -> list[str]:
        return ["linkedin", "jobs"]

    def build_ledger_metadata(self) -> dict[str, Any]:
        return {
            "linkedin_start_url": self._config.linkedin_start_url,
            "notify_on_pause": self._config.notify_on_pause,
        }

    def _build_internal_tools(self) -> tuple[RegisteredTool, ...]:
        return (
            RegisteredTool(
                definition=_tool_definition(
                    key="linkedin.append_action",
                    name="append_action",
                    description="Append a semantic action description and outcome to action_log.jsonl.",
                    properties={
                        "action": {"type": "string", "description": "Human-readable description of the action taken."},
                        "result": {"type": "string", "description": "Outcome or observation for the action."},
                    },
                    required=("action", "result"),
                ),
                handler=self._handle_append_action,
            ),
            RegisteredTool(
                definition=_tool_definition(
                    key="linkedin.append_company",
                    name="append_company",
                    description="Append a structured job record to applied_jobs.jsonl immediately after an application is submitted.",
                    properties={
                        "job_id": {"type": "string", "description": "LinkedIn job identifier."},
                        "title": {"type": "string", "description": "Job title."},
                        "company": {"type": "string", "description": "Company name."},
                        "url": {"type": "string", "description": "Canonical LinkedIn job URL."},
                        "status": {"type": "string", "description": "Application status. Defaults to 'applied'."},
                        "easy_apply": {"type": "boolean", "description": "Whether the job used Easy Apply."},
                        "notes": {"type": "string", "description": "Optional free-form notes about the submission."},
                    },
                    required=("job_id", "title", "company", "url"),
                ),
                handler=self._handle_append_company,
            ),
            RegisteredTool(
                definition=_tool_definition(
                    key="linkedin.update_job_status",
                    name="update_job_status",
                    description="Append a newer record for an existing job with an updated status and notes.",
                    properties={
                        "job_id": {"type": "string", "description": "LinkedIn job identifier."},
                        "status": {"type": "string", "description": "New status such as applied, failed, or skipped."},
                        "notes": {"type": "string", "description": "Reason or detail for the status change."},
                    },
                    required=("job_id", "status", "notes"),
                ),
                handler=self._handle_update_job_status,
            ),
            RegisteredTool(
                definition=_tool_definition(
                    key="linkedin.read_memory_file",
                    name="read_memory_file",
                    description="Read a text file from the configured memory path.",
                    properties={"filename": {"type": "string", "description": "Path relative to the memory directory."}},
                    required=("filename",),
                ),
                handler=self._handle_read_memory_file,
            ),
            RegisteredTool(
                definition=_tool_definition(
                    key="linkedin.save_screenshot_to_memory",
                    name="save_screenshot_to_memory",
                    description="Persist the current browser screenshot to MEMORY_PATH/screenshots/ with a timestamped filename.",
                    properties={"label": {"type": "string", "description": "Short label used in the screenshot filename."}},
                    required=("label",),
                ),
                handler=self._handle_save_screenshot_to_memory,
            ),
            RegisteredTool(
                definition=_tool_definition(
                    key="linkedin.pause_and_notify",
                    name="pause_and_notify",
                    description="Pause the harness and optionally notify an external webhook about the blocker.",
                    properties={"reason": {"type": "string", "description": "Why human intervention is required."}},
                    required=("reason",),
                ),
                handler=self._handle_pause_and_notify,
            ),
            RegisteredTool(
                definition=_tool_definition(
                    key="linkedin.mark_job_skipped",
                    name="mark_job_skipped",
                    description="Append a skipped job record so the same LinkedIn posting is not reconsidered later.",
                    properties={
                        "job_id": {"type": "string", "description": "LinkedIn job identifier."},
                        "title": {"type": "string", "description": "Job title."},
                        "company": {"type": "string", "description": "Company name."},
                        "url": {"type": "string", "description": "Canonical LinkedIn job URL."},
                        "reason": {"type": "string", "description": "Why the job was skipped."},
                    },
                    required=("job_id", "title", "company", "url", "reason"),
                ),
                handler=self._handle_mark_job_skipped,
            ),
        )

    def _handle_append_action(self, arguments: dict[str, Any]) -> dict[str, Any]:
        entry = self._memory_store.append_action(action=str(arguments["action"]), result=str(arguments["result"]))
        return entry.as_dict()

    def _handle_append_company(self, arguments: dict[str, Any]) -> dict[str, Any]:
        record = JobApplicationRecord(
            job_id=str(arguments["job_id"]),
            title=str(arguments["title"]),
            company=str(arguments["company"]),
            url=str(arguments["url"]),
            applied_at=_utcnow(),
            status=str(arguments.get("status", "applied")),
            easy_apply=bool(arguments["easy_apply"]) if "easy_apply" in arguments else None,
            notes=str(arguments["notes"]) if arguments.get("notes") is not None else None,
        )
        return self._memory_store.append_job_record(record).as_dict()

    def _handle_update_job_status(self, arguments: dict[str, Any]) -> dict[str, Any]:
        record = self._memory_store.update_job_status(
            job_id=str(arguments["job_id"]),
            status=str(arguments["status"]),
            notes=str(arguments["notes"]),
        )
        return record.as_dict()

    def _handle_read_memory_file(self, arguments: dict[str, Any]) -> dict[str, Any]:
        filename = str(arguments["filename"])
        return {"filename": filename, "content": self._memory_store.read_memory_file(filename)}

    def _handle_save_screenshot_to_memory(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if self._screenshot_persistor is None:
            message = "Screenshot persistence is not configured for this agent instance."
            raise RuntimeError(message)
        label = _sanitize_label(str(arguments["label"]))
        output_path = self._memory_store.screenshot_dir / f"{_timestamp_for_filename()}_{label}.png"
        self._screenshot_persistor(output_path, label)
        if not output_path.exists():
            message = f"Screenshot persistor did not create '{output_path}'."
            raise RuntimeError(message)
        return {"path": str(output_path)}

    def _handle_pause_and_notify(self, arguments: dict[str, Any]) -> AgentPauseSignal:
        reason = str(arguments["reason"])
        details = self._notify_on_pause(reason)
        return AgentPauseSignal(reason=reason, details=details)

    def _handle_mark_job_skipped(self, arguments: dict[str, Any]) -> dict[str, Any]:
        record = self._memory_store.mark_job_skipped(
            job_id=str(arguments["job_id"]),
            title=str(arguments["title"]),
            company=str(arguments["company"]),
            url=str(arguments["url"]),
            reason=str(arguments["reason"]),
        )
        return record.as_dict()

    def _notify_on_pause(self, reason: str) -> dict[str, Any]:
        details: dict[str, Any] = {"notified": False}
        if not self._config.notify_on_pause:
            return details
        details["notified"] = True
        details["timestamp"] = _utcnow()
        if self._config.pause_webhook is None:
            return details

        payload = json.dumps({"agent": self.name, "reason": reason, "timestamp": details["timestamp"]}).encode("utf-8")
        webhook_request = request.Request(
            self._config.pause_webhook,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(webhook_request, timeout=10) as response:
                details["webhook_status"] = getattr(response, "status", None)
        except Exception as exc:  # pragma: no cover - depends on external environment
            details["notification_error"] = str(exc)
        return details


def create_linkedin_browser_stub_tools() -> tuple[RegisteredTool, ...]:
    return tuple(
        RegisteredTool(definition=definition, handler=_unavailable_browser_handler(definition.name))
        for definition in build_linkedin_browser_tool_definitions()
    )


def build_linkedin_browser_tool_definitions() -> tuple[ToolDefinition, ...]:
    return (
        _tool_definition(
            key="linkedin.navigate",
            name="navigate",
            description="Navigate the browser to a URL.",
            properties={"url": {"type": "string", "description": "Target URL."}},
            required=("url",),
        ),
        _tool_definition(
            key="linkedin.click",
            name="click",
            description="Click a DOM element by selector or accessible name.",
            properties={"selector": {"type": "string", "description": "Element selector or accessible name."}},
            required=("selector",),
        ),
        _tool_definition(
            key="linkedin.type",
            name="type",
            description="Focus an input and type text into it after clearing the current value.",
            properties={
                "selector": {"type": "string", "description": "Input selector."},
                "text": {"type": "string", "description": "Text to type."},
            },
            required=("selector", "text"),
        ),
        _tool_definition(
            key="linkedin.select_option",
            name="select_option",
            description="Select an option in a dropdown by value or label.",
            properties={
                "selector": {"type": "string", "description": "Select element selector."},
                "value": {"type": "string", "description": "Option value or visible label."},
            },
            required=("selector", "value"),
        ),
        _tool_definition(
            key="linkedin.hover",
            name="hover",
            description="Hover over an element without clicking it.",
            properties={"selector": {"type": "string", "description": "Element selector."}},
            required=("selector",),
        ),
        _tool_definition(
            key="linkedin.upload_file",
            name="upload_file",
            description="Upload a file through a file input on the current page.",
            properties={
                "selector": {"type": "string", "description": "File input selector."},
                "file_path": {"type": "string", "description": "Path to the file that should be uploaded."},
            },
            required=("selector", "file_path"),
        ),
        _tool_definition(
            key="linkedin.press_key",
            name="press_key",
            description="Send a keyboard event such as Enter, Tab, or Escape.",
            properties={"key": {"type": "string", "description": "Keyboard key value."}},
            required=("key",),
        ),
        _tool_definition(
            key="linkedin.scroll",
            name="scroll",
            description="Scroll the page up or down by a pixel amount.",
            properties={
                "direction": {"type": "string", "enum": ["up", "down"], "description": "Scroll direction."},
                "amount": {"type": "integer", "description": "Number of pixels to scroll."},
            },
            required=("direction", "amount"),
        ),
        _tool_definition(
            key="linkedin.wait_for_element",
            name="wait_for_element",
            description="Wait until a selector appears in the DOM or the timeout expires.",
            properties={
                "selector": {"type": "string", "description": "Element selector to wait for."},
                "timeout_ms": {"type": "integer", "description": "Maximum wait time in milliseconds."},
            },
            required=("selector", "timeout_ms"),
        ),
        _tool_definition(
            key="linkedin.screenshot",
            name="screenshot",
            description="Capture a screenshot of the current browser state and return it to the model.",
            properties={},
        ),
        _tool_definition(
            key="linkedin.view_html",
            name="view_html",
            description="Return the raw HTML of the current page.",
            properties={},
        ),
        _tool_definition(
            key="linkedin.get_text",
            name="get_text",
            description="Return the visible text of the current page without HTML markup.",
            properties={},
        ),
        _tool_definition(
            key="linkedin.find_element",
            name="find_element",
            description="Return whether a selector or text exists on the current page.",
            properties={"selector": {"type": "string", "description": "Selector or text to search for."}},
            required=("selector",),
        ),
        _tool_definition(
            key="linkedin.get_current_url",
            name="get_current_url",
            description="Return the current browser URL.",
            properties={},
        ),
    )


def _resolve_memory_path(memory_path: str | Path | None) -> Path:
    """Resolve a memory path argument to an absolute Path.

    When ``memory_path`` is ``None`` the agent's default memory directory
    (``harnessiq/agents/linkedin/memory/``) is used.
    """
    if memory_path is None:
        return _DEFAULT_MEMORY_PATH
    return Path(memory_path)


def _build_linkedin_instance_payload(
    *,
    memory_path: Path | None,
    max_tokens: int,
    reset_threshold: float,
    action_log_window: int,
    linkedin_start_url: str,
    notify_on_pause: bool,
    pause_webhook: str | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "runtime": {
            "action_log_window": action_log_window,
            "linkedin_start_url": linkedin_start_url,
            "max_tokens": max_tokens,
            "notify_on_pause": notify_on_pause,
            "pause_webhook": pause_webhook,
            "reset_threshold": reset_threshold,
        }
    }
    if memory_path is not None:
        payload["memory_path"] = str(memory_path)
    if memory_path is None or not memory_path.exists():
        return payload

    store = LinkedInMemoryStore(memory_path=memory_path)
    payload["job_preferences"] = _read_optional_text(store.job_preferences_path)
    payload["user_profile"] = _read_optional_text(store.user_profile_path)
    payload["agent_identity"] = _read_optional_text(store.agent_identity_path)
    payload["additional_prompt"] = _read_optional_text(store.additional_prompt_path)
    runtime_parameters = store.read_runtime_parameters() if store.runtime_parameters_path.exists() else {}
    custom_parameters = store.read_custom_parameters() if store.custom_parameters_path.exists() else {}
    if runtime_parameters:
        payload["runtime"] = runtime_parameters
    if custom_parameters:
        payload["custom"] = custom_parameters
    return payload


def _unavailable_browser_handler(tool_name: str):
    def handler(arguments: dict[str, Any]) -> dict[str, Any]:
        message = f"Browser tool '{tool_name}' requires a runtime handler."
        raise RuntimeError(message)

    return handler


def _tool_definition(
    *,
    key: str,
    name: str,
    description: str,
    properties: dict[str, Any],
    required: Sequence[str] = (),
) -> ToolDefinition:
    return ToolDefinition(
        key=key,
        name=name,
        description=description,
        input_schema={
            "type": "object",
            "properties": properties,
            "required": list(required),
            "additionalProperties": False,
        },
    )


def _or_placeholder(value: str, placeholder: str) -> str:
    return value if value else placeholder


def _sanitize_label(label: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", label).strip("-")
    return cleaned or "screenshot"


def _relative_path_text(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _read_optional_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _find_repo_root(path: Path | None) -> Path:
    if path is None:
        return Path.cwd()
    resolved = path.resolve()
    for candidate in (resolved, *resolved.parents):
        if (candidate / ".git").exists():
            return candidate
    if resolved.parent.name == "linkedin" and resolved.parent.parent.name == "memory":
        return resolved.parent.parent.parent
    return Path.cwd()


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _timestamp_for_filename() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


__all__ = [
    "ActionLogEntry",
    "JobApplicationRecord",
    "LinkedInAgentConfig",
    "LinkedInManagedFile",
    "LinkedInJobApplierAgent",
    "LinkedInMemoryStore",
    "ScreenshotPersistor",
    "SUPPORTED_LINKEDIN_RUNTIME_PARAMETERS",
    "build_linkedin_browser_tool_definitions",
    "create_linkedin_browser_stub_tools",
    "normalize_linkedin_runtime_parameters",
]
