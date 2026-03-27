"""Focused tests for the ResearchSweepAgent harness."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from harnessiq.agents import AgentModelRequest, AgentModelResponse, ResearchSweepAgent
from harnessiq.providers.serper import SerperClient, SerperCredentials
from harnessiq.shared.agents import AgentContextRuntimeState, DEFAULT_AGENT_CONTEXT_MEMORY_FIELD_RULES
from harnessiq.shared.dtos import ResearchSweepAgentInstancePayload
from harnessiq.shared.research_sweep import (
    CANONICAL_RESEARCH_SWEEP_SITES,
    RESEARCH_SWEEP_MEMORY_FIELD_RULES,
    ResearchSweepMemoryStore,
)
from harnessiq.shared.tools import (
    CONTEXT_INJECT_HANDOFF_BRIEF,
    CONTEXT_INJECT_TASK_REMINDER,
    CONTEXT_PARAM_APPEND_MEMORY_FIELD,
    CONTEXT_PARAM_BULK_WRITE_MEMORY,
    CONTEXT_PARAM_OVERWRITE_MEMORY_FIELD,
    CONTEXT_PARAM_WRITE_ONCE_MEMORY_FIELD,
    CONTEXT_SUMMARIZE_STATE_SNAPSHOT,
    SERPER_REQUEST,
    ToolCall,
)


class _SequenceModel:
    def __init__(self, responses: list[AgentModelResponse]) -> None:
        self._responses = list(responses)
        self.requests: list[AgentModelRequest] = []

    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        self.requests.append(request)
        if self._responses:
            return self._responses.pop(0)
        return AgentModelResponse(assistant_message="done", should_continue=False)


def _serper_client() -> SerperClient:
    return SerperClient(
        credentials=SerperCredentials(api_key="test-serper-key"),
        request_executor=lambda method, url, **kwargs: {"method": method, "url": url, "organic": [], **kwargs},
    )


def _write_context_state(memory_path: Path, memory_fields: dict[str, object]) -> None:
    state = AgentContextRuntimeState(
        memory_fields=dict(memory_fields),
        memory_field_rules={**DEFAULT_AGENT_CONTEXT_MEMORY_FIELD_RULES, **RESEARCH_SWEEP_MEMORY_FIELD_RULES},
    )
    path = memory_path / "context_runtime_state.json"
    path.write_text(json.dumps(state.as_dict(), indent=2, sort_keys=True), encoding="utf-8")


class ResearchSweepAgentTests(unittest.TestCase):
    def test_build_instance_payload_returns_explicit_dto(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temp_dir:
            agent = ResearchSweepAgent(
                model=_SequenceModel([]),
                query="CRISPR therapeutic applications",
                memory_path=temp_dir,
                serper_client=_serper_client(),
            )

            payload = agent.build_instance_payload()

            self.assertIsInstance(payload, ResearchSweepAgentInstancePayload)
            self.assertEqual(payload.to_dict()["config"]["query"], "CRISPR therapeutic applications")

    def test_parameter_sections_render_master_prompt_config_and_custom_memory(self) -> None:
        with self.subTest("initial sections"):
            from tempfile import TemporaryDirectory

            with TemporaryDirectory() as temp_dir:
                agent = ResearchSweepAgent(
                    model=_SequenceModel([]),
                    query="CRISPR therapeutic applications",
                    memory_path=temp_dir,
                    serper_client=_serper_client(),
                )

                sections = agent.load_parameter_sections()
                section_index = {section.title: section.content for section in sections}

                self.assertIn("Master Prompt", section_index)
                self.assertIn("Research Sweep Configuration", section_index)
                self.assertIn("Research Sweep Memory", section_index)
                self.assertNotIn("Context Memory", section_index)
                config_payload = json.loads(section_index["Research Sweep Configuration"])
                self.assertEqual(config_payload["query"], "CRISPR therapeutic applications")
                self.assertEqual(len(config_payload["canonical_site_order"]), 9)
                self.assertEqual(json.loads(section_index["Research Sweep Memory"]), {})

    def test_available_tools_are_limited_to_serper_and_required_context_tools(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temp_dir:
            agent = ResearchSweepAgent(
                model=_SequenceModel([]),
                query="graph neural networks in chemistry",
                memory_path=temp_dir,
                serper_client=_serper_client(),
            )

            self.assertEqual(
                {tool.key for tool in agent.available_tools()},
                {
                    SERPER_REQUEST,
                    CONTEXT_PARAM_WRITE_ONCE_MEMORY_FIELD,
                    CONTEXT_PARAM_OVERWRITE_MEMORY_FIELD,
                    CONTEXT_PARAM_APPEND_MEMORY_FIELD,
                    CONTEXT_PARAM_BULK_WRITE_MEMORY,
                    CONTEXT_INJECT_HANDOFF_BRIEF,
                    CONTEXT_INJECT_TASK_REMINDER,
                    CONTEXT_SUMMARIZE_STATE_SNAPSHOT,
                },
            )

    def test_query_change_resets_stale_context_state(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temp_dir:
            memory_path = Path(temp_dir)
            store = ResearchSweepMemoryStore(memory_path=memory_path)
            store.prepare()
            store.write_query("old query")
            _write_context_state(
                memory_path,
                {
                    "query": "old query",
                    "continuation_pointer": "__COMPLETE__",
                    "final_report": "# Research Findings: old query",
                    "sites_remaining": [],
                },
            )

            ResearchSweepAgent(
                model=_SequenceModel([]),
                query="new query",
                memory_path=memory_path,
                serper_client=_serper_client(),
            )

            self.assertEqual(store.read_query(), "new query")
            self.assertEqual(store.read_research_memory(), {})

    def test_agent_can_complete_synthesis_from_seeded_state(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temp_dir:
            memory_path = Path(temp_dir)
            store = ResearchSweepMemoryStore(memory_path=memory_path)
            store.prepare()
            store.write_query("foundation model evaluation")
            _write_context_state(
                memory_path,
                {
                    "query": "foundation model evaluation",
                    "sites_remaining": [],
                    "continuation_pointer": "__SYNTHESIS__",
                    "site_results": [
                        {
                            "site_key": "google_scholar",
                            "site_name": "Google Scholar",
                            "status": "found",
                            "result_count": 2,
                            "top_results": [],
                            "error_reason": None,
                            "searched_at_reset_count": 0,
                        }
                    ],
                },
            )
            model = _SequenceModel(
                [
                    AgentModelResponse(
                        assistant_message="Write the report.",
                        tool_calls=(
                            ToolCall(
                                CONTEXT_PARAM_OVERWRITE_MEMORY_FIELD,
                                {"field_name": "all_sites_empty", "value": False},
                            ),
                            ToolCall(
                                CONTEXT_PARAM_OVERWRITE_MEMORY_FIELD,
                                {
                                    "field_name": "final_report",
                                    "value": "# Research Findings: foundation model evaluation",
                                },
                            ),
                            ToolCall(
                                CONTEXT_PARAM_OVERWRITE_MEMORY_FIELD,
                                {"field_name": "continuation_pointer", "value": "__COMPLETE__"},
                            ),
                        ),
                        should_continue=False,
                    )
                ]
            )
            agent = ResearchSweepAgent(
                model=model,
                query="foundation model evaluation",
                memory_path=memory_path,
                serper_client=_serper_client(),
            )

            result = agent.run()

            self.assertEqual(result.status, "completed")
            self.assertEqual(
                store.read_final_report(),
                "# Research Findings: foundation model evaluation",
            )
            self.assertEqual(
                store.read_research_memory()["continuation_pointer"],
                "__COMPLETE__",
            )
            self.assertEqual(
                agent.build_ledger_outputs()["query"],
                "foundation model evaluation",
            )

    def test_agent_can_emit_no_results_error_from_seeded_state(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temp_dir:
            memory_path = Path(temp_dir)
            store = ResearchSweepMemoryStore(memory_path=memory_path)
            store.prepare()
            store.write_query("nonexistent biomedical concept")
            _write_context_state(
                memory_path,
                {
                    "query": "nonexistent biomedical concept",
                    "sites_remaining": [],
                    "continuation_pointer": "__SYNTHESIS__",
                    "site_results": [
                        {
                            "site_key": site.site_key,
                            "site_name": site.site_name,
                            "status": "empty",
                            "result_count": 0,
                            "top_results": [],
                            "error_reason": None,
                            "searched_at_reset_count": 0,
                        }
                        for site in CANONICAL_RESEARCH_SWEEP_SITES
                    ],
                },
            )
            model = _SequenceModel(
                [
                    AgentModelResponse(
                        assistant_message="Emit the error block.",
                        tool_calls=(
                            ToolCall(
                                CONTEXT_PARAM_OVERWRITE_MEMORY_FIELD,
                                {"field_name": "all_sites_empty", "value": True},
                            ),
                            ToolCall(
                                CONTEXT_PARAM_OVERWRITE_MEMORY_FIELD,
                                {
                                    "field_name": "final_report",
                                    "value": "NO_RESULTS_ERROR\n- all sources empty",
                                },
                            ),
                            ToolCall(
                                CONTEXT_PARAM_OVERWRITE_MEMORY_FIELD,
                                {"field_name": "continuation_pointer", "value": "__ERROR_ALL_EMPTY__"},
                            ),
                        ),
                        should_continue=False,
                    )
                ]
            )
            agent = ResearchSweepAgent(
                model=model,
                query="nonexistent biomedical concept",
                memory_path=memory_path,
                serper_client=_serper_client(),
            )

            result = agent.run()

            self.assertEqual(result.status, "completed")
            self.assertIn("NO_RESULTS_ERROR", store.read_final_report() or "")
            self.assertTrue(agent.build_ledger_outputs()["all_sites_empty"])


if __name__ == "__main__":
    unittest.main()
