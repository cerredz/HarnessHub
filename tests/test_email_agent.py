"""Tests for the abstract email-capable agent harness."""

from __future__ import annotations

import unittest

from harnessiq.agents import AgentModelRequest, AgentModelResponse, AgentParameterSection, BaseEmailAgent, EmailAgentConfig
from harnessiq.shared.tools import RegisteredTool, ToolCall, ToolDefinition
from harnessiq.tools import RESEND_REQUEST, ResendClient, ResendCredentials


class _FakeModel:
    def __init__(self, responses: list[AgentModelResponse]) -> None:
        self._responses = list(responses)
        self.requests: list[AgentModelRequest] = []

    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        self.requests.append(request)
        return self._responses[len(self.requests) - 1]


class _TestEmailAgent(BaseEmailAgent):
    def __init__(
        self,
        *,
        model: _FakeModel,
        resend_credentials: ResendCredentials,
        allowed_resend_operations: tuple[str, ...] | None = None,
        resend_client: ResendClient | None = None,
        tools: tuple[RegisteredTool, ...] = (),
    ) -> None:
        super().__init__(
            name="test_email_agent",
            model=model,
            config=EmailAgentConfig(
                resend_credentials=resend_credentials,
                allowed_resend_operations=allowed_resend_operations,
            ),
            resend_client=resend_client,
            tools=tools,
        )

    def email_objective(self) -> str:
        return "Send personalized onboarding and follow-up emails."

    def load_email_parameter_sections(self) -> list[AgentParameterSection]:
        return [AgentParameterSection(title="Campaign Brief", content="Welcome new qualified leads.")]


class BaseEmailAgentTests(unittest.TestCase):
    def test_email_agent_injects_masked_credentials_and_resend_tool(self) -> None:
        credentials = ResendCredentials(api_key="re_test_1234567890")
        model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])
        agent = _TestEmailAgent(model=model, resend_credentials=credentials)

        result = agent.run(max_cycles=1)

        self.assertEqual(result.status, "completed")
        self.assertIn("resend_request", model.requests[0].system_prompt)
        self.assertEqual(model.requests[0].parameter_sections[0].title, "Resend Credentials")
        self.assertEqual(model.requests[0].parameter_sections[1].title, "Campaign Brief")
        self.assertIn(credentials.masked_api_key(), model.requests[0].parameter_sections[0].content)
        self.assertNotIn(credentials.api_key, model.requests[0].parameter_sections[0].content)
        self.assertEqual(model.requests[0].tools[0].name, "resend_request")

    def test_email_agent_executes_send_email_through_resend_tooling(self) -> None:
        captured: dict[str, object] = {}

        def fake_request_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured["method"] = method
            captured["url"] = url
            captured["kwargs"] = kwargs
            return {"id": "email_123"}

        credentials = ResendCredentials(api_key="re_test_1234567890")
        model = _FakeModel(
            [
                AgentModelResponse(
                    assistant_message="Send the welcome email.",
                    tool_calls=(
                        ToolCall(
                            tool_key=RESEND_REQUEST,
                            arguments={
                                "operation": "send_email",
                                "payload": {
                                    "from": "HarnessHub <hello@example.com>",
                                    "to": ["user@example.com"],
                                    "subject": "Welcome",
                                    "html": "<p>Hello</p>",
                                },
                            },
                        ),
                    ),
                    should_continue=False,
                )
            ]
        )
        agent = _TestEmailAgent(
            model=model,
            resend_credentials=credentials,
            resend_client=ResendClient(credentials=credentials, request_executor=fake_request_executor),
        )

        result = agent.run(max_cycles=1)

        self.assertEqual(result.status, "completed")
        self.assertEqual(captured["method"], "POST")
        self.assertEqual(captured["url"], "https://api.resend.com/emails")
        self.assertIn("email_123", agent.transcript[-1].content)

    def test_email_agent_can_limit_allowed_resend_operations(self) -> None:
        credentials = ResendCredentials(api_key="re_test_1234567890")
        model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])
        agent = _TestEmailAgent(
            model=model,
            resend_credentials=credentials,
            allowed_resend_operations=("send_email", "list_domains"),
        )

        agent.run(max_cycles=1)

        self.assertEqual(
            model.requests[0].tools[0].input_schema["properties"]["operation"]["enum"],
            ["send_email", "list_domains"],
        )

    def test_email_agent_accepts_additive_custom_tools(self) -> None:
        credentials = ResendCredentials(api_key="re_test_1234567890")
        custom_tool = RegisteredTool(
            definition=ToolDefinition(
                key="custom.email_helper",
                name="email_helper",
                description="Custom helper.",
                input_schema={"type": "object", "properties": {}, "required": [], "additionalProperties": False},
            ),
            handler=lambda arguments: {"ok": True, "arguments": arguments},
        )
        agent = _TestEmailAgent(
            model=_FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)]),
            resend_credentials=credentials,
            tools=(custom_tool,),
        )

        self.assertIn("custom.email_helper", {tool.key for tool in agent.available_tools()})


if __name__ == "__main__":
    unittest.main()
