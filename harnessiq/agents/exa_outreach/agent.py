"""ExaOutreach agent harness for prospect discovery and optional email outreach."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from harnessiq.agents.base import BaseAgent
from harnessiq.shared.agents import (
    DEFAULT_AGENT_MAX_TOKENS,
    DEFAULT_AGENT_RESET_THRESHOLD,
    AgentModel,
    AgentParameterSection,
    AgentRuntimeConfig,
    merge_agent_runtime_config,
    json_parameter_section,
)
from harnessiq.shared.exa_outreach import (
    DEFAULT_AGENT_IDENTITY,
    DEFAULT_SEARCH_QUERY,
    EmailSentRecord,
    EmailTemplate,
    ExaOutreachAgentConfig,
    ExaOutreachMemoryStore,
    FileSystemStorageBackend,
    LEGACY_DEFAULT_AGENT_IDENTITIES,
    LeadRecord,
    StorageBackend,
)
from harnessiq.shared.tools import (
    EXA_OUTREACH_CHECK_CONTACTED,
    EXA_OUTREACH_GET_TEMPLATE,
    EXA_OUTREACH_LIST_TEMPLATES,
    EXA_OUTREACH_LOG_EMAIL_SENT,
    EXA_OUTREACH_LOG_LEAD,
    RegisteredTool,
    ToolDefinition,
)
from harnessiq.tools.registry import create_tool_registry

_PROMPTS_DIR = Path(__file__).parent / "prompts"
_MASTER_PROMPT_PATH = _PROMPTS_DIR / "master_prompt.md"
_DEFAULT_MEMORY_PATH = Path(__file__).parent / "memory"


class ExaOutreachAgent(BaseAgent):
    """Concrete agent harness for Exa-driven prospect discovery and optional outreach."""

    def __init__(
        self,
        *,
        model: AgentModel,
        email_data: Iterable[EmailTemplate | dict[str, Any]] | None = None,
        search_query: str = DEFAULT_SEARCH_QUERY,
        search_only: bool = False,
        memory_path: str | Path | None = None,
        storage_backend: StorageBackend | None = None,
        max_tokens: int = DEFAULT_AGENT_MAX_TOKENS,
        reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD,
        exa_credentials: Any | None = None,
        exa_client: Any | None = None,
        resend_credentials: Any | None = None,
        resend_client: Any | None = None,
        allowed_resend_operations: tuple[str, ...] | None = None,
        allowed_exa_operations: tuple[str, ...] | None = None,
        tools: Sequence[RegisteredTool] | None = None,
        runtime_config: AgentRuntimeConfig | None = None,
    ) -> None:
        # Store all params needed by build_instance_payload() before calling super().__init__().
        self._candidate_memory_path = Path(memory_path) if memory_path is not None else None
        resolved_templates = _coerce_email_data(email_data)
        if not search_only and not resolved_templates:
            raise ValueError(
                "ExaOutreachAgent requires at least one email template unless search_only is True."
            )
        self._payload_email_data = resolved_templates
        self._payload_search_query = search_query
        self._payload_max_tokens = max_tokens
        self._payload_reset_threshold = reset_threshold
        self._payload_allowed_resend_operations = allowed_resend_operations
        self._payload_allowed_exa_operations = allowed_exa_operations

        # Current run ID - assigned in prepare() before the loop starts.
        self._current_run_id: str | None = None
        self._search_only = search_only

        tool_registry = create_tool_registry(
            _create_exa_tools(
                credentials=exa_credentials,
                client=exa_client,
                allowed_operations=allowed_exa_operations
                or ("search", "get_contents", "search_and_contents"),
            ),
            _create_resend_tools(
                credentials=resend_credentials if not search_only else None,
                client=resend_client if not search_only else None,
                allowed_operations=allowed_resend_operations,
            ),
            self._build_internal_tools(),
            tuple(tools or ()),
        )
        super().__init__(
            name="exa_outreach",
            model=model,
            tool_executor=tool_registry,
            runtime_config=merge_agent_runtime_config(
                runtime_config,
                max_tokens=max_tokens,
                reset_threshold=reset_threshold,
            ),
            memory_path=self._candidate_memory_path,
            repo_root=_find_repo_root(self._candidate_memory_path),
        )
        resolved_memory_path = self.memory_path
        self._memory_store = ExaOutreachMemoryStore(memory_path=resolved_memory_path)
        resolved_backend = storage_backend or FileSystemStorageBackend(resolved_memory_path)
        self._config = ExaOutreachAgentConfig(
            email_data=resolved_templates,
            search_query=search_query,
            search_only=search_only,
            memory_path=resolved_memory_path,
            storage_backend=resolved_backend,
            max_tokens=max_tokens,
            reset_threshold=reset_threshold,
            allowed_resend_operations=allowed_resend_operations,
            allowed_exa_operations=allowed_exa_operations,
        )

    @property
    def config(self) -> ExaOutreachAgentConfig:
        return self._config

    @property
    def memory_store(self) -> ExaOutreachMemoryStore:
        return self._memory_store

    # ------------------------------------------------------------------
    # BaseAgent overrides
    # ------------------------------------------------------------------

    def build_instance_payload(self) -> dict[str, Any]:
        return _build_exa_outreach_instance_payload(
            memory_path=self._candidate_memory_path,
            email_data=self._payload_email_data,
            search_query=self._payload_search_query,
            max_tokens=self._payload_max_tokens,
            reset_threshold=self._payload_reset_threshold,
            allowed_resend_operations=self._payload_allowed_resend_operations,
            allowed_exa_operations=self._payload_allowed_exa_operations,
        )

    def prepare(self) -> None:
        """Initialise memory directory and start a new run in the storage backend."""
        self._memory_store.prepare()
        run_id = self._memory_store.next_run_id()
        self._current_run_id = run_id
        self._config.storage_backend.start_run(
            run_id,
            {
                "query": self._config.search_query,
                "search_only": self._config.search_only,
            },
        )

    def build_system_prompt(self) -> str:
        """Load and return the master prompt from the prompts directory."""
        if not _MASTER_PROMPT_PATH.exists():
            raise FileNotFoundError(
                f"ExaOutreach master prompt not found at '{_MASTER_PROMPT_PATH}'. "
                "Ensure harnessiq/agents/exa_outreach/prompts/master_prompt.md exists."
            )
        identity = (
            self._memory_store.read_agent_identity()
            if self._memory_store.agent_identity_path.exists()
            else DEFAULT_AGENT_IDENTITY
        )
        prompt = _MASTER_PROMPT_PATH.read_text(encoding="utf-8")
        if identity and identity not in {DEFAULT_AGENT_IDENTITY, *LEGACY_DEFAULT_AGENT_IDENTITIES}:
            prompt = prompt.replace(
                "[IDENTITY]\nYou are ExaOutreachAgent.",
                f"[IDENTITY]\n{identity}\n\n(You are ExaOutreachAgent.)",
            )
        if self._config.search_only:
            prompt = (
                f"{prompt}\n\n[MODE OVERRIDE]\n"
                "Search-only mode is enabled. You must only discover prospects, deduplicate them "
                "against prior lead logs, and call `exa_outreach.log_lead` for each new lead. Do "
                "not attempt template selection, email drafting, or email sending."
            )
        additional_prompt = (
            self._memory_store.read_additional_prompt()
            if self._memory_store.additional_prompt_path.exists()
            else ""
        )
        if additional_prompt:
            prompt = f"{prompt}\n\n[ADDITIONAL INSTRUCTIONS]\n{additional_prompt}"
        return prompt

    def load_parameter_sections(self) -> Sequence[AgentParameterSection]:
        """Return durable parameter sections injected at the front of the context window."""
        query_config = self._memory_store.read_query_config() if self._memory_store.query_config_path.exists() else {}
        query_metadata = dict(query_config)
        query_metadata["search_only"] = self._config.search_only
        query_content = self._config.search_query
        if query_metadata:
            query_content = f"{query_content}\n\n{json.dumps(query_metadata, indent=2, sort_keys=True)}"
        run_content = self._current_run_id or "(run not started)"

        sections: list[AgentParameterSection] = []
        if not self._config.search_only:
            sections.append(json_parameter_section("Email Templates", [template.as_dict() for template in self._config.email_data]))
        sections.extend(
            (
                AgentParameterSection(title="Search Query", content=query_content),
                AgentParameterSection(title="Current Run", content=run_content),
            )
        )
        return tuple(sections)

    def build_ledger_outputs(self) -> dict[str, Any]:
        run_log = self._read_current_run_log()
        if run_log is None:
            return {}
        return {
            "search_query": run_log.query,
            "leads_found": [record.as_dict() for record in run_log.leads_found],
            "emails_sent": [record.as_dict() for record in run_log.emails_sent],
        }

    def build_ledger_tags(self) -> list[str]:
        tags = ["outreach", "sales"]
        if self._config.search_only:
            tags.append("lead_discovery")
        else:
            tags.append("email")
        return tags

    def build_ledger_metadata(self) -> dict[str, Any]:
        return {
            "current_run_id": self._current_run_id,
            "search_only": self._config.search_only,
            "template_count": len(self._config.email_data),
        }

    def _build_internal_tools(self) -> tuple[RegisteredTool, ...]:
        tools: list[RegisteredTool] = [
            RegisteredTool(
                definition=_tool_definition(
                    key=EXA_OUTREACH_CHECK_CONTACTED,
                    name="check_contacted",
                    description=(
                        "Check whether a prospect URL has already been logged in any prior run. "
                        "Returns {already_contacted: bool}. Always call this before processing a prospect."
                    ),
                    properties={
                        "url": {
                            "type": "string",
                            "description": "The Exa profile or webpage URL of the prospect.",
                        }
                    },
                    required=("url",),
                ),
                handler=self._handle_check_contacted,
            ),
            RegisteredTool(
                definition=_tool_definition(
                    key=EXA_OUTREACH_LOG_LEAD,
                    name="log_lead",
                    description=(
                        "Log a newly discovered prospect to the current run file. "
                        "Call this for every new prospect found. This is required; never skip it."
                    ),
                    properties={
                        "url": {
                            "type": "string",
                            "description": "The Exa profile or webpage URL of the prospect.",
                        },
                        "name": {
                            "type": "string",
                            "description": "The prospect's full name.",
                        },
                        "email_address": {
                            "type": "string",
                            "description": "The prospect's email address if found in their profile.",
                        },
                        "notes": {
                            "type": "string",
                            "description": "Optional notes about the prospect or why they were skipped.",
                        },
                    },
                    required=("url", "name"),
                ),
                handler=self._handle_log_lead,
            ),
        ]
        if self._search_only:
            return tuple(tools)

        tools[0:0] = [
            RegisteredTool(
                definition=_tool_definition(
                    key=EXA_OUTREACH_LIST_TEMPLATES,
                    name="list_templates",
                    description=(
                        "List all available email templates with their id, title, description, icp, "
                        "and pain_points. Call this to survey what templates are available before "
                        "selecting one for a prospect."
                    ),
                    properties={},
                ),
                handler=self._handle_list_templates,
            ),
            RegisteredTool(
                definition=_tool_definition(
                    key=EXA_OUTREACH_GET_TEMPLATE,
                    name="get_template",
                    description=(
                        "Retrieve the full email template by its id, including actual_email, subject, "
                        "links, and all metadata. Call this immediately before composing and sending "
                        "an email to a specific prospect."
                    ),
                    properties={
                        "template_id": {
                            "type": "string",
                            "description": "The id of the template to retrieve.",
                        }
                    },
                    required=("template_id",),
                ),
                handler=self._handle_get_template,
            ),
        ]
        tools.append(
            RegisteredTool(
                definition=_tool_definition(
                    key=EXA_OUTREACH_LOG_EMAIL_SENT,
                    name="log_email_sent",
                    description=(
                        "Log a successfully sent email to the current run file. Call this immediately "
                        "after every successful resend.request send_email call. This is required; never skip it."
                    ),
                    properties={
                        "to_email": {
                            "type": "string",
                            "description": "The recipient email address.",
                        },
                        "to_name": {
                            "type": "string",
                            "description": "The recipient's full name.",
                        },
                        "subject": {
                            "type": "string",
                            "description": "The subject line used (after any personalisation).",
                        },
                        "template_id": {
                            "type": "string",
                            "description": "The id of the template used.",
                        },
                        "notes": {
                            "type": "string",
                            "description": "Optional notes about the send (e.g. personalisation applied).",
                        },
                    },
                    required=("to_email", "to_name", "subject", "template_id"),
                ),
                handler=self._handle_log_email_sent,
            )
        )
        return tuple(tools)

    def _handle_list_templates(self, arguments: dict[str, Any]) -> dict[str, Any]:
        templates = [
            {
                "id": template.id,
                "title": template.title,
                "description": template.description,
                "icp": template.icp,
                "pain_points": list(template.pain_points),
            }
            for template in self._config.email_data
        ]
        return {"templates": templates, "count": len(templates)}

    def _handle_get_template(self, arguments: dict[str, Any]) -> dict[str, Any]:
        template_id = str(arguments["template_id"])
        template_index = {template.id: template for template in self._config.email_data}
        if template_id not in template_index:
            available = ", ".join(sorted(template_index))
            raise ValueError(
                f"Template '{template_id}' not found. Available templates: {available}."
            )
        return template_index[template_id].as_dict()

    def _handle_check_contacted(self, arguments: dict[str, Any]) -> dict[str, Any]:
        url = str(arguments["url"])
        already_contacted = self._config.storage_backend.has_seen("url", url, event_type="lead")
        return {"url": url, "already_contacted": already_contacted}

    def _handle_log_lead(self, arguments: dict[str, Any]) -> dict[str, Any]:
        run_id = self._current_run_id
        if run_id is None:
            raise RuntimeError("Cannot log a lead before prepare() has been called.")
        lead = LeadRecord(
            url=str(arguments["url"]),
            name=str(arguments["name"]),
            found_at=_utcnow(),
            email_address=str(arguments["email_address"]) if arguments.get("email_address") else None,
            notes=str(arguments["notes"]) if arguments.get("notes") else None,
        )
        self._config.storage_backend.log_event(run_id, "lead", lead.as_dict())
        return lead.as_dict()

    def _handle_log_email_sent(self, arguments: dict[str, Any]) -> dict[str, Any]:
        run_id = self._current_run_id
        if run_id is None:
            raise RuntimeError("Cannot log an email before prepare() has been called.")
        record = EmailSentRecord(
            to_email=str(arguments["to_email"]),
            to_name=str(arguments["to_name"]),
            subject=str(arguments["subject"]),
            template_id=str(arguments["template_id"]),
            sent_at=_utcnow(),
            notes=str(arguments["notes"]) if arguments.get("notes") else None,
        )
        self._config.storage_backend.log_event(run_id, "email_sent", record.as_dict())
        return record.as_dict()

    def _read_current_run_log(self):
        run_id = self._current_run_id
        if run_id is None:
            return None
        self._config.storage_backend.finish_run(run_id, _utcnow())
        try:
            return self._memory_store.read_run(run_id)
        except FileNotFoundError:
            return None


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


def _coerce_email_data(
    email_data: Iterable[EmailTemplate | dict[str, Any]] | None,
) -> tuple[EmailTemplate, ...]:
    if email_data is None:
        return ()
    templates: list[EmailTemplate] = []
    for item in email_data:
        if isinstance(item, EmailTemplate):
            templates.append(item)
            continue
        if isinstance(item, dict):
            templates.append(EmailTemplate.from_dict(item))
            continue
        raise TypeError(f"email_data items must be EmailTemplate or dict, got {type(item)!r}.")
    return tuple(templates)


def _build_exa_outreach_instance_payload(
    *,
    memory_path: Path | None,
    email_data: tuple[EmailTemplate, ...],
    search_query: str,
    max_tokens: int,
    reset_threshold: float,
    allowed_resend_operations: tuple[str, ...] | None,
    allowed_exa_operations: tuple[str, ...] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "allowed_exa_operations": list(allowed_exa_operations) if allowed_exa_operations is not None else None,
        "allowed_resend_operations": list(allowed_resend_operations) if allowed_resend_operations is not None else None,
        "email_data": [item.as_dict() for item in email_data],
        "max_tokens": max_tokens,
        "reset_threshold": reset_threshold,
        "search_query": search_query,
    }
    if memory_path is not None:
        payload["memory_path"] = str(memory_path)
    if memory_path is None or not memory_path.exists():
        return payload

    store = ExaOutreachMemoryStore(memory_path=memory_path)
    payload["agent_identity"] = _read_optional_text(store.agent_identity_path)
    payload["additional_prompt"] = _read_optional_text(store.additional_prompt_path)
    query_config = store.read_query_config() if store.query_config_path.exists() else {}
    if query_config:
        payload["query_config"] = query_config
    return payload


def _create_exa_tools(
    *,
    credentials: Any | None,
    client: Any | None,
    allowed_operations: Sequence[str] | None,
) -> tuple[RegisteredTool, ...]:
    from harnessiq.providers.exa.operations import create_exa_tools

    return create_exa_tools(credentials=credentials, client=client, allowed_operations=allowed_operations)


def _create_resend_tools(
    *,
    credentials: Any | None,
    client: Any | None,
    allowed_operations: tuple[str, ...] | None,
) -> tuple[RegisteredTool, ...]:
    if credentials is None and client is None:
        return ()
    from harnessiq.tools.resend import create_resend_tools

    return create_resend_tools(credentials=credentials, client=client, allowed_operations=allowed_operations)


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
    if resolved.parent.name == "outreach" and resolved.parent.parent.name == "memory":
        return resolved.parent.parent.parent
    return Path.cwd()


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


__all__ = [
    "ExaOutreachAgent",
    "ExaOutreachAgentConfig",
]
