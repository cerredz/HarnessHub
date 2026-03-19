"""LinkedIn-specific agent harness and durable memory helpers."""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence
from urllib import request

from harnessiq.agents.base import BaseAgent
from harnessiq.shared.agents import (
    DEFAULT_AGENT_MAX_TOKENS,
    DEFAULT_AGENT_RESET_THRESHOLD,
    AgentModel,
    AgentParameterSection,
    AgentPauseSignal,
    AgentRuntimeConfig,
    merge_agent_runtime_config,
)
from harnessiq.shared.linkedin import (
    ACTION_LOG_FILENAME,
    AGENT_IDENTITY_FILENAME,
    APPLIED_JOBS_FILENAME,
    ADDITIONAL_PROMPT_FILENAME,
    DEFAULT_AGENT_IDENTITY,
    DEFAULT_JOB_PREFERENCES,
    DEFAULT_LINKEDIN_ACTION_LOG_WINDOW,
    DEFAULT_LINKEDIN_NOTIFY_ON_PAUSE,
    DEFAULT_LINKEDIN_START_URL,
    DEFAULT_USER_PROFILE,
    CUSTOM_PARAMETERS_FILENAME,
    JOB_PREFERENCES_FILENAME,
    MANAGED_FILES_DIRNAME,
    MANAGED_FILES_INDEX_FILENAME,
    SCREENSHOT_DIRNAME,
    USER_PROFILE_FILENAME,
    ActionLogEntry,
    JobApplicationRecord,
    LinkedInAgentConfig,
    LinkedInManagedFile,
    RUNTIME_PARAMETERS_FILENAME,
    ScreenshotPersistor,
)
from harnessiq.shared.tools import RegisteredTool, ToolDefinition
from harnessiq.tools.registry import ToolRegistry

# Default memory location: the `memory/` folder inside this agent's subdirectory.
# Users can override this by passing an explicit `memory_path` argument.
_DEFAULT_MEMORY_PATH = Path(__file__).parent / "memory"

