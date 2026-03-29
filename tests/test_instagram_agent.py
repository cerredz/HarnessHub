"""Tests for the Instagram keyword discovery agent."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from harnessiq.agents import (
    AgentModelRequest,
    AgentModelResponse,
    InstagramKeywordDiscoveryAgent,
    InstagramMemoryStore,
)
from harnessiq.shared.agents import AgentRuntimeConfig
from harnessiq.shared.dtos import InstagramAgentInstancePayload
from harnessiq.shared.instagram import (
    DEFAULT_AGENT_IDENTITY,
    InstagramLeadRecord,
    InstagramSearchExecution,
    InstagramSearchRecord,
)
from harnessiq.shared.instagram import build_instagram_lead_export_rows
from harnessiq.shared.tools import RegisteredTool, ToolCall, ToolDefinition

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


class _FakeSearchBackend:
    def __init__(self, execution: InstagramSearchExecution) -> None:
        self.execution = execution
        self.calls: list[tuple[str, int]] = []
        self.close_calls = 0

    def search_keyword(self, *, keyword: str, max_results: int) -> InstagramSearchExecution:
        self.calls.append((keyword, max_results))
        return self.execution

    def close(self) -> None:
        self.close_calls += 1


class _FailingSearchBackend:
    def __init__(self, message: str = "google blocked") -> None:
        self.message = message
        self.calls: list[tuple[str, int]] = []
        self.close_calls = 0

    def search_keyword(self, *, keyword: str, max_results: int) -> InstagramSearchExecution:
        self.calls.append((keyword, max_results))
        raise RuntimeError(self.message)

    def close(self) -> None:
        self.close_calls += 1


def _build_execution(keyword: str = "fitness coach") -> InstagramSearchExecution:
    lead = InstagramLeadRecord(
        source_url="https://www.instagram.com/creator-a/",
        source_keyword=keyword,
        found_at="2026-03-19T00:00:00Z",
        emails=("creator@example.com",),
        title="Creator A",
        snippet=f"creator@example.com {keyword}",
    )
    search_record = InstagramSearchRecord(
        keyword=keyword,
        query=f'site:instagram .com "@gmail .com" {keyword}',
        searched_at="2026-03-19T00:00:00Z",
        visited_urls=("https://www.instagram.com/creator-a/",),
        lead_count=1,
        email_count=1,
    )
    return InstagramSearchExecution(search_record=search_record, leads=(lead,))


class InstagramKeywordDiscoveryAgentTests(unittest.TestCase):
    def test_custom_tools_are_added_to_the_agent_surface(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_tool = RegisteredTool(
                definition=ToolDefinition(
                    key="custom.instagram_helper",
                    name="instagram_helper",
                    description="Custom helper.",
                    input_schema={"type": "object", "properties": {}, "required": [], "additionalProperties": False},
                ),
                handler=lambda arguments: {"ok": True, "arguments": arguments},
            )
            agent = InstagramKeywordDiscoveryAgent(
                model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
                search_backend=_FakeSearchBackend(_build_execution()),
                memory_path=temp_dir,
                tools=(custom_tool,),
            )

            self.assertIn("custom.instagram_helper", {tool.key for tool in agent.available_tools()})

    def test_multi_icp_run_rotates_in_configured_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model = _FakeModel(
                [
                    AgentModelResponse(assistant_message="done", should_continue=False),
                    AgentModelResponse(assistant_message="done", should_continue=False),
                ]
            )
            agent = InstagramKeywordDiscoveryAgent(
                model=model,
                search_backend=_FakeSearchBackend(_build_execution()),
                memory_path=temp_dir,
                icp_descriptions=("fitness creators", "ugc skincare creators"),
            )

            result = agent.run(max_cycles=2)

            self.assertEqual(result.status, "completed")
            self.assertTrue(Path(temp_dir, "run_state.json").exists())
            self.assertTrue(Path(temp_dir, "icps").is_dir())
            self.assertEqual(len(model.requests), 2)
            self.assertEqual(
                [section.title for section in model.requests[0].parameter_sections],
                ["Active ICP", "Run Progress", "Recent Searches"],
            )
            self.assertEqual(model.requests[0].parameter_sections[0].content, "fitness creators")
            self.assertEqual(model.requests[1].parameter_sections[0].content, "ugc skincare creators")
            run_state = json.loads(Path(temp_dir, "run_state.json").read_text(encoding="utf-8"))
            self.assertEqual(run_state["status"], "completed")
            self.assertEqual(run_state["active_icp_index"], 1)

    def test_search_tool_persists_results_and_refreshes_active_icp_context_without_transcript_duplication(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model = _FakeModel(
                [
                    AgentModelResponse(
                        assistant_message="Search fitness coach.",
                        tool_calls=(ToolCall(tool_key="instagram.search_keyword", arguments={"keyword": "fitness coach"}),),
                        should_continue=True,
                    ),
                    AgentModelResponse(assistant_message="done", should_continue=False),
                ]
            )
            backend = _FakeSearchBackend(_build_execution())
            agent = InstagramKeywordDiscoveryAgent(
                model=model,
                search_backend=backend,
                memory_path=temp_dir,
                icp_descriptions=("fitness creators",),
            )

            result = agent.run(max_cycles=2)

            self.assertEqual(result.status, "completed")
            self.assertEqual(backend.calls, [("fitness coach", 5)])
            self.assertEqual(model.requests[1].parameter_sections[0].content, "fitness creators")
            self.assertEqual(model.requests[1].parameter_sections[2].content, "fitness coach")
            self.assertEqual(model.requests[1].transcript, ())
            self.assertFalse(any(entry.entry_type == "tool_call" for entry in agent.transcript))
            self.assertFalse(any(entry.entry_type == "tool_result" for entry in agent.transcript))
            database = json.loads(Path(temp_dir, "lead_database.json").read_text(encoding="utf-8"))
            self.assertEqual(database["emails"], ["creator@example.com"])

    def test_sequential_searches_refresh_recent_search_parameter_without_transcript_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model = _FakeModel(
                [
                    AgentModelResponse(
                        assistant_message="Search fitness coach.",
                        tool_calls=(ToolCall(tool_key="instagram.search_keyword", arguments={"keyword": "fitness coach"}),),
                        should_continue=True,
                    ),
                    AgentModelResponse(
                        assistant_message="Search pilates creator.",
                        tool_calls=(ToolCall(tool_key="instagram.search_keyword", arguments={"keyword": "pilates creator"}),),
                        should_continue=True,
                    ),
                    AgentModelResponse(assistant_message="done", should_continue=False),
                ]
            )
            backend = _FakeSearchBackend(_build_execution())
            agent = InstagramKeywordDiscoveryAgent(
                model=model,
                search_backend=backend,
                memory_path=temp_dir,
                icp_descriptions=("fitness creators",),
            )

            result = agent.run(max_cycles=3)

            self.assertEqual(result.status, "completed")
            self.assertEqual(model.requests[1].parameter_sections[2].content, "fitness coach")
            self.assertEqual(model.requests[2].parameter_sections[2].content, "fitness coach, pilates creator")
            self.assertEqual(model.requests[1].transcript, ())
            self.assertEqual(model.requests[2].transcript, ())
            self.assertFalse(any(entry.entry_type == "tool_call" for entry in model.requests[2].transcript))
            self.assertFalse(any(entry.entry_type == "tool_result" for entry in model.requests[2].transcript))

    def test_failed_search_attempt_still_updates_recent_searches_without_persisted_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model = _FakeModel(
                [
                    AgentModelResponse(
                        assistant_message="Search fitness coach.",
                        tool_calls=(ToolCall(tool_key="instagram.search_keyword", arguments={"keyword": "fitness coach"}),),
                        should_continue=True,
                    ),
                    AgentModelResponse(assistant_message="done", should_continue=False),
                ]
            )
            agent = InstagramKeywordDiscoveryAgent(
                model=model,
                search_backend=_FailingSearchBackend("Google blocked"),
                memory_path=temp_dir,
                icp_descriptions=("fitness creators",),
            )

            result = agent.run(max_cycles=2)

            self.assertEqual(result.status, "completed")
            self.assertEqual(model.requests[1].parameter_sections[2].content, "fitness coach")
            self.assertEqual(model.requests[1].transcript, ())
            self.assertEqual(agent.get_search_history(), ())

    def test_duplicate_keyword_detection_is_scoped_per_icp(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model = _FakeModel(
                [
                    AgentModelResponse(
                        assistant_message="Search fitness coach.",
                        tool_calls=(ToolCall(tool_key="instagram.search_keyword", arguments={"keyword": "fitness coach"}),),
                        should_continue=True,
                    ),
                    AgentModelResponse(assistant_message="done", should_continue=False),
                    AgentModelResponse(
                        assistant_message="Search fitness coach again.",
                        tool_calls=(ToolCall(tool_key="instagram.search_keyword", arguments={"keyword": "fitness coach"}),),
                        should_continue=True,
                    ),
                    AgentModelResponse(assistant_message="done", should_continue=False),
                ]
            )
            backend = _FakeSearchBackend(_build_execution())
            agent = InstagramKeywordDiscoveryAgent(
                model=model,
                search_backend=backend,
                memory_path=temp_dir,
                icp_descriptions=("fitness creators", "ugc skincare creators"),
            )

            result = agent.run(max_cycles=4)

            self.assertEqual(result.status, "completed")
            self.assertEqual(backend.calls, [("fitness coach", 5), ("fitness coach", 5)])

    def test_system_prompt_uses_structured_identity_goal_and_checklist_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = InstagramKeywordDiscoveryAgent(
                model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
                search_backend=_FakeSearchBackend(_build_execution()),
                memory_path=temp_dir,
                icp_descriptions=("fitness creators",),
            )

            prompt = agent.build_system_prompt()

            self.assertIn("## Identity", prompt)
            self.assertIn("## Goal", prompt)
            self.assertIn("## Action Checklist", prompt)
            self.assertIn(DEFAULT_AGENT_IDENTITY, prompt)

    def test_recent_searches_are_scoped_to_the_active_icp(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = InstagramMemoryStore(memory_path=temp_dir)
            store.prepare()
            icps = store.initialize_icp_states(["fitness creators", "ugc skincare creators"])
            store.append_search(
                InstagramSearchRecord(
                    keyword="fitness coach",
                    query='site:instagram.com "@gmail.com" "fitness coach"',
                    searched_at="2026-03-19T00:00:00Z",
                ),
                icp_key=icps[0].key,
            )
            store.append_search(
                InstagramSearchRecord(
                    keyword="skincare creator",
                    query='site:instagram.com "@gmail.com" "skincare creator"',
                    searched_at="2026-03-19T01:00:00Z",
                ),
                icp_key=icps[1].key,
            )
            agent = InstagramKeywordDiscoveryAgent(
                model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
                search_backend=_FakeSearchBackend(_build_execution()),
                memory_path=temp_dir,
                icp_descriptions=("fitness creators", "ugc skincare creators"),
            )
            agent.prepare()

            first_sections = agent.load_parameter_sections()
            agent._activate_icp(1)
            second_sections = agent.load_parameter_sections()

            self.assertEqual(first_sections[0].content, "fitness creators")
            self.assertEqual(first_sections[2].content, "fitness coach")
            self.assertEqual(second_sections[0].content, "ugc skincare creators")
            self.assertEqual(second_sections[2].content, "skincare creator")

    def test_legacy_search_history_remains_readable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = InstagramMemoryStore(memory_path=temp_dir)
            store.prepare()
            store.write_icp_profiles(["fitness creators"])
            Path(temp_dir, "search_history.json").write_text(
                json.dumps(
                    [
                        {
                            "email_count": 1,
                            "keyword": "fitness coach",
                            "lead_count": 1,
                            "query": 'site:instagram.com "@gmail.com" "fitness coach"',
                            "searched_at": "2026-03-19T00:00:00Z",
                            "visited_urls": [],
                        }
                    ]
                ),
                encoding="utf-8",
            )
            agent = InstagramKeywordDiscoveryAgent(
                model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
                search_backend=_FakeSearchBackend(_build_execution()),
                memory_path=temp_dir,
                icp_descriptions=("fitness creators",),
            )
            agent.prepare()

            self.assertEqual(agent.get_search_history()[0].keyword, "fitness coach")
            self.assertEqual(agent.load_parameter_sections()[2].content, "fitness coach")

    def test_build_ledger_outputs_reads_persisted_instagram_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = InstagramKeywordDiscoveryAgent(
                model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
                search_backend=_FakeSearchBackend(_build_execution()),
                memory_path=temp_dir,
                icp_descriptions=("fitness creators",),
            )
            agent.prepare()

            agent.tool_executor.execute("instagram.search_keyword", {"keyword": "fitness coach"})
            outputs = agent.build_ledger_outputs()

            self.assertEqual(outputs["emails"], ["creator@example.com"])
            self.assertEqual(outputs["search_history"][0]["keyword"], "fitness coach")
            self.assertEqual(outputs["leads"][0]["source_url"], "https://www.instagram.com/creator-a/")

    def test_build_instagram_lead_export_rows_explodes_one_row_per_email(self) -> None:
        lead = InstagramLeadRecord(
            source_url="https://www.instagram.com/creator-a/",
            source_keyword="fitness coach",
            found_at="2026-03-19T00:00:00Z",
            emails=("creator@example.com", "team@example.com"),
            title="",
            snippet="creator@example.com team@example.com",
        )

        rows = build_instagram_lead_export_rows(lead)

        self.assertEqual(
            rows,
            [
                {
                    "name": "creator-a",
                    "instagram_url": "https://www.instagram.com/creator-a/",
                    "email_address": "creator@example.com",
                    "username": "creator-a",
                },
                {
                    "name": "creator-a",
                    "instagram_url": "https://www.instagram.com/creator-a/",
                    "email_address": "team@example.com",
                    "username": "creator-a",
                },
            ],
        )

    def test_from_memory_loads_runtime_parameters_and_custom_icp_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = InstagramMemoryStore(memory_path=temp_dir)
            store.prepare()
            store.write_icp_profiles(["fitness creators"])
            store.write_runtime_parameters(
                {
                    "recent_result_window": 3,
                    "recent_search_window": 4,
                    "search_result_limit": 2,
                }
            )
            store.write_custom_parameters({"research_mode": True})
            model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])

            agent = InstagramKeywordDiscoveryAgent.from_memory(
                model=model,
                search_backend=_FakeSearchBackend(_build_execution("skincare")),
                memory_path=temp_dir,
                custom_overrides={
                    "icp_profiles": ["ugc skincare creators"],
                    "target_segment": "micro-creators",
                },
            )

            sections = agent.load_parameter_sections()

            self.assertEqual(agent.config.recent_search_window, 4)
            self.assertEqual(agent.config.recent_result_window, 3)
            self.assertEqual(agent.config.search_result_limit, 2)
            self.assertEqual([section.title for section in sections], ["Active ICP", "Run Progress", "Recent Searches", "Custom Parameters"])
            self.assertEqual(sections[0].content, "ugc skincare creators")
            self.assertIn("target_segment", sections[3].content)
            self.assertIn("research_mode", sections[3].content)
            self.assertNotIn("icp_profiles", sections[3].content)

    def test_agent_is_importable_from_harnessiq_agents(self) -> None:
        from harnessiq.agents import InstagramKeywordDiscoveryAgent as Imported

        self.assertIs(Imported, InstagramKeywordDiscoveryAgent)

    def test_build_instance_payload_returns_explicit_dto(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = InstagramKeywordDiscoveryAgent(
                model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
                search_backend=_FakeSearchBackend(_build_execution()),
                memory_path=temp_dir,
                icp_descriptions=("fitness creators",),
            )

            payload = agent.build_instance_payload()

            self.assertIsInstance(payload, InstagramAgentInstancePayload)
            self.assertEqual(payload.to_dict()["runtime"]["search_result_limit"], 5)
            self.assertEqual(payload.to_dict()["memory_path"], Path(temp_dir).as_posix())

    def test_run_closes_backend_after_completion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            backend = _FakeSearchBackend(_build_execution())
            agent = InstagramKeywordDiscoveryAgent(
                model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
                search_backend=backend,
                memory_path=temp_dir,
                icp_descriptions=("fitness creators",),
            )

            agent.run(max_cycles=1)

            self.assertEqual(backend.close_calls, 1)

    def test_run_closes_backend_after_model_error(self) -> None:
        class _FailingModel:
            def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
                raise RuntimeError("boom")

        with tempfile.TemporaryDirectory() as temp_dir:
            backend = _FakeSearchBackend(_build_execution())
            agent = InstagramKeywordDiscoveryAgent(
                model=_FailingModel(),
                search_backend=backend,
                memory_path=temp_dir,
                icp_descriptions=("fitness creators",),
            )

            with self.assertRaisesRegex(RuntimeError, "boom"):
                agent.run(max_cycles=1)

            self.assertEqual(backend.close_calls, 1)

    def test_runtime_config_preserves_langsmith_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            agent = InstagramKeywordDiscoveryAgent(
                model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
                search_backend=_FakeSearchBackend(_build_execution()),
                memory_path=temp_dir,
                icp_descriptions=("fitness creators",),
                runtime_config=AgentRuntimeConfig(
                    langsmith_api_key="ls_test_sdk",
                    langsmith_project="instagram-project",
                ),
            )

            self.assertEqual(agent.runtime_config.langsmith_api_key, "ls_test_sdk")
            self.assertEqual(agent.runtime_config.langsmith_project, "instagram-project")


if __name__ == "__main__":
    unittest.main()
