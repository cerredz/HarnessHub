"""Tests for the generic agent runtime."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from harnessiq.agents import (
    AgentModelRequest,
    AgentModelResponse,
    AgentParameterSection,
    AgentPauseSignal,
    AgentRuntimeConfig,
    AgentTranscriptEntry,
    BaseAgent,
    json_parameter_section,
)
from harnessiq.formalization import (
    BaseFormalizationLayer,
    BaseBehaviorLayer,
    BehaviorConstraint,
    InputArtifactLayer,
    InputArtifactSpec,
    LayerRuleRecord,
    OutputArtifactLayer,
    OutputArtifactSpec,
)
from harnessiq.formalization.stages import SimpleStageSpec
from harnessiq.shared.agents import DEFAULT_AGENT_MAX_TOKENS, DEFAULT_AGENT_RESET_THRESHOLD
from harnessiq.shared.tool_selection import ToolSelectionConfig, ToolSelectionResult
from harnessiq.shared.tools import (
    ARTIFACT_WRITE_MARKDOWN,
    CONTEXT_INJECT_ASSISTANT_NOTE,
    CONTEXT_PARAM_INJECT_SECTION,
    CONTROL_MARK_COMPLETE,
    CONTROL_PAUSE_FOR_HUMAN,
    HEAVY_COMPACTION,
    RegisteredTool,
    ToolCall,
    ToolDefinition,
    ToolResult,
)
from harnessiq.tools import create_context_compaction_tools, create_general_purpose_tools
from harnessiq.tools.control import create_control_tools
from harnessiq.tools.registry import ToolRegistry
from harnessiq.utils import JSONLLedgerSink, LedgerEntry, build_agent_instance_dirname, load_ledger_entries

_LANGSMITH_CLIENT_PATCHER = patch("harnessiq.agents.base.agent_helpers.build_langsmith_client", return_value=None)


def setUpModule() -> None:
    _LANGSMITH_CLIENT_PATCHER.start()


def tearDownModule() -> None:
    _LANGSMITH_CLIENT_PATCHER.stop()


class _FakeModel:
    def __init__(self, responses: list[AgentModelResponse]) -> None:
        self._responses = list(responses)
        self.requests: list[AgentModelRequest] = []

    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        self.requests.append(request)
        return self._responses[len(self.requests) - 1]


class _InspectableAgent(BaseAgent):
    def __init__(
        self,
        *,
        model: _FakeModel,
        tool_executor: ToolRegistry,
        parameter_versions: list[str] | None = None,
        progress_step: int | None = None,
        runtime_config: AgentRuntimeConfig | None = None,
        payload: dict | None = None,
        dynamic_tool_selector=None,
        formalization_layers=None,
        behaviors=None,
        stages=None,
        input_artifacts=None,
        output_artifacts=None,
        memory_path: Path | None = None,
        repo_root: str | Path | None = None,
    ) -> None:
        self._parameter_versions = parameter_versions or ["initial"]
        self._parameter_index = 0
        self._payload = payload or {}
        self._progress_step = progress_step
        self._progress_value = 0
        super().__init__(
            name="inspectable_agent",
            model=model,
            tool_executor=tool_executor,
            runtime_config=runtime_config or AgentRuntimeConfig(include_default_output_sink=False),
            dynamic_tool_selector=dynamic_tool_selector,
            formalization_layers=formalization_layers,
            behaviors=behaviors,
            stages=stages,
            input_artifacts=input_artifacts,
            output_artifacts=output_artifacts,
            memory_path=memory_path,
            repo_root=repo_root,
        )

    def build_instance_payload(self) -> dict:
        return self._payload

    def build_system_prompt(self) -> str:
        return "System prompt"

    def load_parameter_sections(self) -> list[AgentParameterSection]:
        index = min(self._parameter_index, len(self._parameter_versions) - 1)
        self._parameter_index += 1
        return [AgentParameterSection(title="State", content=self._parameter_versions[index])]

    def build_ledger_outputs(self) -> dict[str, object]:
        return {"parameter_state": self.parameter_sections[0].content}

    def build_ledger_tags(self) -> list[str]:
        return ["inspectable"]

    def pruning_progress_value(self) -> int:
        if self._progress_step is None:
            return super().pruning_progress_value()
        value = self._progress_value
        self._progress_value += self._progress_step
        return value


class _CollectingSink:
    def __init__(self) -> None:
        self.entries: list[LedgerEntry] = []

    def on_run_complete(self, entry: LedgerEntry) -> None:
        self.entries.append(entry)


class _FailingSink:
    def on_run_complete(self, entry: LedgerEntry) -> None:
        del entry
        raise RuntimeError("sink failed")


def _constant_tool(tool_key: str, name: str, handler):
    return RegisteredTool(
        definition=ToolDefinition(
            key=tool_key,
            name=name,
            description=f"{name} tool",
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": True,
            },
        ),
        handler=handler,
    )


def _echo_handler(arguments: dict[str, object]) -> dict[str, object]:
    return {"echoed": arguments["text"]}


class _FakeDynamicToolSelector:
    def __init__(self, *, selected_keys: tuple[str, ...]) -> None:
        self._selected_keys = selected_keys
        self.calls: list[tuple[tuple[str, ...], str]] = []

    @property
    def config(self) -> ToolSelectionConfig:
        top_k = max(1, len(self._selected_keys))
        return ToolSelectionConfig(enabled=True, top_k=top_k)

    def index(self, profiles) -> None:
        self._indexed = tuple(profile.key for profile in profiles)

    def select(self, *, context_window, candidate_profiles, metadata=None) -> ToolSelectionResult:
        del context_window, metadata
        candidate_keys = tuple(profile.key for profile in candidate_profiles)
        selected_keys = tuple(key for key in self._selected_keys if key in candidate_keys)
        self.calls.append((candidate_keys, "select"))
        return ToolSelectionResult(
            selected_keys=selected_keys,
            retrieval_query="test-query",
            rejected_keys=tuple(key for key in candidate_keys if key not in selected_keys),
        )


class _TrackingFormalizationLayer(BaseFormalizationLayer):
    def __init__(self) -> None:
        self.prepare_calls: list[tuple[str, str]] = []
        self.pre_reset_calls = 0
        self.post_reset_calls = 0
        self.tool_results: list[ToolResult] = []

    def _describe_contract(self) -> str:
        return "Track prompt, parameters, tools, and reset hooks."

    def _describe_rules(self) -> tuple[LayerRuleRecord, ...]:
        return (
            LayerRuleRecord(
                rule_id="TRACKING-LAYER",
                description="Tracks runtime integration points for tests.",
                enforced_at="on_tool_result",
                enforcement_type="transform",
            ),
        )

    def _describe_configuration(self) -> dict[str, object]:
        return {"kind": "tracking"}

    def augment_system_prompt(self, system_prompt: str) -> str:
        return f"{system_prompt}\n\n[TRACKING LAYER]\nUse only the visible tool surface."

    def get_parameter_sections(self) -> tuple[AgentParameterSection, ...]:
        return (AgentParameterSection(title="Formalization Layer", content="tracking"),)

    def filter_tool_keys(self, tool_keys) -> tuple[str, ...]:
        allowed = {"session.echo"}
        return tuple(tool_key for tool_key in tool_keys if tool_key in allowed)

    def on_agent_prepare(self, *, agent_name: str, memory_path: str) -> None:
        self.prepare_calls.append((agent_name, memory_path))

    def on_tool_result(self, result: ToolResult) -> ToolResult:
        self.tool_results.append(result)
        if result.tool_key != "session.echo":
            return result
        output = result.output if isinstance(result.output, dict) else {"raw": result.output}
        return ToolResult(
            tool_key=result.tool_key,
            output={"wrapped": True, "payload": output},
        )

    def on_pre_reset(self) -> None:
        self.pre_reset_calls += 1

    def on_post_reset(self) -> None:
        self.post_reset_calls += 1


class _AllowSpecificToolsLayer(BaseFormalizationLayer):
    def __init__(self, allowed_keys: tuple[str, ...]) -> None:
        self._allowed_keys = allowed_keys

    def _describe_contract(self) -> str:
        return "Restrict the visible tool surface to a known subset."

    def _describe_rules(self) -> tuple[LayerRuleRecord, ...]:
        return (
            LayerRuleRecord(
                rule_id="ALLOW-SPECIFIC-TOOLS",
                description="Only explicitly allowed tools remain visible to the model.",
                enforced_at="filter_tool_keys",
                enforcement_type="block",
            ),
        )

    def _describe_configuration(self) -> dict[str, object]:
        return {"allowed_keys": self._allowed_keys}

    def filter_tool_keys(self, tool_keys) -> tuple[str, ...]:
        allowed = set(self._allowed_keys)
        return tuple(tool_key for tool_key in tool_keys if tool_key in allowed)


class _TrackingBehaviorLayer(BaseBehaviorLayer):
    def __init__(self, events: list[str] | None = None) -> None:
        self.prepare_calls: list[tuple[str, str]] = []
        self.tool_calls: list[ToolCall] = []
        self.tool_results: list[ToolResult] = []
        self._events = events

    def get_behavioral_constraints(self) -> tuple[BehaviorConstraint, ...]:
        return (
            BehaviorConstraint(
                constraint_id="BEHAVIOR-TRACKING",
                description="Track tool-call and tool-result behavior integration points.",
                category="test_behavior",
                enforced_at="on_tool_call",
                violation_action="warn",
            ),
        )

    def on_agent_prepare(self, *, agent_name: str, memory_path: str) -> None:
        self.prepare_calls.append((agent_name, memory_path))
        if self._events is not None:
            self._events.append("behavior")

    def on_tool_call(self, tool_call: ToolCall):
        self.tool_calls.append(tool_call)
        return tool_call

    def on_tool_result_event(self, tool_call: ToolCall, result: ToolResult) -> ToolResult:
        self.tool_results.append(result)
        if result.tool_key != "session.echo":
            return result
        output = result.output if isinstance(result.output, dict) else {"raw": result.output}
        return ToolResult(
            tool_key=result.tool_key,
            output={"wrapped": True, "arguments": dict(tool_call.arguments), "payload": output},
        )


class _OrderingFormalizationLayer(BaseFormalizationLayer):
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def _describe_contract(self) -> str:
        return "Record prepare-order integration."

    def _describe_rules(self) -> tuple[LayerRuleRecord, ...]:
        return ()

    def _describe_configuration(self) -> dict[str, object]:
        return {}

    def on_agent_prepare(self, *, agent_name: str, memory_path: str) -> None:
        del agent_name, memory_path
        self._events.append("formalization")


class _InvalidResultEventLayer(BaseBehaviorLayer):
    def get_behavioral_constraints(self) -> tuple[BehaviorConstraint, ...]:
        return ()

    def on_tool_result_event(self, tool_call: ToolCall, result: ToolResult):
        del tool_call, result
        return {"invalid": True}


class BaseAgentTests(unittest.TestCase):
    def test_runtime_config_defaults_align_with_shared_constants(self) -> None:
        runtime_config = AgentRuntimeConfig()

        self.assertEqual(runtime_config.max_tokens, DEFAULT_AGENT_MAX_TOKENS)
        self.assertEqual(runtime_config.reset_threshold, DEFAULT_AGENT_RESET_THRESHOLD)
        self.assertIsNone(runtime_config.prune_progress_interval)
        self.assertIsNone(runtime_config.prune_token_limit)
        self.assertFalse(runtime_config.tool_selection.enabled)

    def test_build_model_request_preserves_static_tool_surface_when_dynamic_selection_is_disabled(self) -> None:
        registry = ToolRegistry(
            [
                _constant_tool("session.echo", "echo", _echo_handler),
                _constant_tool("session.write", "write", lambda arguments: {"written": arguments}),
            ]
        )
        selector = _FakeDynamicToolSelector(selected_keys=("session.echo",))
        agent = _InspectableAgent(
            model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
            tool_executor=registry,
            runtime_config=AgentRuntimeConfig(
                include_default_output_sink=False,
                tool_selection=ToolSelectionConfig(enabled=False),
            ),
            dynamic_tool_selector=selector,
        )

        request = agent.build_model_request()

        self.assertEqual([tool.key for tool in request.tools], ["session.echo", "session.write"])
        self.assertEqual(selector.calls, [])
        self.assertIsNone(agent.last_tool_selection_result)

    def test_build_model_request_uses_selected_dynamic_tool_subset_when_enabled(self) -> None:
        registry = ToolRegistry(
            [
                _constant_tool("session.echo", "echo", _echo_handler),
                _constant_tool("session.write", "write", lambda arguments: {"written": arguments}),
                _constant_tool("filesystem.read", "read", lambda arguments: {"read": arguments}),
            ]
        )
        selector = _FakeDynamicToolSelector(selected_keys=("session.write", "filesystem.read"))
        agent = _InspectableAgent(
            model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
            tool_executor=registry,
            runtime_config=AgentRuntimeConfig(
                include_default_output_sink=False,
                allowed_tools=("session.*", "filesystem.read"),
                tool_selection=ToolSelectionConfig(
                    enabled=True,
                    top_k=2,
                    candidate_tool_keys=("session.write", "filesystem.read"),
                ),
            ),
            dynamic_tool_selector=selector,
        )

        request = agent.build_model_request()

        self.assertEqual([tool.key for tool in request.tools], ["session.write", "filesystem.read"])
        self.assertEqual(
            selector.calls,
            [(("session.write", "filesystem.read"), "select")],
        )
        self.assertIsNotNone(agent.last_tool_selection_result)
        assert agent.last_tool_selection_result is not None
        self.assertEqual(agent.last_tool_selection_result.selected_keys, ("session.write", "filesystem.read"))

    def test_snapshot_prepares_and_returns_assembled_runtime_state(self) -> None:
        registry = ToolRegistry([_constant_tool("session.echo", "echo", _echo_handler)])
        agent = _InspectableAgent(
            model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
            tool_executor=registry,
            parameter_versions=["snapshot-state"],
        )

        snapshot = agent.snapshot()

        self.assertEqual(snapshot.system_prompt, "System prompt")
        self.assertEqual(snapshot.parameter_sections[0].title, "State")
        self.assertEqual(snapshot.parameter_sections[0].content, "snapshot-state")
        self.assertEqual([tool.key for tool in snapshot.tools], ["session.echo"])
        self.assertEqual(snapshot.memory_path, agent.memory_path)
        self.assertEqual(snapshot.instance_id, agent.instance_id)
        self.assertEqual(snapshot.instance_name, agent.instance_name)

    def test_formalization_layers_augment_prompt_filter_tools_transform_results_and_run_reset_hooks(self) -> None:
        registry = ToolRegistry(
            [
                _constant_tool("session.echo", "echo", _echo_handler),
                _constant_tool("session.write", "write", lambda arguments: {"written": arguments}),
            ]
        )
        model = _FakeModel(
            [
                AgentModelResponse(
                    assistant_message="Use the echo tool.",
                    tool_calls=(ToolCall(tool_key="session.echo", arguments={"text": "hello"}),),
                    should_continue=True,
                ),
                AgentModelResponse(assistant_message="done", should_continue=False),
            ]
        )
        layer = _TrackingFormalizationLayer()
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = _InspectableAgent(
                model=model,
                tool_executor=registry,
                formalization_layers=(layer,),
                parameter_versions=["initial", "refreshed"],
                repo_root=temp_dir,
            )

            request = agent.build_model_request()
            agent.reset_context()
            result = agent.run(max_cycles=3)

        self.assertEqual(result.status, "completed")
        self.assertEqual(layer.prepare_calls[0][0], "inspectable_agent")
        self.assertIn("[TRACKING LAYER]", request.system_prompt)
        self.assertIn("Formalization Layer", [section.title for section in request.parameter_sections])
        self.assertEqual([tool.key for tool in request.tools], ["session.echo"])
        self.assertEqual(layer.pre_reset_calls, 1)
        self.assertEqual(layer.post_reset_calls, 1)
        self.assertTrue(layer.tool_results)
        self.assertIn('"wrapped": true', model.requests[1].transcript[2].content.lower())

    def test_behaviors_run_before_explicit_formalization_layers_and_receive_tool_call_context(self) -> None:
        registry = ToolRegistry(
            [
                _constant_tool("session.echo", "echo", _echo_handler),
                _constant_tool("session.write", "write", lambda arguments: {"written": arguments}),
            ]
        )
        model = _FakeModel(
            [
                AgentModelResponse(
                    assistant_message="Use the echo tool.",
                    tool_calls=(ToolCall(tool_key="session.echo", arguments={"text": "hello"}),),
                    should_continue=True,
                ),
                AgentModelResponse(assistant_message="done", should_continue=False),
            ]
        )
        events: list[str] = []
        behavior = _TrackingBehaviorLayer(events)
        explicit_layer = _OrderingFormalizationLayer(events)

        with tempfile.TemporaryDirectory() as temp_dir:
            agent = _InspectableAgent(
                model=model,
                tool_executor=registry,
                behaviors=(behavior,),
                formalization_layers=(explicit_layer,),
                parameter_versions=["initial", "refreshed"],
                repo_root=temp_dir,
            )

            request = agent.build_model_request()
            result = agent.run(max_cycles=3)

        self.assertEqual(result.status, "completed")
        self.assertEqual(events, ["behavior", "formalization"])
        self.assertEqual(behavior.prepare_calls[0][0], "inspectable_agent")
        self.assertEqual(behavior.tool_calls[0].arguments, {"text": "hello"})
        self.assertIn("[BEHAVIORAL CONSTRAINTS: _TrackingBehaviorLayer]", request.system_prompt)
        self.assertIn('"arguments": {', model.requests[1].transcript[2].content)
        self.assertIn('"text": "hello"', model.requests[1].transcript[2].content)

    def test_result_event_hooks_must_return_tool_result(self) -> None:
        registry = ToolRegistry([_constant_tool("session.echo", "echo", _echo_handler)])
        model = _FakeModel(
            [
                AgentModelResponse(
                    assistant_message="Use the echo tool.",
                    tool_calls=(ToolCall(tool_key="session.echo", arguments={"text": "hello"}),),
                    should_continue=True,
                ),
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            agent = _InspectableAgent(
                model=model,
                tool_executor=registry,
                behaviors=(_InvalidResultEventLayer(),),
                repo_root=temp_dir,
            )

            with self.assertRaisesRegex(
                TypeError,
                r"_InvalidResultEventLayer\.on_tool_result_event\(\) must return ToolResult\.",
            ):
                agent.run(max_cycles=1)

    def test_stages_drive_live_tool_swaps_and_terminal_completion(self) -> None:
        registry = ToolRegistry(
            [
                _constant_tool("session.echo", "echo", _echo_handler),
                _constant_tool("session.write", "write", lambda arguments: {"written": arguments}),
            ]
        )
        discovery_stage = SimpleStageSpec(
            name="discovery",
            description="Discover inputs.",
            system_prompt_fragment="Focus on discovery only.",
            tools=(_constant_tool("stage.discovery", "stage_discovery", "stage-1"),),
            allowed_tool_patterns=("session.echo",),
            required_output_keys=("items",),
            completion_hint="At least one item is found.",
        )
        report_stage = SimpleStageSpec(
            name="report",
            description="Write the report.",
            system_prompt_fragment="Turn the discovered items into a report.",
            tools=(_constant_tool("stage.report", "stage_report", "stage-2"),),
            allowed_tool_patterns=("session.write",),
            required_output_keys=("artifact",),
            completion_hint="The report artifact exists.",
        )
        model = _FakeModel(
            [
                AgentModelResponse(
                    assistant_message="Complete discovery.",
                    tool_calls=(
                        ToolCall(
                            tool_key="formalization.stage_complete",
                            arguments={"summary": "done discovery", "outputs": {"items": ["Acme"]}},
                        ),
                    ),
                    should_continue=True,
                ),
                AgentModelResponse(
                    assistant_message="Complete report.",
                    tool_calls=(
                        ToolCall(
                            tool_key="formalization.stage_complete",
                            arguments={"summary": "done report", "outputs": {"artifact": "report.md"}},
                        ),
                    ),
                    should_continue=True,
                ),
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = _InspectableAgent(
                model=model,
                tool_executor=registry,
                stages=(discovery_stage, report_stage),
                repo_root=temp_dir,
            )

            result = agent.run(max_cycles=5)

            self.assertEqual(result.status, "completed")
            self.assertEqual(result.cycles_completed, 2)
            self.assertEqual(result.resets, 2)
            self.assertEqual(
                [tool.key for tool in model.requests[0].tools],
                ["stage.discovery", "session.echo", "formalization.stage_complete"],
            )
            self.assertEqual(
                [tool.key for tool in model.requests[1].tools],
                ["stage.report", "session.write", "formalization.stage_complete"],
            )
            self.assertIn("[STAGE 1/2: DISCOVERY]", model.requests[0].system_prompt)
            self.assertIn("[STAGE 2/2: REPORT]", model.requests[1].system_prompt)

            stage_outputs_path = agent.memory_path / "stage_outputs.json"
            stage_index_path = agent.memory_path / "stage_index.json"
            self.assertTrue(stage_outputs_path.exists())
            self.assertTrue(stage_index_path.exists())
            outputs_payload = stage_outputs_path.read_text(encoding="utf-8")
            index_payload = stage_index_path.read_text(encoding="utf-8")
            self.assertIn('"discovery"', outputs_payload)
            self.assertIn('"report"', outputs_payload)
            self.assertIn('"current_stage": "report"', index_payload)

    def test_input_and_output_artifacts_wire_into_base_agent_constructor(self) -> None:
        registry = ToolRegistry(create_control_tools())
        model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])

        with tempfile.TemporaryDirectory() as temp_dir:
            memory_path = Path(temp_dir) / "agent-memory"
            brief_path = memory_path / "inputs" / "brief.md"
            brief_path.parent.mkdir(parents=True, exist_ok=True)
            brief_path.write_text("Client brief", encoding="utf-8")

            agent = _InspectableAgent(
                model=model,
                tool_executor=registry,
                input_artifacts=(
                    InputArtifactSpec(
                        name="client_brief",
                        path="inputs/brief.md",
                        description="The full client brief.",
                        file_format="markdown",
                    ),
                ),
                output_artifacts=(
                    OutputArtifactSpec(
                        name="executive_memo",
                        description="A one-page executive memo.",
                        file_format="markdown",
                    ),
                ),
                memory_path=memory_path,
                repo_root=temp_dir,
            )

            request = agent.build_model_request()

        section_titles = [section.title for section in request.parameter_sections]
        self.assertIn("Input: client_brief", section_titles)
        self.assertIn("Output Artifacts", section_titles)
        input_section = next(section for section in request.parameter_sections if section.title == "Input: client_brief")
        output_section = next(section for section in request.parameter_sections if section.title == "Output Artifacts")
        self.assertIn("Client brief", input_section.content)
        self.assertIn('artifact.write_markdown(name="executive_memo", ...)', output_section.content)
        tool_keys = [tool.key for tool in request.tools]
        self.assertIn(CONTROL_MARK_COMPLETE, tool_keys)
        self.assertIn(ARTIFACT_WRITE_MARKDOWN, tool_keys)

    def test_output_artifacts_work_through_base_agent_run_and_block_completion(self) -> None:
        registry = ToolRegistry(create_control_tools())
        model = _FakeModel(
            [
                AgentModelResponse(
                    assistant_message="Try to finish early.",
                    tool_calls=(ToolCall(tool_key=CONTROL_MARK_COMPLETE, arguments={"summary": "done"}),),
                    should_continue=True,
                ),
                AgentModelResponse(
                    assistant_message="Write the memo.",
                    tool_calls=(
                        ToolCall(
                            tool_key=ARTIFACT_WRITE_MARKDOWN,
                            arguments={"name": "executive_memo", "content": "Body"},
                        ),
                    ),
                    should_continue=True,
                ),
                AgentModelResponse(
                    assistant_message="Finish now.",
                    tool_calls=(ToolCall(tool_key=CONTROL_MARK_COMPLETE, arguments={"summary": "done"}),),
                    should_continue=True,
                ),
            ]
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            agent = _InspectableAgent(
                model=model,
                tool_executor=registry,
                output_artifacts=(
                    OutputArtifactSpec(
                        name="executive_memo",
                        description="A one-page executive memo.",
                        file_format="markdown",
                    ),
                ),
                repo_root=temp_dir,
            )

            result = agent.run(max_cycles=5)
            agent.refresh_parameters()

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.cycles_completed, 3)
        self.assertEqual(result.resets, 0)
        self.assertIn("Completion blocked.", model.requests[1].transcript[2].content)
        output_section = next(section for section in agent.parameter_sections if section.title == "Output Artifacts")
        self.assertIn("executive_memo [required]  [written]", output_section.content)

    def test_explicit_output_artifact_layer_tools_still_flow_through_formalization_filters(self) -> None:
        registry = ToolRegistry(
            [
                _constant_tool("session.echo", "echo", _echo_handler),
                *create_control_tools(),
            ]
        )
        model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])
        output_layer = OutputArtifactLayer(
            (
                OutputArtifactSpec(
                    name="executive_memo",
                    description="A one-page executive memo.",
                    file_format="markdown",
                ),
            )
        )
        filter_layer = _AllowSpecificToolsLayer((ARTIFACT_WRITE_MARKDOWN, CONTROL_MARK_COMPLETE))

        with tempfile.TemporaryDirectory() as temp_dir:
            agent = _InspectableAgent(
                model=model,
                tool_executor=registry,
                formalization_layers=(output_layer, filter_layer),
                repo_root=temp_dir,
            )

            request = agent.build_model_request()

        self.assertEqual(
            [tool.key for tool in request.tools],
            [CONTROL_MARK_COMPLETE, ARTIFACT_WRITE_MARKDOWN],
        )

    def test_explicit_input_artifact_layer_renders_sections_through_base_agent(self) -> None:
        registry = ToolRegistry(create_control_tools())
        model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])

        with tempfile.TemporaryDirectory() as temp_dir:
            memory_path = Path(temp_dir) / "agent-memory"
            brief_path = memory_path / "inputs" / "brief.md"
            brief_path.parent.mkdir(parents=True, exist_ok=True)
            brief_path.write_text("Client brief", encoding="utf-8")
            input_layer = InputArtifactLayer(
                (
                    InputArtifactSpec(
                        name="client_brief",
                        path="inputs/brief.md",
                        description="The full client brief.",
                        file_format="markdown",
                    ),
                )
            )

            agent = _InspectableAgent(
                model=model,
                tool_executor=registry,
                formalization_layers=(input_layer,),
                memory_path=memory_path,
                repo_root=temp_dir,
            )

            request = agent.build_model_request()

        input_section = next(section for section in request.parameter_sections if section.title == "Input: client_brief")
        self.assertIn("Client brief", input_section.content)

    def test_run_records_tool_results_and_passes_transcript_to_next_turn(self) -> None:
        registry = ToolRegistry(
            [
                _constant_tool("session.echo", "echo", _echo_handler),
            ]
        )
        model = _FakeModel(
            [
                AgentModelResponse(
                    assistant_message="Use the echo tool.",
                    tool_calls=(ToolCall(tool_key="session.echo", arguments={"text": "hello"}),),
                    should_continue=True,
                ),
                AgentModelResponse(
                    assistant_message="Finished.",
                    should_continue=False,
                ),
            ]
        )
        agent = _InspectableAgent(model=model, tool_executor=registry)

        result = agent.run(max_cycles=5)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.cycles_completed, 2)
        self.assertEqual(len(model.requests), 2)
        self.assertEqual(model.requests[0].transcript, ())
        self.assertEqual(len(model.requests[1].transcript), 3)
        self.assertEqual(model.requests[1].transcript[0].entry_type, "assistant")
        self.assertEqual(model.requests[1].transcript[1].entry_type, "tool_call")
        self.assertEqual(model.requests[1].transcript[2].entry_type, "tool_result")
        self.assertIn("session.echo", model.requests[1].transcript[1].content)
        self.assertIn("hello", model.requests[1].transcript[2].content)

    def test_base_agent_resolves_stable_instance_metadata(self) -> None:
        registry = ToolRegistry([])
        model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])
        payload = {"segment": "platform", "max_tokens": 1024}

        with tempfile.TemporaryDirectory() as temp_dir:
            first = _InspectableAgent(
                model=model,
                tool_executor=registry,
                payload=payload,
                repo_root=temp_dir,
            )
            second = _InspectableAgent(
                model=model,
                tool_executor=registry,
                payload=dict(payload),
                repo_root=temp_dir,
            )

            self.assertEqual(first.instance_id, second.instance_id)
            self.assertEqual(first.instance_name, second.instance_name)
            self.assertEqual(first.instance_record.memory_path, second.instance_record.memory_path)
            self.assertEqual(
                first.memory_path.resolve(),
                (
                    Path(temp_dir)
                    / "memory"
                    / "agents"
                    / "inspectable_agent"
                    / build_agent_instance_dirname(first.instance_id)
                ).resolve(),
            )

    def test_run_wraps_agent_and_tool_execution_in_tracing_helpers(self) -> None:
        registry = ToolRegistry(
            [
                _constant_tool("session.echo", "echo", _echo_handler),
            ]
        )
        model = _FakeModel(
            [
                AgentModelResponse(
                    assistant_message="Use the echo tool.",
                    tool_calls=(ToolCall(tool_key="session.echo", arguments={"text": "hello"}),),
                    should_continue=True,
                ),
                AgentModelResponse(
                    assistant_message="Finished.",
                    should_continue=False,
                ),
            ]
        )
        agent = _InspectableAgent(
            model=model,
            tool_executor=registry,
            runtime_config=AgentRuntimeConfig(langsmith_api_key="ls_test_123"),
        )

        def _wrap_agent(operation, **kwargs):
            del kwargs
            return lambda: operation()

        def _wrap_tool(operation, **kwargs):
            del kwargs
            return operation()

        with (
            patch("harnessiq.agents.base.agent_helpers.build_langsmith_client", return_value=object()) as mock_client,
            patch("harnessiq.agents.base.agent_helpers.trace_agent_run", side_effect=_wrap_agent) as mock_trace_agent,
            patch("harnessiq.agents.base.agent_helpers.trace_tool_call", side_effect=_wrap_tool) as mock_trace_tool,
        ):
            result = agent.run(max_cycles=5)

        self.assertEqual(result.status, "completed")
        self.assertEqual(mock_client.call_count, 2)
        self.assertEqual(mock_trace_agent.call_count, 1)
        self.assertEqual(mock_trace_tool.call_count, 1)
        self.assertEqual(mock_trace_agent.call_args.kwargs["name"], "inspectable_agent.run")
        self.assertEqual(mock_trace_tool.call_args.kwargs["tool_key"], "session.echo")
        self.assertEqual(mock_trace_tool.call_args.kwargs["tool_name"], "echo")

    def test_run_pauses_when_a_tool_returns_pause_signal(self) -> None:
        registry = ToolRegistry(
            [
                _constant_tool(
                    "session.pause",
                    "pause",
                    lambda arguments: AgentPauseSignal(reason="captcha required"),
                ),
            ]
        )
        model = _FakeModel(
            [
                AgentModelResponse(
                    assistant_message="Pause for a CAPTCHA.",
                    tool_calls=(ToolCall(tool_key="session.pause", arguments={}),),
                    should_continue=True,
                ),
            ]
        )
        agent = _InspectableAgent(model=model, tool_executor=registry)

        result = agent.run(max_cycles=3)

        self.assertEqual(result.status, "paused")
        self.assertEqual(result.pause_reason, "captcha required")
        self.assertEqual(result.cycles_completed, 1)
        self.assertEqual(len(model.requests), 1)

    def test_run_pauses_when_builtin_pause_tool_is_invoked(self) -> None:
        registry = ToolRegistry(create_control_tools())
        model = _FakeModel(
            [
                AgentModelResponse(
                    assistant_message="Request approval before continuing.",
                    tool_calls=(
                        ToolCall(
                            tool_key=CONTROL_PAUSE_FOR_HUMAN,
                            arguments={"reason": "approval required", "context_summary": "send outreach"},
                        ),
                    ),
                    should_continue=True,
                ),
            ]
        )
        agent = _InspectableAgent(model=model, tool_executor=registry)

        result = agent.run(max_cycles=3)

        self.assertEqual(result.status, "paused")
        self.assertEqual(result.pause_reason, "approval required")
        self.assertEqual(len(model.requests), 1)
    def test_run_resets_context_and_refreshes_parameters_when_budget_is_exceeded(self) -> None:
        registry = ToolRegistry([])
        model = _FakeModel(
            [
                AgentModelResponse(
                    assistant_message="x" * 400,
                    should_continue=True,
                ),
                AgentModelResponse(
                    assistant_message="done",
                    should_continue=False,
                ),
            ]
        )
        agent = _InspectableAgent(
            model=model,
            tool_executor=registry,
            parameter_versions=["initial", "refreshed"],
            runtime_config=AgentRuntimeConfig(max_tokens=100, reset_threshold=0.5),
        )

        result = agent.run(max_cycles=3)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.resets, 1)
        self.assertEqual(len(model.requests), 2)
        self.assertEqual(model.requests[1].transcript, ())
        self.assertEqual(model.requests[1].parameter_sections[0].content, "refreshed")

    def test_run_resets_when_transcript_free_request_is_below_max_tokens_but_above_threshold(self) -> None:
        registry = ToolRegistry([])
        model = _FakeModel(
            [
                AgentModelResponse(
                    assistant_message="y" * 400,
                    should_continue=True,
                ),
                AgentModelResponse(
                    assistant_message="done",
                    should_continue=False,
                ),
            ]
        )
        agent = _InspectableAgent(
            model=model,
            tool_executor=registry,
            parameter_versions=["x" * 700, "refreshed"],
            runtime_config=AgentRuntimeConfig(max_tokens=400, reset_threshold=0.5),
        )

        result = agent.run(max_cycles=3)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.resets, 1)
        self.assertEqual(len(model.requests), 2)
        self.assertEqual(model.requests[1].transcript, ())
        self.assertEqual(model.requests[1].parameter_sections[0].content, "refreshed")

    def test_run_resets_context_when_prune_progress_interval_is_reached(self) -> None:
        registry = ToolRegistry([])
        model = _FakeModel(
            [
                AgentModelResponse(assistant_message="keep going", should_continue=True),
                AgentModelResponse(assistant_message="done", should_continue=False),
            ]
        )
        agent = _InspectableAgent(
            model=model,
            tool_executor=registry,
            parameter_versions=["initial", "refreshed"],
            progress_step=2,
            runtime_config=AgentRuntimeConfig(
                max_tokens=10_000,
                reset_threshold=0.95,
                prune_progress_interval=2,
            ),
        )

        result = agent.run(max_cycles=3)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.resets, 1)
        self.assertEqual(len(model.requests), 2)
        self.assertEqual(model.requests[1].transcript, ())
        self.assertEqual(model.requests[1].parameter_sections[0].content, "refreshed")

    def test_run_can_reset_immediately_after_a_tool_result_and_skip_remaining_stale_tool_calls(self) -> None:
        first_tool_calls: list[dict[str, object]] = []
        second_tool_calls: list[dict[str, object]] = []
        registry = ToolRegistry(
            [
                _constant_tool(
                    "session.large_result",
                    "large_result",
                    lambda arguments: first_tool_calls.append(dict(arguments)) or {"blob": "x" * 500},
                ),
                _constant_tool(
                    "session.never_run",
                    "never_run",
                    lambda arguments: second_tool_calls.append(dict(arguments)) or {"ok": True},
                ),
            ]
        )
        model = _FakeModel(
            [
                AgentModelResponse(
                    assistant_message="Run both tools.",
                    tool_calls=(
                        ToolCall(tool_key="session.large_result", arguments={"step": 1}),
                        ToolCall(tool_key="session.never_run", arguments={"step": 2}),
                    ),
                    should_continue=True,
                ),
                AgentModelResponse(
                    assistant_message="done",
                    should_continue=False,
                ),
            ]
        )
        agent = _InspectableAgent(
            model=model,
            tool_executor=registry,
            parameter_versions=["initial", "refreshed"],
            runtime_config=AgentRuntimeConfig(max_tokens=220, reset_threshold=0.5),
        )

        result = agent.run(max_cycles=3)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.resets, 1)
        self.assertEqual(len(first_tool_calls), 1)
        self.assertEqual(len(second_tool_calls), 0)
        self.assertEqual(len(model.requests), 2)
        self.assertEqual(model.requests[1].transcript, ())
        self.assertEqual(model.requests[1].parameter_sections[0].content, "refreshed")

    def test_run_resets_context_when_explicit_prune_token_limit_is_reached(self) -> None:
        registry = ToolRegistry([])
        model = _FakeModel(
            [
                AgentModelResponse(assistant_message="x" * 400, should_continue=True),
                AgentModelResponse(assistant_message="done", should_continue=False),
            ]
        )
        agent = _InspectableAgent(
            model=model,
            tool_executor=registry,
            parameter_versions=["initial", "refreshed"],
            runtime_config=AgentRuntimeConfig(
                max_tokens=10_000,
                reset_threshold=0.99,
                prune_token_limit=80,
            ),
        )

        result = agent.run(max_cycles=3)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.resets, 1)
        self.assertEqual(len(model.requests), 2)
        self.assertEqual(model.requests[1].transcript, ())
        self.assertEqual(model.requests[1].parameter_sections[0].content, "refreshed")

    def test_compaction_tool_result_rewrites_agent_context_window(self) -> None:
        registry = ToolRegistry(create_context_compaction_tools())
        compactable_window = [
            {"kind": "parameter", "label": "State", "content": "initial"},
            {"kind": "message", "role": "assistant", "content": "Earlier turn"},
            {"kind": "tool_result", "content": "session.echo\n{\"echoed\": \"hello\"}"},
        ]
        model = _FakeModel(
            [
                AgentModelResponse(
                    assistant_message="Use heavy compaction.",
                    tool_calls=(ToolCall(tool_key=HEAVY_COMPACTION, arguments={"context_window": compactable_window}),),
                    should_continue=True,
                ),
                AgentModelResponse(
                    assistant_message="Finished.",
                    should_continue=False,
                ),
            ]
        )
        agent = _InspectableAgent(model=model, tool_executor=registry)

        result = agent.run(max_cycles=3)

        self.assertEqual(result.status, "completed")
        self.assertEqual(len(model.requests), 2)
        self.assertEqual(model.requests[1].transcript, ())
        self.assertEqual(model.requests[1].parameter_sections[0].content, "initial")

    def test_run_emits_ledger_entry_to_injected_sink(self) -> None:
        registry = ToolRegistry([])
        sink = _CollectingSink()
        agent = _InspectableAgent(
            model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
            tool_executor=registry,
            runtime_config=AgentRuntimeConfig(
                output_sinks=(sink,),
                include_default_output_sink=False,
            ),
        )

        result = agent.run(max_cycles=1)

        self.assertEqual(result.status, "completed")
        self.assertEqual(len(sink.entries), 1)
        self.assertEqual(sink.entries[0].agent_name, "inspectable_agent")
        self.assertEqual(sink.entries[0].outputs["parameter_state"], "initial")
        self.assertEqual(sink.entries[0].tags, ["inspectable"])
        stats = sink.entries[0].metadata["stats"]
        self.assertEqual(stats["version"], 1)
        self.assertEqual(stats["instance_id"], agent.instance_id)
        self.assertTrue(stats["session_id"].startswith("sess_"))
        self.assertEqual(stats["model_provider"], "custom")
        self.assertEqual(stats["model_name"], "_FakeModel")
        self.assertEqual(stats["token_usage"]["source"], "estimated")
        self.assertEqual(stats["counters"]["tool_calls"], 0)
        self.assertEqual(stats["counters"]["distinct_tools"], 0)
        self.assertEqual(stats["counters"]["tool_call_breakdown"], {})

    def test_sink_failures_are_swallowed_and_later_sinks_still_run(self) -> None:
        registry = ToolRegistry([])
        good_sink = _CollectingSink()
        agent = _InspectableAgent(
            model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
            tool_executor=registry,
            runtime_config=AgentRuntimeConfig(
                output_sinks=(_FailingSink(), good_sink),
                include_default_output_sink=False,
            ),
        )

        with self.assertLogs("harnessiq.agents.base.agent", level="WARNING") as logs:
            result = agent.run(max_cycles=1)

        self.assertEqual(result.status, "completed")
        self.assertEqual(len(good_sink.entries), 1)
        self.assertIn("OutputSink _FailingSink failed", "\n".join(logs.output))

    def test_default_jsonl_sink_writes_to_harnessiq_home(self) -> None:
        registry = ToolRegistry([])
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.dict("os.environ", {"HARNESSIQ_HOME": temp_dir}):
                agent = _InspectableAgent(
                    model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
                    tool_executor=registry,
                    runtime_config=AgentRuntimeConfig(),
                )

                agent.run(max_cycles=1)

                ledger_path = Path(temp_dir, "runs.jsonl")
                self.assertTrue(ledger_path.exists())
                self.assertIn("inspectable_agent", ledger_path.read_text(encoding="utf-8"))

    def test_stats_metadata_tracks_tool_counters(self) -> None:
        registry = ToolRegistry(
            [
                _constant_tool("session.echo", "echo", _echo_handler),
            ]
        )
        sink = _CollectingSink()
        model = _FakeModel(
            [
                AgentModelResponse(
                    assistant_message="Use the echo tool.",
                    tool_calls=(ToolCall(tool_key="session.echo", arguments={"text": "hello"}),),
                    should_continue=True,
                ),
                AgentModelResponse(assistant_message="done", should_continue=False),
            ]
        )
        agent = _InspectableAgent(
            model=model,
            tool_executor=registry,
            runtime_config=AgentRuntimeConfig(output_sinks=(sink,), include_default_output_sink=False),
        )

        result = agent.run(max_cycles=3)

        self.assertEqual(result.status, "completed")
        stats = sink.entries[0].metadata["stats"]
        self.assertEqual(stats["counters"]["tool_calls"], 1)
        self.assertEqual(stats["counters"]["distinct_tools"], 1)
        self.assertEqual(stats["counters"]["tool_call_breakdown"], {"session.echo": 1})

    def test_session_id_reuses_latest_paused_run_for_same_instance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir, "repo")
            repo_root.mkdir()
            ledger_path = Path(temp_dir, "runs.jsonl")
            sink = JSONLLedgerSink(path=ledger_path)
            runtime_config = AgentRuntimeConfig(
                output_sinks=(sink,),
                include_default_output_sink=False,
            )
            registry = ToolRegistry([])
            first = _InspectableAgent(
                model=_FakeModel(
                    [AgentModelResponse(assistant_message="pause", pause_reason="needs review")]
                ),
                tool_executor=registry,
                runtime_config=runtime_config,
                repo_root=repo_root,
                payload={"segment": "platform"},
            )

            paused_result = first.run(max_cycles=1)
            self.assertEqual(paused_result.status, "paused")
            first_entry = load_ledger_entries(ledger_path)[0]
            first_session_id = first_entry.metadata["stats"]["session_id"]

            second = _InspectableAgent(
                model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
                tool_executor=registry,
                runtime_config=runtime_config,
                repo_root=repo_root,
                payload={"segment": "platform"},
            )

            completed_result = second.run(max_cycles=1)
            self.assertEqual(completed_result.status, "completed")
            entries = load_ledger_entries(ledger_path)
            self.assertEqual(entries[1].metadata["stats"]["session_id"], first_session_id)

            third = _InspectableAgent(
                model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
                tool_executor=registry,
                runtime_config=runtime_config,
                repo_root=repo_root,
                payload={"segment": "platform"},
            )

            third.run(max_cycles=1)
            entries = load_ledger_entries(ledger_path)
            self.assertNotEqual(entries[2].metadata["stats"]["session_id"], first_session_id)
    def test_runtime_config_rejects_invalid_prune_values(self) -> None:
        with self.assertRaises(ValueError):
            AgentRuntimeConfig(prune_progress_interval=0)
        with self.assertRaises(ValueError):
            AgentRuntimeConfig(prune_token_limit=0)
    def test_inspect_tools_returns_rich_metadata_for_registered_tools(self) -> None:
        registry = ToolRegistry(
            [
                _constant_tool("session.echo", "echo", _echo_handler),
            ]
        )
        agent = _InspectableAgent(model=_FakeModel([]), tool_executor=registry)

        payload = agent.inspect_tools()

        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["key"], "session.echo")
        self.assertEqual(payload[0]["description"], "echo tool")
        self.assertEqual(payload[0]["parameters"], [])
        self.assertEqual(payload[0]["function"]["module"], __name__)
        self.assertEqual(payload[0]["function"]["qualname"], "_echo_handler")

    def test_build_context_window_includes_parameters_and_transcript_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = _InspectableAgent(
                model=_FakeModel([]),
                tool_executor=ToolRegistry([]),
                repo_root=temp_dir,
            )
            agent.refresh_parameters()
            agent._transcript.extend(
                [
                    AgentTranscriptEntry(entry_type="assistant", content="hello"),
                    AgentTranscriptEntry(entry_type="tool_result", content='session.echo\n{"echoed": "hello"}'),
                ]
            )

            context_window = agent.build_context_window()

            self.assertEqual(context_window[0]["kind"], "parameter")
            self.assertEqual(context_window[0]["label"], "State")
            self.assertEqual(context_window[1]["kind"], "assistant")
            self.assertEqual(context_window[2]["kind"], "tool_result")

    def test_context_tools_are_not_bound_until_explicitly_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = _InspectableAgent(
                model=_FakeModel([]),
                tool_executor=ToolRegistry([]),
                repo_root=temp_dir,
            )

            self.assertNotIn(
                CONTEXT_INJECT_ASSISTANT_NOTE,
                {definition.key for definition in agent.available_tools()},
            )

            agent.enable_context_tools()

            self.assertIn(
                CONTEXT_INJECT_ASSISTANT_NOTE,
                {definition.key for definition in agent.available_tools()},
            )

    def test_enable_context_tools_applies_injection_result_without_recording_tool_result(self) -> None:
        registry = ToolRegistry([])
        model = _FakeModel(
            [
                AgentModelResponse(
                    assistant_message="Inject a reminder note.",
                    tool_calls=(
                        ToolCall(
                            tool_key=CONTEXT_INJECT_ASSISTANT_NOTE,
                            arguments={"content": "Focus on the active objective.", "note_type": "plan"},
                        ),
                    ),
                    should_continue=True,
                ),
                AgentModelResponse(
                    assistant_message="Finished.",
                    should_continue=False,
                ),
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = _InspectableAgent(model=model, tool_executor=registry, repo_root=temp_dir)
            agent.enable_context_tools()

            result = agent.run(max_cycles=3)

            self.assertEqual(result.status, "completed")
            self.assertEqual(len(model.requests), 2)
            transcript = model.requests[1].transcript
            self.assertEqual(len(transcript), 3)
            self.assertEqual(transcript[0].entry_type, "assistant")
            self.assertEqual(transcript[1].entry_type, "tool_call")
            self.assertEqual(transcript[2].entry_type, "assistant")
            self.assertIn("[PLAN]", transcript[2].content)

    def test_enable_context_tools_records_group4_results_and_refreshes_parameters(self) -> None:
        registry = ToolRegistry([])
        model = _FakeModel(
            [
                AgentModelResponse(
                    assistant_message="Inject a runtime section.",
                    tool_calls=(
                        ToolCall(
                            tool_key=CONTEXT_PARAM_INJECT_SECTION,
                            arguments={
                                "section_label": "Runtime Note",
                                "content": "This section was injected mid-run.",
                                "position": "last",
                            },
                        ),
                    ),
                    should_continue=True,
                ),
                AgentModelResponse(
                    assistant_message="Finished.",
                    should_continue=False,
                ),
            ]
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = _InspectableAgent(model=model, tool_executor=registry, repo_root=temp_dir)
            agent.enable_context_tools()

            result = agent.run(max_cycles=3)

            self.assertEqual(result.status, "completed")
            self.assertEqual(len(model.requests), 2)
            second_request = model.requests[1]
            self.assertEqual(second_request.parameter_sections[-1].title, "Runtime Note")
            self.assertEqual(second_request.parameter_sections[-1].content, "This section was injected mid-run.")
            self.assertEqual([entry.entry_type for entry in second_request.transcript], ["assistant", "tool_call", "tool_result"])
        agent = _InspectableAgent(model=_FakeModel([]), tool_executor=ToolRegistry([]))
        agent.refresh_parameters()
        agent._transcript.extend(
            [
                AgentTranscriptEntry(entry_type="assistant", content="hello"),
                AgentTranscriptEntry(entry_type="tool_result", content='session.echo\n{"echoed": "hello"}'),
            ]
        )

        context_window = agent.build_context_window()

        self.assertEqual(context_window[0]["kind"], "parameter")
        self.assertEqual(context_window[0]["label"], "State")
        self.assertEqual(context_window[1]["kind"], "assistant")
        self.assertEqual(context_window[2]["kind"], "tool_result")

    def test_json_parameter_section_renders_sorted_json_content(self) -> None:
        section = json_parameter_section("State", {"b": 2, "a": 1})

        self.assertEqual(section.title, "State")
        self.assertEqual(section.content, '{\n  "a": 1,\n  "b": 2\n}')


if __name__ == "__main__":
    unittest.main()
