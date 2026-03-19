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
from harnessiq.shared.instagram import InstagramLeadRecord, InstagramSearchExecution, InstagramSearchRecord
from harnessiq.shared.tools import ToolCall

_LANGSMITH_CLIENT_PATCHER = patch("harnessiq.agents.base.agent.build_langsmith_client", return_value=None)


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

    def search_keyword(self, *, keyword: str, max_results: int) -> InstagramSearchExecution:
        self.calls.append((keyword, max_results))
        return self.execution


def _build_execution(keyword: str = "fitness coach") -> InstagramSearchExecution:
    lead = InstagramLeadRecord(
        source_url="https://www.instagram.com/creator-a/",
        source_keyword=keyword,
        found_at="2026-03-19T00:00:00Z",
        emails=("creator@example.com",),
        title="Creator A",
        snippet="creator@example.com fitness coach",
    )
    search_record = InstagramSearchRecord(
        keyword=keyword,
        query='site:instagram.com "@gmail.com" "fitness coach"',
        searched_at="2026-03-19T00:00:00Z",
        visited_urls=("https://www.instagram.com/creator-a/",),
        lead_count=1,
        email_count=1,
    )
    return InstagramSearchExecution(search_record=search_record, leads=(lead,))


class InstagramKeywordDiscoveryAgentTests(unittest.TestCase):
    def test_run_bootstraps_memory_files_and_parameter_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])
            agent = InstagramKeywordDiscoveryAgent(
                model=model,
                search_backend=_FakeSearchBackend(_build_execution()),
                memory_path=temp_dir,
                icp_descriptions=("fitness creators", "ugc skincare creators"),
            )

            result = agent.run(max_cycles=1)

            self.assertEqual(result.status, "completed")
            self.assertTrue(Path(temp_dir, "icp_profiles.json").exists())
            self.assertTrue(Path(temp_dir, "search_history.json").exists())
            self.assertTrue(Path(temp_dir, "lead_database.json").exists())
            self.assertTrue(Path(temp_dir, "runtime_parameters.json").exists())
            self.assertEqual(
                [section.title for section in model.requests[0].parameter_sections],
                ["ICP Profiles", "Recent Searches", "Recent Search Results"],
            )
            self.assertIn("fitness creators", model.requests[0].parameter_sections[0].content)

    def test_search_tool_persists_results_and_refreshes_parameter_sections(self) -> None:
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
            self.assertEqual(len(model.requests), 2)
            self.assertIn("fitness coach", model.requests[1].parameter_sections[1].content)
            self.assertIn("creator@example.com", model.requests[1].parameter_sections[2].content)
            database = json.loads(Path(temp_dir, "lead_database.json").read_text(encoding="utf-8"))
            self.assertEqual(database["emails"], ["creator@example.com"])

    def test_get_emails_returns_unique_persisted_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])
            agent = InstagramKeywordDiscoveryAgent(
                model=model,
                search_backend=_FakeSearchBackend(_build_execution()),
                memory_path=temp_dir,
                icp_descriptions=("fitness creators",),
            )
            agent.prepare()

            agent.tool_executor.execute("instagram.search_keyword", {"keyword": "fitness coach"})
            agent.tool_executor.execute("instagram.search_keyword", {"keyword": "fitness coach"})

            self.assertEqual(agent.get_emails(), ("creator@example.com",))

    def test_from_memory_loads_runtime_parameters(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = InstagramMemoryStore(memory_path=temp_dir)
            store.prepare()
            store.write_icp_profiles(["ugc skincare creators"])
            store.write_runtime_parameters(
                {
                    "recent_result_window": 3,
                    "recent_search_window": 4,
                    "search_result_limit": 2,
                }
            )
            model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])

            agent = InstagramKeywordDiscoveryAgent.from_memory(
                model=model,
                search_backend=_FakeSearchBackend(_build_execution("skincare")),
                memory_path=temp_dir,
            )

            self.assertEqual(agent.config.recent_search_window, 4)
            self.assertEqual(agent.config.recent_result_window, 3)
            self.assertEqual(agent.config.search_result_limit, 2)
            self.assertIn("ugc skincare creators", agent.load_parameter_sections()[0].content)

    def test_agent_is_importable_from_harnessiq_agents(self) -> None:
        from harnessiq.agents import InstagramKeywordDiscoveryAgent as Imported

        self.assertIs(Imported, InstagramKeywordDiscoveryAgent)

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
