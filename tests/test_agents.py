"""Tests for the abstract agent base."""

from __future__ import annotations

import unittest

from src.agents import AgentConfigurationError, AgentToolAccessError, BaseAgent, UnsupportedProviderError
from src.tools import ADD_NUMBERS, ECHO_TEXT
from src.tools.registry import UnknownToolError


class RecordingAgent(BaseAgent):
    def invoke(self, messages: list[dict[str, str]]) -> dict[str, object]:
        return self.build_request(messages)


class BaseAgentTests(unittest.TestCase):
    def test_base_agent_requires_concrete_subclass(self) -> None:
        with self.assertRaises(TypeError):
            BaseAgent(
                name="abstract",
                model_name="gpt-4.1",
                system_prompt="Be precise.",
                tools=[ECHO_TEXT],
                provider="openai",
            )

    def test_initialization_rejects_unknown_provider(self) -> None:
        with self.assertRaises(UnsupportedProviderError):
            RecordingAgent(
                name="bad-provider",
                model_name="unknown",
                system_prompt="Be precise.",
                tools=[ECHO_TEXT],
                provider="invalid",  # type: ignore[arg-type]
            )

    def test_initialization_rejects_blank_name(self) -> None:
        with self.assertRaises(AgentConfigurationError):
            RecordingAgent(
                name="   ",
                model_name="gpt-4.1",
                system_prompt="Be precise.",
                tools=[ECHO_TEXT],
                provider="openai",
            )

    def test_initialization_rejects_blank_model_name(self) -> None:
        with self.assertRaises(AgentConfigurationError):
            RecordingAgent(
                name="assistant",
                model_name="   ",
                system_prompt="Be precise.",
                tools=[ECHO_TEXT],
                provider="openai",
            )

    def test_initialization_rejects_unknown_tool_key(self) -> None:
        with self.assertRaises(UnknownToolError):
            RecordingAgent(
                name="bad-tool",
                model_name="gpt-4.1",
                system_prompt="Be precise.",
                tools=["missing.tool"],
                provider="openai",
            )

    def test_build_request_uses_provider_helpers(self) -> None:
        agent = RecordingAgent(
            name="assistant",
            model_name="gpt-4.1",
            system_prompt="Be precise.",
            tools=[ECHO_TEXT],
            provider="openai",
        )

        request = agent.build_request([{"role": "user", "content": "hello"}])

        self.assertEqual(request["model"], "gpt-4.1")
        self.assertEqual(request["messages"][0], {"role": "system", "content": "Be precise."})
        self.assertEqual(request["tools"][0]["function"]["name"], "echo_text")

    def test_execute_tool_runs_authorized_tool(self) -> None:
        agent = RecordingAgent(
            name="assistant",
            model_name="gpt-4.1",
            system_prompt="Be precise.",
            tools=[ADD_NUMBERS],
            provider="openai",
        )

        result = agent.execute_tool(ADD_NUMBERS, {"left": 2, "right": 3})

        self.assertEqual(result.output, {"sum": 5.0})

    def test_execute_tool_rejects_unauthorized_tool(self) -> None:
        agent = RecordingAgent(
            name="assistant",
            model_name="gpt-4.1",
            system_prompt="Be precise.",
            tools=[ECHO_TEXT],
            provider="openai",
        )

        with self.assertRaises(AgentToolAccessError):
            agent.execute_tool(ADD_NUMBERS, {"left": 2, "right": 3})


if __name__ == "__main__":
    unittest.main()
