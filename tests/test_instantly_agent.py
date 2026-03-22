"""Tests for the abstract Instantly-backed agent harness."""

from __future__ import annotations

from tempfile import TemporaryDirectory
import unittest

from harnessiq.agents import AgentModelRequest, AgentModelResponse, AgentParameterSection
from harnessiq.agents.instantly import BaseInstantlyAgent, InstantlyAgentConfig
from harnessiq.providers.instantly import InstantlyClient, InstantlyCredentials
from harnessiq.shared.tools import INSTANTLY_REQUEST, RegisteredTool, ToolCall, ToolDefinition


class _FakeModel:
    def __init__(self, responses: list[AgentModelResponse]) -> None:
        self._responses = list(responses)
        self.requests: list[AgentModelRequest] = []

    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        self.requests.append(request)
        return self._responses[len(self.requests) - 1]


class _TestInstantlyAgent(BaseInstantlyAgent):
    def __init__(
        self,
        *,
        model: _FakeModel,
        instantly_credentials: InstantlyCredentials,
        allowed_instantly_operations: tuple[str, ...] | None = None,
        instantly_client: InstantlyClient | None = None,
        tools: tuple[RegisteredTool, ...] = (),
        repo_root: str | None = None,
    ) -> None:
        super().__init__(
            name="test_instantly_agent",
            model=model,
            config=InstantlyAgentConfig(
                instantly_credentials=instantly_credentials,
                allowed_instantly_operations=allowed_instantly_operations,
            ),
            instantly_client=instantly_client,
            tools=tools,
            repo_root=repo_root,
        )

    def instantly_objective(self) -> str:
        return "Manage Instantly outreach operations safely."

    def load_instantly_parameter_sections(self) -> list[AgentParameterSection]:
        return [AgentParameterSection(title="Instantly Brief", content="Focus on active outbound campaigns.")]


class BaseInstantlyAgentTests(unittest.TestCase):
    def test_instantly_agent_injects_masked_credentials_and_default_tooling(self) -> None:
        with TemporaryDirectory() as temp_repo_root:
            credentials = InstantlyCredentials(api_key="instantly-secret-key")
            custom_tool = _make_custom_tool()
            model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])
            agent = _TestInstantlyAgent(
                model=model,
                instantly_credentials=credentials,
                tools=(custom_tool,),
                repo_root=temp_repo_root,
            )

            result = agent.run(max_cycles=1)

            self.assertEqual(result.status, "completed")
            self.assertIn("instantly_request", model.requests[0].system_prompt)
            self.assertEqual(model.requests[0].parameter_sections[0].title, "Instantly Credentials")
            self.assertEqual(model.requests[0].parameter_sections[1].title, "Instantly Brief")
            self.assertIn(credentials.masked_api_key(), model.requests[0].parameter_sections[0].content)
            self.assertNotIn(credentials.api_key, model.requests[0].parameter_sections[0].content)
            self.assertEqual(model.requests[0].tools[0].name, "instantly_request")
            self.assertIn("custom.instantly_helper", {tool.key for tool in model.requests[0].tools})

    def test_instantly_agent_executes_list_campaigns_through_provider_tooling(self) -> None:
        with TemporaryDirectory() as temp_repo_root:
            captured: dict[str, object] = {}

            def fake_request_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
                captured["method"] = method
                captured["url"] = url
                captured["kwargs"] = kwargs
                return [{"id": "campaign_1"}]

            credentials = InstantlyCredentials(api_key="instantly-secret-key")
            model = _FakeModel(
                [
                    AgentModelResponse(
                        assistant_message="List the campaigns.",
                        tool_calls=(
                            ToolCall(
                                tool_key=INSTANTLY_REQUEST,
                                arguments={"operation": "list_campaigns"},
                            ),
                        ),
                        should_continue=False,
                    )
                ]
            )
            agent = _TestInstantlyAgent(
                model=model,
                instantly_credentials=credentials,
                instantly_client=InstantlyClient(credentials=credentials, request_executor=fake_request_executor),
                repo_root=temp_repo_root,
            )

            result = agent.run(max_cycles=1)

            self.assertEqual(result.status, "completed")
            self.assertEqual(captured["method"], "GET")
            self.assertIn("/campaigns", str(captured["url"]))
            self.assertIn('"operation": "list_campaigns"', agent.transcript[-1].content)

    def test_instantly_agent_can_limit_allowed_operations(self) -> None:
        with TemporaryDirectory() as temp_repo_root:
            credentials = InstantlyCredentials(api_key="instantly-secret-key")
            model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])
            agent = _TestInstantlyAgent(
                model=model,
                instantly_credentials=credentials,
                allowed_instantly_operations=("list_campaigns", "get_campaign"),
                repo_root=temp_repo_root,
            )

            agent.run(max_cycles=1)

            self.assertEqual(
                model.requests[0].tools[0].input_schema["properties"]["operation"]["enum"],
                ["list_campaigns", "get_campaign"],
            )


def _make_custom_tool() -> RegisteredTool:
    return RegisteredTool(
        definition=ToolDefinition(
            key="custom.instantly_helper",
            name="instantly_helper",
            description="Custom helper for Instantly post-processing.",
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
                "additionalProperties": False,
            },
        ),
        handler=lambda arguments: {"ok": True, "arguments": arguments},
    )


if __name__ == "__main__":
    unittest.main()
