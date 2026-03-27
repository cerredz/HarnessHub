"""Tests for the abstract Exa-backed agent harness."""

from __future__ import annotations

from dataclasses import dataclass
from tempfile import TemporaryDirectory
import unittest

from harnessiq.agents import AgentModelRequest, AgentModelResponse, AgentParameterSection
from harnessiq.agents.exa import BaseExaAgent, ExaAgentRequest
from harnessiq.providers.exa import ExaClient, ExaCredentials
from harnessiq.shared.dtos import StatelessAgentInstancePayload
from harnessiq.shared.tools import EXA_REQUEST, RegisteredTool, ToolCall, ToolDefinition


class _FakeModel:
    def __init__(self, responses: list[AgentModelResponse]) -> None:
        self._responses = list(responses)
        self.requests: list[AgentModelRequest] = []

    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        self.requests.append(request)
        return self._responses[len(self.requests) - 1]


class _TestExaAgent(BaseExaAgent):
    def __init__(
        self,
        *,
        model: _FakeModel,
        request: ExaAgentRequest,
        exa_client: ExaClient | None = None,
        tools: tuple[RegisteredTool, ...] = (),
        repo_root: str | None = None,
    ) -> None:
        super().__init__(
            name="test_exa_agent",
            model=model,
            request=request,
            exa_client=exa_client,
            tools=tools,
            repo_root=repo_root,
        )

    def exa_objective(self) -> str:
        return "Run grounded Exa research workflows."

    def load_exa_parameter_sections(self) -> list[AgentParameterSection]:
        return [AgentParameterSection(title="Research Brief", content="Investigate AI infrastructure companies.")]


class BaseExaAgentTests(unittest.TestCase):
    def test_exa_agent_accepts_protocol_compatible_client(self) -> None:
        @dataclass
        class _FakeExaClient:
            credentials: ExaCredentials

            def request_executor(self, method: str, url: str, **kwargs: object) -> dict[str, object]:
                return {"results": [], "method": method, "url": url, "timeout_seconds": kwargs["timeout_seconds"]}

            def prepare_request(
                self,
                operation_name: str,
                *,
                path_params=None,
                query=None,
                payload=None,
            ):
                del path_params, query
                return type(
                    "PreparedRequest",
                    (),
                    {
                        "operation": type("Operation", (), {"name": operation_name})(),
                        "method": "POST",
                        "path": "/search",
                        "url": "https://api.exa.ai/search",
                        "headers": {"x-api-key": "exa-secret-key"},
                        "json_body": payload,
                    },
                )()

        with TemporaryDirectory() as temp_repo_root:
            credentials = ExaCredentials(api_key="exa-secret-key")
            model = _FakeModel(
                [
                    AgentModelResponse(
                        assistant_message="Search Exa.",
                        tool_calls=(
                            ToolCall(
                                tool_key=EXA_REQUEST,
                                arguments={"operation": "search", "payload": {"query": "AI infrastructure"}},
                            ),
                        ),
                        should_continue=False,
                    )
                ]
            )
            agent = _TestExaAgent(
                model=model,
                request=ExaAgentRequest(exa_credentials=credentials),
                exa_client=_FakeExaClient(credentials=credentials),
                repo_root=temp_repo_root,
            )

            result = agent.run(max_cycles=1)

            self.assertEqual(result.status, "completed")
            self.assertIn('"operation": "search"', agent.transcript[-1].content)

    def test_exa_agent_injects_masked_credentials_and_default_tooling(self) -> None:
        with TemporaryDirectory() as temp_repo_root:
            credentials = ExaCredentials(api_key="exa-secret-key")
            custom_tool = _make_custom_tool()
            model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])
            agent = _TestExaAgent(
                model=model,
                request=ExaAgentRequest(exa_credentials=credentials),
                tools=(custom_tool,),
                repo_root=temp_repo_root,
            )

            result = agent.run(max_cycles=1)

            self.assertEqual(result.status, "completed")
            self.assertIn("exa_request", model.requests[0].system_prompt)
            self.assertEqual(model.requests[0].parameter_sections[0].title, "Exa Credentials")
            self.assertEqual(model.requests[0].parameter_sections[1].title, "Research Brief")
            self.assertIn(credentials.masked_api_key(), model.requests[0].parameter_sections[0].content)
            self.assertNotIn(credentials.api_key, model.requests[0].parameter_sections[0].content)
            self.assertEqual(model.requests[0].tools[0].name, "exa_request")
            self.assertIn("custom.exa_helper", {tool.key for tool in model.requests[0].tools})
            self.assertEqual(agent.request, ExaAgentRequest(exa_credentials=credentials))
            self.assertIsInstance(agent.build_instance_payload(), StatelessAgentInstancePayload)

    def test_exa_agent_executes_search_through_provider_tooling(self) -> None:
        with TemporaryDirectory() as temp_repo_root:
            captured: dict[str, object] = {}

            def fake_request_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
                captured["method"] = method
                captured["url"] = url
                captured["kwargs"] = kwargs
                return {"results": []}

            credentials = ExaCredentials(api_key="exa-secret-key")
            model = _FakeModel(
                [
                    AgentModelResponse(
                        assistant_message="Search Exa.",
                        tool_calls=(
                            ToolCall(
                                tool_key=EXA_REQUEST,
                                arguments={"operation": "search", "payload": {"query": "AI infrastructure"}},
                            ),
                        ),
                        should_continue=False,
                    )
                ]
            )
            agent = _TestExaAgent(
                model=model,
                request=ExaAgentRequest(exa_credentials=credentials),
                exa_client=ExaClient(credentials=credentials, request_executor=fake_request_executor),
                repo_root=temp_repo_root,
            )

            result = agent.run(max_cycles=1)

            self.assertEqual(result.status, "completed")
            self.assertEqual(captured["method"], "POST")
            self.assertIn("/search", str(captured["url"]))
            self.assertIn('"operation": "search"', agent.transcript[-1].content)

    def test_exa_agent_can_limit_allowed_operations(self) -> None:
        with TemporaryDirectory() as temp_repo_root:
            credentials = ExaCredentials(api_key="exa-secret-key")
            model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])
            agent = _TestExaAgent(
                model=model,
                request=ExaAgentRequest(
                    exa_credentials=credentials,
                    allowed_exa_operations=("search", "get_contents"),
                ),
                repo_root=temp_repo_root,
            )

            agent.run(max_cycles=1)

            self.assertEqual(
                model.requests[0].tools[0].input_schema["properties"]["operation"]["enum"],
                ["search", "get_contents"],
            )


def _make_custom_tool() -> RegisteredTool:
    return RegisteredTool(
        definition=ToolDefinition(
            key="custom.exa_helper",
            name="exa_helper",
            description="Custom helper for Exa post-processing.",
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
