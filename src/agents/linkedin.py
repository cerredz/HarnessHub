"""LinkedIn-specific agent harness and durable memory helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib import request

from src.agents.base import BaseAgent
from src.shared.agents import (
    DEFAULT_AGENT_MAX_TOKENS,
    DEFAULT_AGENT_RESET_THRESHOLD,
    AgentModel,
    AgentParameterSection,
    AgentPauseSignal,
    AgentRuntimeConfig,
)
from src.shared.linkedin import (
    ACTION_LOG_FILENAME,
    AGENT_IDENTITY_FILENAME,
    APPLIED_JOBS_FILENAME,
    DEFAULT_AGENT_IDENTITY,
    DEFAULT_JOB_PREFERENCES,
    DEFAULT_LINKEDIN_ACTION_LOG_WINDOW,
    DEFAULT_LINKEDIN_NOTIFY_ON_PAUSE,
    DEFAULT_LINKEDIN_START_URL,
    DEFAULT_USER_PROFILE,
    JOB_PREFERENCES_FILENAME,
    SCREENSHOT_DIRNAME,
    USER_PROFILE_FILENAME,
    ActionLogEntry,
    JobApplicationRecord,
    LinkedInAgentConfig,
    ScreenshotPersistor,
)
from src.shared.tools import RegisteredTool, ToolDefinition
from src.tools.registry import ToolRegistry


@dataclass(slots=True)
class LinkedInMemoryStore:
    """Manage the durable state files used by the LinkedIn harness."""

    memory_path: Path
    action_log_window: int = DEFAULT_LINKEDIN_ACTION_LOG_WINDOW

    def __post_init__(self) -> None:
        self.memory_path = Path(self.memory_path)

    @property
    def job_preferences_path(self) -> Path:
        return self.memory_path / JOB_PREFERENCES_FILENAME

    @property
    def user_profile_path(self) -> Path:
        return self.memory_path / USER_PROFILE_FILENAME

    @property
    def agent_identity_path(self) -> Path:
        return self.memory_path / AGENT_IDENTITY_FILENAME

    @property
    def applied_jobs_path(self) -> Path:
        return self.memory_path / APPLIED_JOBS_FILENAME

    @property
    def action_log_path(self) -> Path:
        return self.memory_path / ACTION_LOG_FILENAME

    @property
    def screenshot_dir(self) -> Path:
        return self.memory_path / SCREENSHOT_DIRNAME

    def prepare(self) -> None:
        self.memory_path.mkdir(parents=True, exist_ok=True)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        _ensure_text_file(self.job_preferences_path, DEFAULT_JOB_PREFERENCES)
        _ensure_text_file(self.user_profile_path, DEFAULT_USER_PROFILE)
        _ensure_text_file(self.agent_identity_path, DEFAULT_AGENT_IDENTITY)
        _ensure_text_file(self.applied_jobs_path, "")
        _ensure_text_file(self.action_log_path, "")

    def read_job_preferences(self) -> str:
        return self.job_preferences_path.read_text(encoding="utf-8").strip()

    def read_user_profile(self) -> str:
        return self.user_profile_path.read_text(encoding="utf-8").strip()

    def read_agent_identity(self) -> str:
        return self.agent_identity_path.read_text(encoding="utf-8").strip()

    def read_applied_jobs_raw(self) -> str:
        return self.applied_jobs_path.read_text(encoding="utf-8").strip()

    def read_memory_file(self, filename: str) -> str:
        requested_path = (self.memory_path / filename).resolve()
        root_path = self.memory_path.resolve()
        if root_path not in requested_path.parents and requested_path != root_path:
            message = f"Memory file '{filename}' is outside the configured memory path."
            raise ValueError(message)
        return requested_path.read_text(encoding="utf-8")

    def append_action(self, action: str, result: str) -> ActionLogEntry:
        entry = ActionLogEntry(timestamp=_utcnow(), action=action, result=result)
        self._append_jsonl(self.action_log_path, entry.as_dict())
        return entry

    def append_job_record(self, record: JobApplicationRecord) -> JobApplicationRecord:
        self._append_jsonl(self.applied_jobs_path, record.as_dict())
        return record

    def mark_job_skipped(
        self,
        *,
        job_id: str,
        title: str,
        company: str,
        url: str,
        reason: str,
    ) -> JobApplicationRecord:
        record = JobApplicationRecord(
            job_id=job_id,
            title=title,
            company=company,
            url=url,
            applied_at=_utcnow(),
            status="skipped",
            notes=reason,
        )
        return self.append_job_record(record)

    def update_job_status(self, job_id: str, status: str, notes: str) -> JobApplicationRecord:
        current_record = self.current_jobs().get(job_id)
        if current_record is None:
            message = f"Job '{job_id}' does not exist in applied_jobs.jsonl."
            raise ValueError(message)
        updated_record = JobApplicationRecord(
            job_id=current_record.job_id,
            title=current_record.title,
            company=current_record.company,
            url=current_record.url,
            applied_at=current_record.applied_at,
            status=status,
            easy_apply=current_record.easy_apply,
            notes=notes,
            updated_at=_utcnow(),
        )
        return self.append_job_record(updated_record)

    def read_applied_jobs(self) -> list[JobApplicationRecord]:
        return [JobApplicationRecord.from_dict(payload) for payload in self._read_jsonl(self.applied_jobs_path)]

    def current_jobs(self) -> dict[str, JobApplicationRecord]:
        records: dict[str, JobApplicationRecord] = {}
        for record in self.read_applied_jobs():
            records[record.job_id] = record
        return records

    def read_recent_actions(self) -> list[ActionLogEntry]:
        entries = [ActionLogEntry.from_dict(payload) for payload in self._read_jsonl(self.action_log_path)]
        return entries[-self.action_log_window :]

    def _append_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True))
            handle.write("\n")

    def _read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        entries: list[dict[str, Any]] = []
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            entries.append(json.loads(line))
        return entries


class LinkedInJobApplierAgent(BaseAgent):
    """Concrete agent harness matching the LinkedIn job application specification."""

    def __init__(
        self,
        *,
        model: AgentModel,
        memory_path: str | Path,
        browser_tools: Iterable[RegisteredTool] = (),
        screenshot_persistor: ScreenshotPersistor | None = None,
        max_tokens: int = DEFAULT_AGENT_MAX_TOKENS,
        reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD,
        action_log_window: int = DEFAULT_LINKEDIN_ACTION_LOG_WINDOW,
        linkedin_start_url: str = DEFAULT_LINKEDIN_START_URL,
        notify_on_pause: bool = DEFAULT_LINKEDIN_NOTIFY_ON_PAUSE,
        pause_webhook: str | None = None,
    ) -> None:
        self._config = LinkedInAgentConfig(
            memory_path=Path(memory_path),
            max_tokens=max_tokens,
            reset_threshold=reset_threshold,
            action_log_window=action_log_window,
            linkedin_start_url=linkedin_start_url,
            notify_on_pause=notify_on_pause,
            pause_webhook=pause_webhook,
        )
        self._memory_store = LinkedInMemoryStore(
            memory_path=self._config.memory_path,
            action_log_window=self._config.action_log_window,
        )
        self._screenshot_persistor = screenshot_persistor

        tool_registry = ToolRegistry(
            _merge_tools(
                create_linkedin_browser_stub_tools(),
                self._build_internal_tools(),
                tuple(browser_tools),
            )
        )
        runtime_config = AgentRuntimeConfig(
            max_tokens=self._config.max_tokens,
            reset_threshold=self._config.reset_threshold,
        )
        super().__init__(
            name="linkedin_job_applier",
            model=model,
            tool_executor=tool_registry,
            runtime_config=runtime_config,
        )

    @property
    def config(self) -> LinkedInAgentConfig:
        return self._config

    @property
    def memory_store(self) -> LinkedInMemoryStore:
        return self._memory_store

    def prepare(self) -> None:
        self._memory_store.prepare()

    def build_system_prompt(self) -> str:
        identity = self._memory_store.read_agent_identity() or DEFAULT_AGENT_IDENTITY
        tool_lines = [f"- {tool.name}: {tool.description}" for tool in self.available_tools()]
        behavioral_rules = [
            "- Never apply to a job whose `job_id` appears in applied_jobs.jsonl.",
            "- After each application, append to applied_jobs.jsonl immediately.",
            "- After each meaningful action, append a semantic description to action_log.jsonl.",
            "- If a CAPTCHA or login wall is encountered, call `pause_and_notify`.",
            "- Do not apply to roles that do not match the user's stated criteria.",
            "- Prefer LinkedIn Easy Apply when available.",
            "- Use user_profile.md for application fields instead of inventing answers.",
        ]
        sections = [
            "[IDENTITY]",
            identity,
            "[GOAL]",
            (
                "Continuously search LinkedIn for open roles matching the user's preferences, "
                "apply to each qualifying role that is not already in the applied jobs list, "
                "and preserve durable state across context resets."
            ),
            "[INPUT DESCRIPTION]",
            (
                "You will receive the following context: job preferences, user profile, the full applied jobs log, "
                f"and the most recent {self._config.action_log_window} semantic actions. "
                f"Begin navigation from {self._config.linkedin_start_url}."
            ),
            "[TOOLS]",
            "\n".join(tool_lines),
            "[BEHAVIORAL RULES]",
            "\n".join(behavioral_rules),
        ]
        return "\n\n".join(section for section in sections if section)

    def load_parameter_sections(self) -> Sequence[AgentParameterSection]:
        recent_actions = self._memory_store.read_recent_actions()
        recent_actions_text = "\n".join(json.dumps(entry.as_dict(), sort_keys=True) for entry in recent_actions)
        return (
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
        )

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


def _unavailable_browser_handler(tool_name: str):
    def handler(arguments: dict[str, Any]) -> dict[str, Any]:
        message = f"Browser tool '{tool_name}' requires a runtime handler."
        raise RuntimeError(message)

    return handler


def _merge_tools(*tool_groups: Iterable[RegisteredTool]) -> tuple[RegisteredTool, ...]:
    ordered_keys: list[str] = []
    merged: dict[str, RegisteredTool] = {}
    for tool_group in tool_groups:
        for tool in tool_group:
            if tool.key not in merged:
                ordered_keys.append(tool.key)
            merged[tool.key] = tool
    return tuple(merged[key] for key in ordered_keys)


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


def _ensure_text_file(path: Path, default_content: str) -> None:
    if path.exists():
        return
    path.write_text(default_content, encoding="utf-8")


def _sanitize_label(label: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", label).strip("-")
    return cleaned or "screenshot"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _timestamp_for_filename() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


__all__ = [
    "ActionLogEntry",
    "JobApplicationRecord",
    "LinkedInAgentConfig",
    "LinkedInJobApplierAgent",
    "LinkedInMemoryStore",
    "ScreenshotPersistor",
    "build_linkedin_browser_tool_definitions",
    "create_linkedin_browser_stub_tools",
]
