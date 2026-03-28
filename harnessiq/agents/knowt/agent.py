"""Knowt TikTok content creation agent harness."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from harnessiq.agents.base import BaseAgent
from harnessiq.agents.helpers import find_repo_root as _find_repo_root
from harnessiq.agents.helpers import resolve_memory_path as _resolve_memory_path
from harnessiq.agents.knowt.helpers import build_knowt_instance_payload as _build_knowt_instance_payload
from harnessiq.agents.sdk_helpers import (
    load_master_prompt_text,
    load_persisted_profile,
    merge_profile_parameters,
    resolve_profile_memory_path,
)
from harnessiq.config import HarnessProfile
from harnessiq.shared.agents import (
    DEFAULT_AGENT_MAX_TOKENS,
    DEFAULT_AGENT_RESET_THRESHOLD,
    AgentModel,
    AgentParameterSection,
    AgentRuntimeConfig,
    merge_agent_runtime_config,
)
from harnessiq.shared.dtos import KnowtAgentInstancePayload
from harnessiq.shared.exceptions import ResourceNotFoundError
from harnessiq.shared.knowt import (
    KnowtAgentConfig,
    KNOWT_HARNESS_MANIFEST,
    KnowtMemoryStore,
    MASTER_PROMPT_FILENAME,
    PROMPTS_DIRNAME,
)
from harnessiq.shared.tools import RegisteredTool
from harnessiq.tools.knowt import create_knowt_tools
from harnessiq.tools.reasoning import create_injectable_reasoning_tools
from harnessiq.tools.registry import create_tool_registry

if TYPE_CHECKING:
    from harnessiq.providers.creatify.client import CreatifyClient, CreatifyCredentials

_PROMPTS_DIR = Path(__file__).parent / PROMPTS_DIRNAME
_MASTER_PROMPT_PATH = _PROMPTS_DIR / MASTER_PROMPT_FILENAME


class KnowtAgent(BaseAgent):
    """Concrete harness for the Knowt TikTok content creation pipeline.

    The agent follows a deterministic creation sequence — brainstorm →
    create_script → create_avatar_description → create_video — enforced
    by file-backed agent memory. The system prompt is loaded at runtime
    from ``harnessiq/agents/knowt/prompts/master_prompt.md`` so it can
    be updated without touching Python source.
    """

    master_prompt_path = _MASTER_PROMPT_PATH

    def __init__(
        self,
        *,
        model: AgentModel,
        memory_path: str | Path,
        creatify_client: "CreatifyClient | None" = None,
        creatify_credentials: "CreatifyCredentials | None" = None,
        max_tokens: int = DEFAULT_AGENT_MAX_TOKENS,
        reset_threshold: float = DEFAULT_AGENT_RESET_THRESHOLD,
        config: KnowtAgentConfig | None = None,
        tools: "Sequence[RegisteredTool] | None" = None,
        runtime_config: AgentRuntimeConfig | None = None,
        instance_name: str | None = None,
        master_prompt_override: str | Path | None = None,
    ) -> None:
        # Store all params needed by build_instance_payload() before calling super().__init__().
        initial_config = config or KnowtAgentConfig(
            memory_path=Path(memory_path),
            max_tokens=max_tokens,
            reset_threshold=reset_threshold,
        )
        self._master_prompt_override = master_prompt_override
        self._config = initial_config
        self._memory_store = KnowtMemoryStore(memory_path=self._config.memory_path)
        self._memory_store.prepare()

        default_tools: tuple[RegisteredTool, ...] = (
            *create_injectable_reasoning_tools(),
            *create_knowt_tools(
                memory_store=self._memory_store,
                creatify_client=creatify_client,
                creatify_credentials=creatify_credentials,
            ),
        )
        tool_registry = create_tool_registry(default_tools, tools or ())
        super().__init__(
            name="knowt_content_creator",
            model=model,
            tool_executor=tool_registry,
            runtime_config=merge_agent_runtime_config(
                runtime_config,
                max_tokens=self._config.max_tokens,
                reset_threshold=self._config.reset_threshold,
            ),
            memory_path=self._config.memory_path,
            repo_root=_find_repo_root(Path(self._config.memory_path)),
            instance_name=instance_name,
        )
        resolved_memory_path = self.memory_path
        self._config = KnowtAgentConfig(
            memory_path=resolved_memory_path,
            max_tokens=initial_config.max_tokens,
            reset_threshold=initial_config.reset_threshold,
        )
        self._memory_store = KnowtMemoryStore(memory_path=resolved_memory_path)
        self._memory_store.prepare()

    def build_instance_payload(self) -> KnowtAgentInstancePayload:
        return _build_knowt_instance_payload(
            memory_path=Path(self._config.memory_path),
            max_tokens=self._config.max_tokens,
            reset_threshold=self._config.reset_threshold,
        )

    @property
    def config(self) -> KnowtAgentConfig:
        return self._config

    @property
    def memory_store(self) -> KnowtMemoryStore:
        return self._memory_store

    @classmethod
    def from_memory(
        cls,
        *,
        model: AgentModel,
        memory_path: str | Path | None = None,
        creatify_client: "CreatifyClient | None" = None,
        creatify_credentials: "CreatifyCredentials | None" = None,
        runtime_overrides: Mapping[str, Any] | None = None,
        custom_overrides: Mapping[str, Any] | None = None,
        tools: "Sequence[RegisteredTool] | None" = None,
        runtime_config: AgentRuntimeConfig | None = None,
        instance_name: str | None = None,
        master_prompt_override: str | Path | None = None,
    ) -> "KnowtAgent":
        resolved_memory_path = _resolve_memory_path(
            memory_path,
            default_path=Path(KNOWT_HARNESS_MANIFEST.resolved_default_memory_root),
        )
        profile = load_persisted_profile(
            manifest_id=KNOWT_HARNESS_MANIFEST.manifest_id,
            memory_path=resolved_memory_path,
        )
        runtime_parameters, _ = merge_profile_parameters(
            profile=profile,
            runtime_overrides=runtime_overrides,
            custom_overrides=custom_overrides,
        )
        return cls(
            model=model,
            memory_path=resolved_memory_path,
            creatify_client=creatify_client,
            creatify_credentials=creatify_credentials,
            max_tokens=int(runtime_parameters.get("max_tokens", DEFAULT_AGENT_MAX_TOKENS)),
            reset_threshold=float(runtime_parameters.get("reset_threshold", DEFAULT_AGENT_RESET_THRESHOLD)),
            tools=tools,
            runtime_config=runtime_config,
            instance_name=instance_name,
            master_prompt_override=master_prompt_override,
        )

    @classmethod
    def from_profile(
        cls,
        *,
        profile: HarnessProfile,
        model: AgentModel,
        memory_path: str | Path | None = None,
        creatify_client: "CreatifyClient | None" = None,
        creatify_credentials: "CreatifyCredentials | None" = None,
        runtime_config: AgentRuntimeConfig | None = None,
        runtime_overrides: Mapping[str, Any] | None = None,
        custom_overrides: Mapping[str, Any] | None = None,
        tools: "Sequence[RegisteredTool] | None" = None,
        instance_name: str | None = None,
        master_prompt_override: str | Path | None = None,
    ) -> "KnowtAgent":
        resolved_path = resolve_profile_memory_path(
            profile=profile,
            manifest=KNOWT_HARNESS_MANIFEST,
            memory_path=memory_path,
        )
        resolved_runtime, resolved_custom = merge_profile_parameters(
            profile=profile,
            runtime_overrides=runtime_overrides,
            custom_overrides=custom_overrides,
        )
        return cls.from_memory(
            model=model,
            memory_path=resolved_path,
            creatify_client=creatify_client,
            creatify_credentials=creatify_credentials,
            runtime_overrides=resolved_runtime,
            custom_overrides=resolved_custom,
            tools=tools,
            runtime_config=runtime_config,
            instance_name=instance_name or profile.agent_name,
            master_prompt_override=master_prompt_override,
        )

    def prepare(self) -> None:
        self._memory_store.prepare()

    def build_system_prompt(self) -> str:
        """Load and return the master prompt from the prompts directory."""
        return load_master_prompt_text(
            default_path=_MASTER_PROMPT_PATH,
            override=self._master_prompt_override,
            missing_message=(
                f"Knowt master prompt not found at '{_MASTER_PROMPT_PATH}'. "
                "Ensure harnessiq/agents/knowt/prompts/master_prompt.md exists."
            ),
        )

    def load_parameter_sections(self) -> Sequence[AgentParameterSection]:
        """Return current script and avatar description as durable parameter sections."""
        script = self._memory_store.read_script()
        avatar_description = self._memory_store.read_avatar_description()
        return (
            AgentParameterSection(
                title="Current Script",
                content=script if script else "(no script created yet — call create_script first)",
            ),
            AgentParameterSection(
                title="Current Avatar Description",
                content=(
                    avatar_description
                    if avatar_description
                    else "(no avatar description created yet — call create_avatar_description first)"
                ),
            ),
        )

    def build_ledger_outputs(self) -> dict[str, object]:
        return {
            "script": self._memory_store.read_script(),
            "avatar_description": self._memory_store.read_avatar_description(),
            "creation_log": [entry.as_dict() for entry in self._memory_store.read_creation_log()],
        }

    def build_ledger_tags(self) -> list[str]:
        return ["knowt", "content", "video"]


__all__ = ["KnowtAgent"]
