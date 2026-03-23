"""Tests for the abstract Outreach-backed agent harness."""

from __future__ import annotations

from tempfile import TemporaryDirectory
import unittest

from harnessiq.agents import AgentModelRequest, AgentModelResponse, AgentParameterSection
from harnessiq.agents.outreach import BaseOutreachAgent, OutreachAgentConfig
from harnessiq.providers.outreach import OutreachClient, OutreachCredentials
from harnessiq.shared.tools import OUTREACH_REQUEST, RegisteredTool, ToolCall, ToolDefinition


class _FakeModel:
    def __init__(self, responses: list[AgentModelResponse]) -> None:
        self._responses = list(responses)
        self.requests: list[AgentModelRequest] = []

    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        self.requests.append(request)
        return self._responses[len(self.requests) - 1]


class _TestOutreachAgent(BaseOutreachAgent):
    def __init__(
        self,
        *,
        model: _FakeModel,
        outreach_credentials: OutreachCredentials,
        allowed_outreach_operations: tuple[str, ...] | None = None,
        outreach_client: OutreachClient | None = None,
        tools: tuple[RegisteredTool, ...] = (),
        repo_root: str | None = None,
    ) -> None:
        super().__init__(
            name="test_outreach_agent",
            model=model,
            config=OutreachAgentConfig(
                outreach_credentials=outreach_credentials,
                allowed_outreach_operations=allowed_outreach_operations,
            ),
            outreach_client=outreach_client,
            tools=tools,
            repo_root=repo_root,
        )

    def outreach_objective(self) -> str:
        return "Manage Outreach engagement operations safely."

    def load_outreach_parameter_sections(self) -> list[AgentParameterSection]:
        return [AgentParameterSection(title="Outreach Brief", content="Focus on active SDR sequences.")]


class BaseOutreachAgentTests(unittest.TestCase):
    def test_outreach_agent_injects_masked_credentials_and_default_tooling(self) -> None:
        with TemporaryDirectory() as temp_repo_root:
            credentials = OutreachCredentials(access_token="outreach-secret-token")
            custom_tool = _make_custom_tool()
            model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])
            agent = _TestOutreachAgent(
                model=model,
                outreach_credentials=credentials,
                tools=(custom_tool,),
                repo_root=temp_repo_root,
            )

            result = agent.run(max_cycles=1)

            self.assertEqual(result.status, "completed")
            self.assertIn("outreach_request", model.requests[0].system_prompt)
            self.assertEqual(model.requests[0].parameter_sections[0].title, "Outreach Credentials")
            self.assertEqual(model.requests[0].parameter_sections[1].title, "Outreach Brief")
            self.assertIn(credentials.masked_access_token(), model.requests[0].parameter_sections[0].content)
            self.assertNotIn(credentials.access_token, model.requests[0].parameter_sections[0].content)
            self.assertEqual(model.requests[0].tools[0].name, "outreach_request")
            self.assertIn("custom.outreach_helper", {tool.key for tool in model.requests[0].tools})

    def test_outreach_agent_executes_list_prospects_through_provider_tooling(self) -> None:
        with TemporaryDirectory() as temp_repo_root:
            captured: dict[str, object] = {}

            def fake_request_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
                captured["method"] = method
                captured["url"] = url
                captured["kwargs"] = kwargs
                return [{"id": "prospect_1"}]

            credentials = OutreachCredentials(access_token="outreach-secret-token")
            model = _FakeModel(
                [
                    AgentModelResponse(
                        assistant_message="List Outreach prospects.",
                        tool_calls=(
                            ToolCall(
                                tool_key=OUTREACH_REQUEST,
                                arguments={"operation": "list_prospects"},
                            ),
                        ),
                        should_continue=False,
                    )
                ]
            )
            agent = _TestOutreachAgent(
                model=model,
                outreach_credentials=credentials,
                outreach_client=OutreachClient(
                    credentials=credentials,
                    request_executor=fake_request_executor,
                ),
                repo_root=temp_repo_root,
            )

            result = agent.run(max_cycles=1)

            self.assertEqual(result.status, "completed")
            self.assertEqual(captured["method"], "GET")
            self.assertIn("/prospects", str(captured["url"]))
            self.assertIn('"operation": "list_prospects"', agent.transcript[-1].content)

    def test_outreach_agent_can_limit_allowed_operations(self) -> None:
        with TemporaryDirectory() as temp_repo_root:
            credentials = OutreachCredentials(access_token="outreach-secret-token")
            model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])
            agent = _TestOutreachAgent(
                model=model,
                outreach_credentials=credentials,
                allowed_outreach_operations=("list_prospects", "get_prospect"),
                repo_root=temp_repo_root,
            )

            agent.run(max_cycles=1)

            self.assertEqual(
                model.requests[0].tools[0].input_schema["properties"]["operation"]["enum"],
                ["list_prospects", "get_prospect"],
            )

    def test_outreach_agent_rejects_client_with_mismatched_credentials(self) -> None:
        with TemporaryDirectory() as temp_repo_root:
            model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])
            config_credentials = OutreachCredentials(access_token="outreach-secret-token")
            mismatched_client = OutreachClient(
                credentials=OutreachCredentials(access_token="different-secret-token"),
            )

            with self.assertRaisesRegex(
                ValueError,
                "outreach_client credentials must match OutreachAgentConfig.outreach_credentials.",
            ):
                _TestOutreachAgent(
                    model=model,
                    outreach_credentials=config_credentials,
                    outreach_client=mismatched_client,
                    repo_root=temp_repo_root,
                )


def _make_custom_tool() -> RegisteredTool:
    return RegisteredTool(
        definition=ToolDefinition(
            key="custom.outreach_helper",
            name="outreach_helper",
            description="Custom helper for Outreach post-processing.",
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
