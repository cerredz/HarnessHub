"""Knowt TikTok content creation agent harness."""

from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING, Any, Sequence

from harnessiq.agents.base import BaseAgent
from harnessiq.shared.agents import (
    DEFAULT_AGENT_MAX_TOKENS,
    DEFAULT_AGENT_RESET_THRESHOLD,
    AgentModel,
    AgentParameterSection,
    AgentRuntimeConfig,
)
from harnessiq.shared.knowt import (
    KnowtAgentConfig,
    KnowtMemoryStore,
    MASTER_PROMPT_FILENAME,
    PROMPTS_DIRNAME,
)
from harnessiq.shared.tools import RegisteredTool
from harnessiq.tools.knowt import create_knowt_tools
from harnessiq.tools.reasoning import create_injectable_reasoning_tools
from harnessiq.tools.registry import ToolRegistry

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
    ) -> None:
        # Store all params needed by build_instance_payload() before calling super().__init__().
        initial_config = config or KnowtAgentConfig(
            memory_path=Path(memory_path),
            max_tokens=max_tokens,
            reset_threshold=reset_threshold,
        )
        self._config = initial_config
        self._memory_store = KnowtMemoryStore(memory_path=self._config.memory_path)
        self._memory_store.prepare()

        resolved_tools: tuple[RegisteredTool, ...] = tuple(tools) if tools is not None else (
            *create_injectable_reasoning_tools(),
            *create_knowt_tools(
                memory_store=self._memory_store,
                creatify_client=creatify_client,
                creatify_credentials=creatify_credentials,
            ),
        )
        tool_registry = ToolRegistry(resolved_tools)
        runtime_config = AgentRuntimeConfig(
            max_tokens=self._config.max_tokens,
            reset_threshold=self._config.reset_threshold,
        )
        super().__init__(
            name="knowt_content_creator",
            model=model,
            tool_executor=tool_registry,
            runtime_config=runtime_config,
            memory_path=self._config.memory_path,
            repo_root=_find_repo_root(Path(self._config.memory_path)),
        )
        resolved_memory_path = self.memory_path
        self._config = KnowtAgentConfig(
            memory_path=resolved_memory_path,
            max_tokens=initial_config.max_tokens,
            reset_threshold=initial_config.reset_threshold,
        )
        self._memory_store = KnowtMemoryStore(memory_path=resolved_memory_path)
        self._memory_store.prepare()

    def build_instance_payload(self) -> dict[str, Any]:
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

    def prepare(self) -> None:
        self._memory_store.prepare()

    def build_system_prompt(self) -> str:
        """Load and return the master prompt from the prompts directory."""
        if not _MASTER_PROMPT_PATH.exists():
            raise FileNotFoundError(
                f"Knowt master prompt not found at '{_MASTER_PROMPT_PATH}'. "
                "Ensure harnessiq/agents/knowt/prompts/master_prompt.md exists."
            )
        return _MASTER_PROMPT_PATH.read_text(encoding="utf-8")

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


__all__ = ["KnowtAgent"]


def _build_knowt_instance_payload(
    *,
    memory_path: Path,
    max_tokens: int,
    reset_threshold: float,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "memory_path": str(memory_path),
        "runtime": {
            "max_tokens": max_tokens,
            "reset_threshold": reset_threshold,
        },
    }
    store = KnowtMemoryStore(memory_path=memory_path)
    payload["files"] = {
        "current_avatar_description": _read_optional_text(store.current_avatar_description_path),
        "current_script": _read_optional_text(store.current_script_path),
    }
    return payload


def _read_optional_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _find_repo_root(path: Path) -> Path:
    resolved = path.resolve()
    for candidate in (resolved, *resolved.parents):
        if (candidate / ".git").exists():
            return candidate
    if resolved.parent.name == "knowt" and resolved.parent.parent.name == "memory":
        return resolved.parent.parent.parent
    return Path.cwd()