# System prompt template loaded from disk so it can be updated without touching Python source.
_MASTER_PROMPT_PATH = Path(__file__).parent / "prompts" / "master_prompt.md"


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
    def runtime_parameters_path(self) -> Path:
        return self.memory_path / RUNTIME_PARAMETERS_FILENAME

    @property
    def custom_parameters_path(self) -> Path:
        return self.memory_path / CUSTOM_PARAMETERS_FILENAME

    @property
    def additional_prompt_path(self) -> Path:
        return self.memory_path / ADDITIONAL_PROMPT_FILENAME

    @property
    def applied_jobs_path(self) -> Path:
        return self.memory_path / APPLIED_JOBS_FILENAME

    @property
    def action_log_path(self) -> Path:
        return self.memory_path / ACTION_LOG_FILENAME

    @property
    def screenshot_dir(self) -> Path:
        return self.memory_path / SCREENSHOT_DIRNAME

    @property
    def managed_files_dir(self) -> Path:
        return self.memory_path / MANAGED_FILES_DIRNAME

    @property
    def managed_files_index_path(self) -> Path:
        return self.memory_path / MANAGED_FILES_INDEX_FILENAME

    def prepare(self) -> None:
        self.memory_path.mkdir(parents=True, exist_ok=True)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self.managed_files_dir.mkdir(parents=True, exist_ok=True)
        _ensure_text_file(self.job_preferences_path, DEFAULT_JOB_PREFERENCES)
        _ensure_text_file(self.user_profile_path, DEFAULT_USER_PROFILE)
        _ensure_text_file(self.agent_identity_path, DEFAULT_AGENT_IDENTITY)
        _ensure_json_file(self.runtime_parameters_path, {})
        _ensure_json_file(self.custom_parameters_path, {})
        _ensure_text_file(self.additional_prompt_path, "")
        _ensure_json_file(self.managed_files_index_path, [])
        _ensure_text_file(self.applied_jobs_path, "")
        _ensure_text_file(self.action_log_path, "")

    def read_job_preferences(self) -> str:
        return self.job_preferences_path.read_text(encoding="utf-8").strip()

    def write_job_preferences(self, content: str) -> Path:
        return self._write_text(self.job_preferences_path, content)

    def read_user_profile(self) -> str:
        return self.user_profile_path.read_text(encoding="utf-8").strip()

    def write_user_profile(self, content: str) -> Path:
        return self._write_text(self.user_profile_path, content)

    def read_agent_identity(self) -> str:
        return self.agent_identity_path.read_text(encoding="utf-8").strip()

    def write_agent_identity(self, content: str) -> Path:
        return self._write_text(self.agent_identity_path, content)

    def read_runtime_parameters(self) -> dict[str, Any]:
        return self._read_json_file(self.runtime_parameters_path, expected_type=dict)

    def write_runtime_parameters(self, parameters: Mapping[str, Any]) -> Path:
        return self._write_json_file(self.runtime_parameters_path, dict(parameters))

    def read_custom_parameters(self) -> dict[str, Any]:
        return self._read_json_file(self.custom_parameters_path, expected_type=dict)

    def write_custom_parameters(self, parameters: Mapping[str, Any]) -> Path:
        return self._write_json_file(self.custom_parameters_path, dict(parameters))

    def read_additional_prompt(self) -> str:
        return self.additional_prompt_path.read_text(encoding="utf-8").strip()

    def write_additional_prompt(self, content: str) -> Path:
        return self._write_text(self.additional_prompt_path, content)

    def read_applied_jobs_raw(self) -> str:
        return self.applied_jobs_path.read_text(encoding="utf-8").strip()

    def read_managed_files(self) -> list[LinkedInManagedFile]:
        payload = self._read_json_file(self.managed_files_index_path, expected_type=list)
        return [LinkedInManagedFile.from_dict(entry) for entry in payload]

    def ingest_managed_file(self, source_path: str | Path, *, target_name: str | None = None) -> LinkedInManagedFile:
        self.prepare()
        source = Path(source_path).expanduser().resolve()
        if not source.exists() or not source.is_file():
            message = f"Managed file source '{source}' does not exist or is not a file."
            raise FileNotFoundError(message)
        target_filename = _sanitize_filename(target_name or source.name)
        target_path = self.managed_files_dir / target_filename
        shutil.copy2(source, target_path)
        record = LinkedInManagedFile(
            name=target_filename,
            relative_path=_relative_path_text(target_path, self.memory_path),
            source_path=str(source),
            created_at=_utcnow(),
            kind="copied_file",
        )
        self._upsert_managed_file(record)
        return record

    def write_managed_text_file(
        self,
        *,
        name: str,
        content: str,
        source_path: str | None = None,
    ) -> LinkedInManagedFile:
        self.prepare()
        target_filename = _sanitize_filename(name)
        target_path = self.managed_files_dir / target_filename
        target_path.write_text(content, encoding="utf-8")
        record = LinkedInManagedFile(
            name=target_filename,
            relative_path=_relative_path_text(target_path, self.memory_path),
            source_path=source_path,
            created_at=_utcnow(),
            kind="inline_text",
        )
        self._upsert_managed_file(record)
        return record

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

    def _write_text(self, path: Path, content: str) -> Path:
        rendered = content if not content or content.endswith("\n") else f"{content}\n"
        path.write_text(rendered, encoding="utf-8")
        return path

    def _write_json_file(self, path: Path, payload: Any) -> Path:
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def _read_json_file(self, path: Path, *, expected_type: type[dict] | type[list]) -> Any:
        if not path.exists():
            return expected_type()
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            return expected_type()
        payload = json.loads(raw)
        if not isinstance(payload, expected_type):
            message = f"Expected JSON {expected_type.__name__} in '{path.name}'."
            raise ValueError(message)
        return payload

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

    def _upsert_managed_file(self, record: LinkedInManagedFile) -> None:
        managed_files = self.read_managed_files()
        indexed = {item.relative_path: item for item in managed_files}
        indexed[record.relative_path] = record
        ordered = [indexed[key].as_dict() for key in sorted(indexed)]
        self._write_json_file(self.managed_files_index_path, ordered)


