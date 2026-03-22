"""Tests for the abstract provider-backed agent scaffold."""

from __future__ import annotations

import json
from tempfile import TemporaryDirectory
import unittest

from harnessiq.agents import AgentModelRequest, AgentModelResponse, AgentParameterSection
from harnessiq.agents.provider_base import BaseProviderToolAgent
from harnessiq.shared.provider_agents import (
    extract_operation_names,
    render_redacted_provider_credentials,
    render_tool_operation_summary,
)
from harnessiq.shared.tools import RegisteredTool, ToolCall, ToolDefinition


class _FakeModel:
    def __init__(self, responses: list[AgentModelResponse]) -> None:
        self._responses = list(responses)
        self.requests: list[AgentModelRequest] = []

    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        self.requests.append(request)
        return self._responses[len(self.requests) - 1]


class _TestProviderAgent(BaseProviderToolAgent):
    def __init__(
        self,
        *,
        model: _FakeModel,
        provider_tools: tuple[RegisteredTool, ...],
        tools: tuple[RegisteredTool, ...] = (),
        credential_content: str | None = None,
        provider_name: str = "Example Provider",
        repo_root: str | None = None,
    ) -> None:
        self._credential_content = credential_content or render_redacted_provider_credentials(
            {"api_key_masked": "exa***1234"},
            allowed_operations=("list_records", "get_record", "update_record"),
        )
        super().__init__(
            name="test_provider_agent",
            model=model,
            provider_name=provider_name,
            provider_tools=provider_tools,
            tools=tools,
            max_tokens=2_000,
            reset_threshold=0.5,
            repo_root=repo_root,
        )

    def provider_identity(self) -> str:
        return "A careful provider test agent."

    def provider_objective(self) -> str:
        return "Handle example provider records safely."

    def provider_transport_guidance(self) -> str:
        return "Use the provider request surface for all remote record work."

    def render_provider_credentials(self) -> str:
        return self._credential_content

    def load_provider_parameter_sections(self) -> list[AgentParameterSection]:
        return [AgentParameterSection(title="Working Set", content="prospects")]

    def provider_behavioral_rules(self) -> tuple[str, ...]:
        return ("Prefer safe preview operations before mutations.",)

    def additional_provider_instructions(self) -> str | None:
        return "Return concise action summaries after each successful tool call."


class ProviderAgentHelperTests(unittest.TestCase):
    def test_render_redacted_provider_credentials_adds_operation_metadata(self) -> None:
        rendered = render_redacted_provider_credentials(
            {"api_key_masked": "abc***1234"},
            allowed_operations=("search", "get_record", "update_record"),
            operation_sample_size=2,
        )

        payload = json.loads(rendered)

        self.assertEqual(payload["api_key_masked"], "abc***1234")
        self.assertEqual(payload["allowed_operation_count"], 3)
        self.assertEqual(payload["allowed_operation_sample"], ["search", "get_record"])

    def test_render_tool_operation_summary_uses_enum_sample(self) -> None:
        tool = _make_provider_tool().definition

        summary = render_tool_operation_summary(tool, sample_size=2)

        self.assertIn("Supported operations", summary)
        self.assertIn("`list_records`", summary)
        self.assertIn("+1 more", summary)
        self.assertEqual(
            extract_operation_names(tool),
            ("list_records", "get_record", "update_record"),
        )


class BaseProviderToolAgentTests(unittest.TestCase):
    def test_agent_builds_prompt_and_parameter_sections_from_hooks(self) -> None:
        with TemporaryDirectory() as temp_repo_root:
            provider_tool = _make_provider_tool()
            custom_tool = _make_custom_tool()
            model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])
            agent = _TestProviderAgent(
                model=model,
                provider_tools=(provider_tool,),
                tools=(custom_tool,),
                repo_root=temp_repo_root,
            )

            agent.run(max_cycles=1)

            request = model.requests[0]
            self.assertIn("[IDENTITY]", request.system_prompt)
            self.assertIn("Use the provider request surface for all remote record work.", request.system_prompt)
            self.assertIn("provider_request", request.system_prompt)
            self.assertIn("`list_records`", request.system_prompt)
            self.assertIn("Prefer safe preview operations before mutations.", request.system_prompt)
            self.assertIn("Return concise action summaries", request.system_prompt)
            self.assertEqual(request.parameter_sections[0].title, "Example Provider Credentials")
            self.assertEqual(request.parameter_sections[1].title, "Working Set")
            self.assertEqual([tool.key for tool in request.tools], ["example.request", "custom.helper"])

    def test_agent_preserves_default_provider_tool_surface_when_custom_tools_conflict(self) -> None:
        with TemporaryDirectory() as temp_repo_root:
            captured: list[str] = []
            provider_tool = _make_provider_tool(captured=captured, output_prefix="provider")
            conflicting_tool = _make_provider_tool(
                captured=captured,
                output_prefix="custom",
                description="Custom override that should never replace the provider default.",
            )
            model = _FakeModel(
                [
                    AgentModelResponse(
                        assistant_message="List the records.",
                        tool_calls=(
                            ToolCall(
                                tool_key="example.request",
                                arguments={"operation": "list_records"},
                            ),
                        ),
                        should_continue=False,
                    )
                ]
            )
            agent = _TestProviderAgent(
                model=model,
                provider_tools=(provider_tool,),
                tools=(conflicting_tool,),
                repo_root=temp_repo_root,
            )

            result = agent.run(max_cycles=1)

            self.assertEqual(result.status, "completed")
            self.assertEqual(captured, ["provider:list_records"])
            self.assertIn('"source": "provider"', agent.transcript[-1].content)

    def test_agent_requires_provider_name_and_provider_tools(self) -> None:
        with TemporaryDirectory() as temp_repo_root:
            model = _FakeModel([AgentModelResponse(assistant_message="done", should_continue=False)])

            with self.assertRaises(ValueError):
                _TestProviderAgent(
                    model=model,
                    provider_tools=(),
                    provider_name="Example Provider",
                    repo_root=temp_repo_root,
                )

            with self.assertRaises(ValueError):
                _TestProviderAgent(
                    model=model,
                    provider_tools=(_make_provider_tool(),),
                    provider_name="   ",
                    repo_root=temp_repo_root,
                )


def _make_provider_tool(
    *,
    captured: list[str] | None = None,
    output_prefix: str = "provider",
    description: str = "Execute authenticated example provider operations.",
) -> RegisteredTool:
    def handler(arguments: dict[str, object]) -> dict[str, object]:
        operation = str(arguments["operation"])
        if captured is not None:
            captured.append(f"{output_prefix}:{operation}")
        return {"source": output_prefix, "operation": operation}

    return RegisteredTool(
        definition=ToolDefinition(
            key="example.request",
            name="provider_request",
            description=description,
            input_schema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["list_records", "get_record", "update_record"],
                    }
                },
                "required": ["operation"],
                "additionalProperties": False,
            },
        ),
        handler=handler,
    )


def _make_custom_tool() -> RegisteredTool:
    return RegisteredTool(
        definition=ToolDefinition(
            key="custom.helper",
            name="custom_helper",
            description="Custom helper for local record post-processing.",
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
