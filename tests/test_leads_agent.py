"""Tests for the leads discovery agent harness."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harnessiq.agents import AgentModelRequest, AgentModelResponse, LeadsAgent
from harnessiq.agents.leads.agent import (
    LEADS_CHECK_SEEN,
    LEADS_LOG_SEARCH,
    LEADS_SAVE_LEADS,
)
from harnessiq.shared.tools import RegisteredTool, ToolCall, ToolDefinition


class _FakeModel:
    def __init__(self, responses: list[AgentModelResponse]) -> None:
        self._responses = list(responses)
        self.requests: list[AgentModelRequest] = []

    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        self.requests.append(request)
        return self._responses[len(self.requests) - 1]


def _dummy_provider_tool() -> RegisteredTool:
    return RegisteredTool(
        definition=ToolDefinition(
            key="apollo.request",
            name="apollo_request",
            description="Fake Apollo tool for harness tests.",
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": True,
            },
        ),
        handler=lambda arguments: {"ok": True, "arguments": arguments},
    )


class LeadsAgentTests(unittest.TestCase):
    def _make_agent(
        self,
        *,
        temp_dir: str,
        responses: list[AgentModelResponse],
        icps: tuple[str, ...] = ("Sales leaders",),
        search_summary_every: int = 500,
        search_tail_size: int = 20,
        prune_search_interval: int | None = None,
    ) -> tuple[LeadsAgent, _FakeModel]:
        model = _FakeModel(responses)
        agent = LeadsAgent(
            model=model,
            company_background="We sell outbound infrastructure to B2B SaaS revenue teams.",
            icps=icps,
            platforms=("apollo",),
            memory_path=temp_dir,
            tools=(_dummy_provider_tool(),),
            search_summary_every=search_summary_every,
            search_tail_size=search_tail_size,
            prune_search_interval=prune_search_interval,
            max_tokens=10_000,
            reset_threshold=0.99,
        )
        return agent, model

    def test_public_imports_work(self) -> None:
        from harnessiq.agents import LeadsAgent as ImportedLeadsAgent

        self.assertIs(ImportedLeadsAgent, LeadsAgent)

    def test_custom_tools_are_added_alongside_internal_tools(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            agent, _ = self._make_agent(
                temp_dir=temp_dir,
                responses=[AgentModelResponse(assistant_message="done", should_continue=False)],
            )

            keys = {tool.key for tool in agent.available_tools()}

            self.assertIn("apollo.request", keys)
            self.assertIn(LEADS_LOG_SEARCH, keys)

    def test_run_bootstraps_memory_and_parameter_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            agent, model = self._make_agent(
                temp_dir=temp_dir,
                responses=[AgentModelResponse(assistant_message="done", should_continue=False)],
            )

            result = agent.run(max_cycles=2)

            self.assertEqual(result.status, "completed")
            self.assertTrue(Path(temp_dir, "run_config.json").exists())
            self.assertTrue(Path(temp_dir, "run_state.json").exists())
            self.assertTrue(Path(temp_dir, "icps", "sales-leaders.json").exists())
            self.assertTrue(Path(temp_dir, "lead_storage", "saved_leads.json").exists())
            self.assertIn("[GOAL]", model.requests[0].system_prompt)
            self.assertIn("apollo_request", model.requests[0].system_prompt)
            self.assertEqual(
                [section.title for section in model.requests[0].parameter_sections],
                [
                    "Company Background",
                    "Active ICP",
                    "Run Progress",
                    "Search History",
                    "Saved Leads (Current ICP)",
                ],
            )

    def test_run_rotates_across_icps(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            agent, model = self._make_agent(
                temp_dir=temp_dir,
                icps=("Sales leaders", "Marketing leaders"),
                responses=[
                    AgentModelResponse(assistant_message="finished sales", should_continue=False),
                    AgentModelResponse(assistant_message="finished marketing", should_continue=False),
                ],
            )

            result = agent.run(max_cycles=4)

            self.assertEqual(result.status, "completed")
            self.assertEqual(result.cycles_completed, 2)
            self.assertIn('"label": "Sales leaders"', model.requests[0].parameter_sections[1].content)
            self.assertIn('"label": "Marketing leaders"', model.requests[1].parameter_sections[1].content)
            sales_state = agent.memory_store.read_icp_state("sales-leaders")
            marketing_state = agent.memory_store.read_icp_state("marketing-leaders")
            self.assertEqual(sales_state.status, "completed")
            self.assertEqual(marketing_state.status, "completed")
            self.assertEqual(agent.memory_store.read_run_state().status, "completed")

    def test_log_search_persists_and_auto_compacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            agent, _ = self._make_agent(
                temp_dir=temp_dir,
                responses=[AgentModelResponse(assistant_message="done", should_continue=False)],
                search_summary_every=2,
                search_tail_size=1,
            )
            agent.prepare()

            first = agent.tool_executor.execute(
                LEADS_LOG_SEARCH,
                {"platform": "apollo", "query": "VP Sales", "result_count": 5},
            )
            second = agent.tool_executor.execute(
                LEADS_LOG_SEARCH,
                {"platform": "apollo", "query": "Head of Sales", "result_count": 3, "outcome": "title variant"},
            )

            state = agent.memory_store.read_icp_state("sales-leaders")
            self.assertFalse(first.output["auto_compacted"])
            self.assertTrue(second.output["auto_compacted"])
            self.assertEqual(len(state.summaries), 1)
            self.assertEqual([entry.sequence for entry in state.searches], [2])

    def test_save_leads_and_check_seen_use_storage_dedupe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            agent, _ = self._make_agent(
                temp_dir=temp_dir,
                responses=[AgentModelResponse(assistant_message="done", should_continue=False)],
            )
            agent.prepare()

            unseen = agent.tool_executor.execute(
                LEADS_CHECK_SEEN,
                {"full_name": "Alice Smith", "provider": "apollo", "linkedin_url": "https://linkedin.com/in/alice"},
            )
            save_result = agent.tool_executor.execute(
                LEADS_SAVE_LEADS,
                {
                    "leads": [
                        {
                            "full_name": "Alice Smith",
                            "company_name": "Acme",
                            "title": "VP Sales",
                            "provider": "apollo",
                            "linkedin_url": "https://linkedin.com/in/alice",
                        }
                    ]
                },
            )
            seen = agent.tool_executor.execute(
                LEADS_CHECK_SEEN,
                {"full_name": "Alice Smith", "provider": "apollo", "linkedin_url": "https://linkedin.com/in/alice"},
            )
            duplicate = agent.tool_executor.execute(
                LEADS_SAVE_LEADS,
                {
                    "leads": [
                        {
                            "full_name": "Alice Smith",
                            "company_name": "Acme",
                            "title": "VP Sales",
                            "provider": "apollo",
                            "linkedin_url": "https://linkedin.com/in/alice/?trk=foo",
                        }
                    ]
                },
            )

            self.assertFalse(unseen.output["already_seen"])
            self.assertEqual(save_result.output["saved_count"], 1)
            self.assertTrue(seen.output["already_seen"])
            self.assertEqual(duplicate.output["duplicate_count"], 1)
            self.assertEqual(len(agent.config.storage_backend.list_leads()), 1)

    def test_pruning_uses_durable_search_progress(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            agent, model = self._make_agent(
                temp_dir=temp_dir,
                responses=[
                    AgentModelResponse(
                        assistant_message="search one",
                        tool_calls=(ToolCall(tool_key=LEADS_LOG_SEARCH, arguments={"platform": "apollo", "query": "VP Sales"}),),
                        should_continue=True,
                    ),
                    AgentModelResponse(
                        assistant_message="search two",
                        tool_calls=(ToolCall(tool_key=LEADS_LOG_SEARCH, arguments={"platform": "apollo", "query": "Head of Sales"}),),
                        should_continue=True,
                    ),
                    AgentModelResponse(assistant_message="done", should_continue=False),
                ],
                prune_search_interval=1,
            )

            result = agent.run(max_cycles=5)

            self.assertEqual(result.status, "completed")
            self.assertEqual(result.resets, 2)
            self.assertEqual(model.requests[1].transcript, ())
            self.assertEqual(model.requests[2].transcript, ())