class LinkedInJobApplierAgent(BaseAgent):
    """Concrete agent harness matching the LinkedIn job application specification."""

    def __init__(
        self,
        *,
        model: AgentModel,
        memory_path: str | Path | None = None,
        browser_tools: Iterable[RegisteredTool] = (),
        screenshot_persistor: ScreenshotPersistor | None = None,
        max_tokens: int = DEFAULT_AGENT_MAX_TOKENS,
        reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD,
        action_log_window: int = DEFAULT_LINKEDIN_ACTION_LOG_WINDOW,
        linkedin_start_url: str = DEFAULT_LINKEDIN_START_URL,
        notify_on_pause: bool = DEFAULT_LINKEDIN_NOTIFY_ON_PAUSE,
        pause_webhook: str | None = None,
        runtime_config: AgentRuntimeConfig | None = None,
    ) -> None:
        self._config = LinkedInAgentConfig(
            memory_path=_resolve_memory_path(memory_path),
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
        super().__init__(
            name="linkedin_job_applier",
            model=model,
            tool_executor=tool_registry,
            runtime_config=merge_agent_runtime_config(
                runtime_config,
                max_tokens=self._config.max_tokens,
                reset_threshold=self._config.reset_threshold,
            ),
            memory_path=self._config.memory_path,
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
            sections.append(AgentParameterSection(title="Runtime Parameters", content=_json_block(runtime_parameters)))
        custom_parameters = self._memory_store.read_custom_parameters()
        if custom_parameters:
            sections.append(AgentParameterSection(title="Custom Parameters", content=_json_block(custom_parameters)))
        additional_prompt = self._memory_store.read_additional_prompt()
        if additional_prompt:
            sections.append(AgentParameterSection(title="Additional Prompt Data", content=additional_prompt))
        managed_files = [entry.as_dict() for entry in self._memory_store.read_managed_files()]
        if managed_files:
            sections.append(AgentParameterSection(title="Managed Files", content=_json_block(managed_files)))
        return tuple(sections)

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


def _ensure_json_file(path: Path, default_payload: Any) -> None:
    if path.exists():
        return
    path.write_text(json.dumps(default_payload, indent=2, sort_keys=True), encoding="utf-8")


def _sanitize_label(label: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", label).strip("-")
    return cleaned or "screenshot"


def _sanitize_filename(filename: str) -> str:
    candidate = Path(filename).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", candidate).strip("-")
    if not cleaned:
        raise ValueError("Managed filenames must contain at least one alphanumeric character.")
    return cleaned


def _json_block(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


def _relative_path_text(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


SUPPORTED_LINKEDIN_RUNTIME_PARAMETERS = (
    "max_tokens",
    "reset_threshold",
    "action_log_window",
    "linkedin_start_url",
    "notify_on_pause",
    "pause_webhook",
)


def normalize_linkedin_runtime_parameters(parameters: Mapping[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    coercers: dict[str, Callable[[Any], Any]] = {
        "max_tokens": _coerce_int,
        "reset_threshold": _coerce_float,
        "action_log_window": _coerce_int,
        "linkedin_start_url": _coerce_string,
        "notify_on_pause": _coerce_bool,
        "pause_webhook": _coerce_optional_string,
    }
    for key, value in parameters.items():
        if key not in coercers:
            raise ValueError(f"Unsupported LinkedIn runtime parameter '{key}'.")
        normalized[key] = coercers[key](value)
    return normalized


def _coerce_int(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("Boolean values are not valid integer runtime parameters.")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        return int(value)
    raise ValueError("Runtime parameter must be an integer.")


def _coerce_float(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("Boolean values are not valid float runtime parameters.")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        return float(value)
    raise ValueError("Runtime parameter must be a float.")


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    raise ValueError("Runtime parameter must be a boolean.")


def _coerce_string(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Runtime parameter must be a non-empty string.")
    return value


def _coerce_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    raise ValueError("Runtime parameter must be a string or null.")


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
