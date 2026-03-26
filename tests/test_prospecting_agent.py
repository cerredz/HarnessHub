"""Tests for the Google Maps prospecting agent harness."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harnessiq.agents.prospecting.agent import GoogleMapsProspectingAgent
from harnessiq.shared.agents import AgentModelRequest, AgentModelResponse, AgentRuntimeConfig
from harnessiq.shared.prospecting import DEFAULT_QUALIFICATION_THRESHOLD, ProspectingMemoryStore
from harnessiq.shared.tools import RegisteredTool, ToolDefinition


class _FakeModel:
    def __init__(self, responses: list[AgentModelResponse]) -> None:
        self._responses = list(responses)
        self.requests: list[AgentModelRequest] = []

    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        self.requests.append(request)
        return self._responses[len(self.requests) - 1]


def _runner(system_prompt, sections, label):  # noqa: ANN001
    del system_prompt, sections
    if label == "search_summary":
        return {"summary": "Searched dentists in Middlesex County.", "insights": ["avoid repeats"]}
    if label == "next_maps_query":
        return {"query": "dentist", "location": "Edison NJ"}
    if label == "evaluate_company":
        return {"verdict": "QUALIFIED", "score": 12}
    raise AssertionError(label)


class GoogleMapsProspectingAgentTests(unittest.TestCase):
    def test_default_qualification_threshold_matches_thirty_point_rubric(self) -> None:
        self.assertEqual(DEFAULT_QUALIFICATION_THRESHOLD, 16)

    def test_custom_tools_are_added_to_the_agent_surface(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_tool = RegisteredTool(
                definition=ToolDefinition(
                    key="custom.prospecting_helper",
                    name="prospecting_helper",
                    description="Custom helper.",
                    input_schema={"type": "object", "properties": {}, "required": [], "additionalProperties": False},
                ),
                handler=lambda arguments: {"ok": True, "arguments": arguments},
            )
            agent = GoogleMapsProspectingAgent(
                model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
                memory_path=temp_dir,
                company_description="Owner-operated dental practices in New Jersey",
                tools=(custom_tool,),
                json_subcall_runner=_runner,
            )

            self.assertIn("custom.prospecting_helper", {tool.key for tool in agent.available_tools()})

    def test_run_bootstraps_memory_files_and_parameter_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])
            agent = GoogleMapsProspectingAgent(
                model=model,
                memory_path=temp_dir,
                company_description="Owner-operated dental practices in New Jersey",
                json_subcall_runner=_runner,
            )

            result = agent.run(max_cycles=1)

            self.assertEqual(result.status, "completed")
            self.assertTrue(Path(temp_dir, "company_description.md").exists())
            self.assertTrue(Path(temp_dir, "prospecting_state.json").exists())
            self.assertTrue(Path(temp_dir, "qualified_leads.jsonl").exists())
            self.assertEqual(
                [section.title for section in model.requests[0].parameter_sections],
                [
                    "Company Description",
                    "Run State",
                    "Recent Completed Searches",
                    "Recent Qualified Leads",
                ],
            )

    def test_build_system_prompt_uses_updated_ai_discoverability_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = GoogleMapsProspectingAgent(
                model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
                memory_path=temp_dir,
                company_description="Owner-operated dental practices in New Jersey",
                json_subcall_runner=_runner,
            )
            agent.prepare()

            prompt = agent.build_system_prompt()

            self.assertIn("AI discoverability services", prompt)
            self.assertIn("PHASE 2 - PROSPECTING WORKFLOW", prompt)
            self.assertIn("Run State.searches_completed_count", prompt)

    def test_shared_and_internal_tools_persist_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])
            agent = GoogleMapsProspectingAgent(
                model=model,
                memory_path=temp_dir,
                company_description="Owner-operated dental practices in New Jersey",
                json_subcall_runner=_runner,
            )
            agent.prepare()

            start = agent.tool_executor.execute(
                "prospecting.start_search",
                {"index": 0, "query": "dentist", "location": "Edison NJ"},
            )
            planning = agent.tool_executor.execute(
                "search.search_or_summarize",
                {},
            )
            saved = agent.tool_executor.execute(
                "prospecting.save_qualified_lead",
                {
                    "record": {
                        "business_name": "Edison Family Dental",
                        "maps_url": "https://maps.google.com/example",
                        "website_url": "https://edisonfamilydental.com",
                        "score": 12,
                        "pitch_hook": "Review gap vs top competitor.",
                        "score_breakdown": {"website_quality": 3},
                        "search_query": "dentist",
                        "search_index": 0,
                        "raw_listing": {"name": "Edison Family Dental"},
                    }
                },
            )
            agent.tool_executor.execute(
                "prospecting.record_listing_result",
                {"search_index": 0, "listing_position": 0, "verdict": "QUALIFIED"},
            )
            completed = agent.tool_executor.execute(
                "prospecting.complete_search",
                {
                    "search_index": 0,
                    "query": "dentist",
                    "location": "Edison NJ",
                    "listings_found": 8,
                },
            )

            self.assertEqual(start.output["last_listing_position"], -1)
            self.assertEqual(planning.output["next_search_index"], 0)
            self.assertEqual(saved.output["business_name"], "Edison Family Dental")
            self.assertEqual(completed.output["qualified_count"], 1)
            self.assertEqual(len(agent.memory_store.read_qualified_leads()), 1)

    def test_from_memory_loads_runtime_and_custom_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ProspectingMemoryStore(memory_path=temp_dir)
            store.prepare()
            store.write_company_description("Owner-operated HVAC companies in central New Jersey")
            store.write_runtime_parameters({"max_tokens": 1234})
            store.write_custom_parameters({"max_searches_per_run": 5, "website_inspect_enabled": False})

            model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])
            agent = GoogleMapsProspectingAgent.from_memory(
                model=model,
                memory_path=temp_dir,
                json_subcall_runner=_runner,
            )

            self.assertEqual(agent.config.max_tokens, 1234)
            self.assertEqual(agent.config.max_searches_per_run, 5)
            self.assertFalse(agent.config.website_inspect_enabled)
            self.assertIn("HVAC companies", agent.load_parameter_sections()[0].content)

    def test_load_parameter_sections_omit_runtime_and_custom_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ProspectingMemoryStore(memory_path=temp_dir)
            store.prepare()
            store.write_company_description("Owner-operated dental practices in New Jersey")
            store.write_runtime_parameters({"max_tokens": 4096, "reset_threshold": 0.8})
            store.write_custom_parameters({"max_searches_per_run": 12, "website_inspect_enabled": False})

            agent = GoogleMapsProspectingAgent.from_memory(
                model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
                memory_path=temp_dir,
                json_subcall_runner=_runner,
            )

            self.assertEqual(
                [section.title for section in agent.load_parameter_sections()],
                [
                    "Company Description",
                    "Run State",
                    "Recent Completed Searches",
                    "Recent Qualified Leads",
                ],
            )

    def test_completed_run_with_active_search_stays_in_progress(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = GoogleMapsProspectingAgent(
                model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
                memory_path=temp_dir,
                company_description="Owner-operated dental practices in New Jersey",
                json_subcall_runner=_runner,
            )
            agent.prepare()
            agent.tool_executor.execute(
                "prospecting.start_search",
                {"index": 0, "query": "dentist", "location": "Edison NJ"},
            )

            result = agent.run(max_cycles=1)

            self.assertEqual(result.status, "completed")
            self.assertEqual(agent.memory_store.read_state().run_status, "in_progress")

    def test_evaluate_company_replaces_threshold_placeholder_in_subcall_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            captured: dict[str, str] = {}

            def runner(system_prompt, sections, label):  # noqa: ANN001
                del sections
                if label == "evaluate_company":
                    captured["system_prompt"] = system_prompt
                    return {
                        "score": 21,
                        "verdict": "QUALIFIED",
                        "score_breakdown": {
                            "competitive_burial_depth": 2,
                            "review_volume_gap": 2,
                            "review_language_and_ai_query_match": 2,
                            "website_quality_and_ai_scrapability": 2,
                            "business_description_quality": 2,
                            "category_specificity_and_query_surface_area": 2,
                            "profile_attribute_completeness": 2,
                            "content_freshness_and_ai_crawl_signal": 2,
                            "qa_section_quality": 2,
                            "industry_margin_and_ai_query_frequency": 3,
                        },
                        "pitch_hook": "Specific gap summary.",
                    }
                return _runner(system_prompt, sections, label)

            agent = GoogleMapsProspectingAgent(
                model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
                memory_path=temp_dir,
                company_description="Owner-operated dental practices in New Jersey",
                qualification_threshold=21,
                eval_system_prompt="Qualification threshold: score >= {{qualification_threshold}} out of 30.",
                json_subcall_runner=runner,
            )
            agent.prepare()

            result = agent.tool_executor.execute(
                "eval.evaluate_company",
                {"listing_data": {"business_name": "Edison Family Dental"}},
            )

            self.assertEqual(result.output["score"], 21)
            self.assertEqual(
                captured["system_prompt"],
                "Qualification threshold: score >= 21 out of 30.",
            )

    def test_runtime_config_preserves_langsmith_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = GoogleMapsProspectingAgent(
                model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
                memory_path=temp_dir,
                company_description="Owner-operated dental practices in New Jersey",
                runtime_config=AgentRuntimeConfig(
                    langsmith_api_key="ls_test_sdk",
                    langsmith_project="prospecting-project",
                ),
                json_subcall_runner=_runner,
            )

            self.assertEqual(agent.runtime_config.langsmith_api_key, "ls_test_sdk")
            self.assertEqual(agent.runtime_config.langsmith_project, "prospecting-project")


if __name__ == "__main__":
    unittest.main()
