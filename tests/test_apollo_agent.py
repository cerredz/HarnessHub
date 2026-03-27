"""Tests for the abstract Apollo-backed agent harness."""

from __future__ import annotations

from dataclasses import dataclass
from tempfile import TemporaryDirectory
import unittest

from harnessiq.agents import AgentModelRequest, AgentModelResponse, AgentParameterSection
from harnessiq.agents.apollo import ApolloAgentRequest, BaseApolloAgent
from harnessiq.providers.apollo import ApolloClient, ApolloCredentials
from harnessiq.shared.dtos import (
    PreparedProviderOperationResultDTO,
    ProviderOperationRequestDTO,
    StatelessAgentInstancePayload,
)
from harnessiq.shared.tools import APOLLO_REQUEST, RegisteredTool, ToolCall, ToolDefinition


class _FakeModel:
    def __init__(self, responses: list[AgentModelResponse]) -> None:
        self._responses = list(responses)
        self.requests: list[AgentModelRequest] = []

    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        self.requests.append(request)
        return self._responses[len(self.requests) - 1]


class _TestApolloAgent(BaseApolloAgent):
    def __init__(
        self,
        *,
        model: _FakeModel,
        request: ApolloAgentRequest,
        apollo_client: ApolloClient | None = None,
        tools: tuple[RegisteredTool, ...] = (),
        repo_root: str | None = None,
    ) -> None:
        super().__init__(
            name="test_apollo_agent",
            model=model,
            request=request,
            apollo_client=apollo_client,
            tools=tools,
            repo_root=repo_root,
        )

    def apollo_objective(self) -> str:
        return "Find and enrich Apollo prospects."

    def load_apollo_parameter_sections(self) -> list[AgentParameterSection]:
        return [AgentParameterSection(title="Apollo Brief", content="Target VP Sales personas.")]


class BaseApolloAgentTests(unittest.TestCase):
    def test_apollo_agent_accepts_protocol_compatible_client(self) -> None:
        @dataclass
        class _FakeApolloClient:
            credentials: ApolloCredentials

            def request_executor(self, method: str, url: str, **kwargs: object) -> dict[str, object]:
                return {"people": [], "method": method, "url": url, "timeout_seconds": kwargs["timeout_seconds"]}

            def prepare_request(self, request: ProviderOperationRequestDTO):
                return type(
                    "PreparedRequest",
                    (),
                    {
                        "operation": type("Operation", (), {"name": request.operation})(),
                        "method": "POST",
                        "path": "/mixed_people/api_search",
                        "url": "https://api.apollo.io/api/v1/mixed_people/api_search",
                        "headers": {"X-Api-Key": "apollo-secret-key"},
                        "json_body": request.payload,
                    },
                )()

            def execute_operation(
                self,
                request: ProviderOperationRequestDTO,
            ) -> PreparedProviderOperationResultDTO:
                prepared = self.prepare_request(request)
                return PreparedProviderOperationResultDTO.from_prepared_request(
                    prepared=prepared,
                    response=self.request_executor(
                        prepared.method,
                        prepared.url,
                        headers=prepared.headers,
                        json_body=prepared.json_body,
                        timeout_seconds=self.credentials.timeout_seconds,
                    ),
                )

        with TemporaryDirectory() as temp_repo_root:
            credentials = ApolloCredentials(api_key="apollo-secret-key")
            model = _FakeModel(
                [
                    AgentModelResponse(
                        assistant_message="Search Apollo people.",
                        tool_calls=(
                            ToolCall(
                                tool_key=APOLLO_REQUEST,
                                arguments={"operation": "search_people", "payload": {"person_titles": ["VP Sales"]}},
                            ),
                        ),
                        should_continue=False,
                    )
                ]
            )
            agent = _TestApolloAgent(
                model=model,
                request=ApolloAgentRequest(apollo_credentials=credentials),
                apollo_client=_FakeApolloClient(credentials=credentials),
                repo_root=temp_repo_root,
            )

            result = agent.run(max_cycles=1)

            self.assertEqual(result.status, "completed")
            self.assertIn('"operation": "search_people"', agent.transcript[-1].content)

    def test_apollo_agent_injects_masked_credentials_and_default_tooling(self) -> None:
        with TemporaryDirectory() as temp_repo_root:
            credentials = ApolloCredentials(api_key="apollo-secret-key")
            custom_tool = _make_custom_tool()
            model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])
            agent = _TestApolloAgent(
                model=model,
                request=ApolloAgentRequest(apollo_credentials=credentials),
                tools=(custom_tool,),
                repo_root=temp_repo_root,
            )

            result = agent.run(max_cycles=1)

            self.assertEqual(result.status, "completed")
            self.assertIn("apollo_request", model.requests[0].system_prompt)
            self.assertEqual(model.requests[0].parameter_sections[0].title, "Apollo Credentials")
            self.assertEqual(model.requests[0].parameter_sections[1].title, "Apollo Brief")
            self.assertIn(credentials.masked_api_key(), model.requests[0].parameter_sections[0].content)
            self.assertNotIn(credentials.api_key, model.requests[0].parameter_sections[0].content)
            self.assertEqual(model.requests[0].tools[0].name, "apollo_request")
            self.assertIn("custom.apollo_helper", {tool.key for tool in model.requests[0].tools})
            self.assertEqual(agent.request, ApolloAgentRequest(apollo_credentials=credentials))
            self.assertIsInstance(agent.build_instance_payload(), StatelessAgentInstancePayload)

    def test_apollo_agent_executes_search_people_through_provider_tooling(self) -> None:
        with TemporaryDirectory() as temp_repo_root:
            captured: dict[str, object] = {}

            def fake_request_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
                captured["method"] = method
                captured["url"] = url
                captured["kwargs"] = kwargs
                return {"people": []}

            credentials = ApolloCredentials(api_key="apollo-secret-key")
            model = _FakeModel(
                [
                    AgentModelResponse(
                        assistant_message="Search Apollo people.",
                        tool_calls=(
                            ToolCall(
                                tool_key=APOLLO_REQUEST,
                                arguments={"operation": "search_people", "payload": {"person_titles": ["VP Sales"]}},
                            ),
                        ),
                        should_continue=False,
                    )
                ]
            )
            agent = _TestApolloAgent(
                model=model,
                request=ApolloAgentRequest(apollo_credentials=credentials),
                apollo_client=ApolloClient(credentials=credentials, request_executor=fake_request_executor),
                repo_root=temp_repo_root,
            )

            result = agent.run(max_cycles=1)

            self.assertEqual(result.status, "completed")
            self.assertEqual(captured["method"], "POST")
            self.assertIn("/mixed_people/api_search", str(captured["url"]))
            self.assertIn('"operation": "search_people"', agent.transcript[-1].content)

    def test_apollo_agent_can_limit_allowed_operations(self) -> None:
        with TemporaryDirectory() as temp_repo_root:
            credentials = ApolloCredentials(api_key="apollo-secret-key")
            model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])
            agent = _TestApolloAgent(
                model=model,
                request=ApolloAgentRequest(
                    apollo_credentials=credentials,
                    allowed_apollo_operations=("search_people", "view_usage_stats"),
                ),
                repo_root=temp_repo_root,
            )

            agent.run(max_cycles=1)

            self.assertEqual(
                model.requests[0].tools[0].input_schema["properties"]["operation"]["enum"],
                ["search_people", "view_usage_stats"],
            )


def _make_custom_tool() -> RegisteredTool:
    return RegisteredTool(
        definition=ToolDefinition(
            key="custom.apollo_helper",
            name="apollo_helper",
            description="Custom helper for Apollo post-processing.",
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
