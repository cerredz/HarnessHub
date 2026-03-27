"""Minimal pytest-style evaluation examples for Harnessiq agents."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from harnessiq.evaluations import llm_judge, score_efficiency


class _DemoEvalAgent:
    def __init__(self, *, model: str | None) -> None:
        self.model = model or "gpt-4o-mini"

    def run(self, prompt: str) -> SimpleNamespace:
        return SimpleNamespace(
            prompt=prompt,
            model=self.model,
            parallel_tool_calls=True,
            tool_calls=("time.lookup", "weather.lookup"),
            steps=4,
            time=7.5,
            final_output="The local time is 4:00 PM and the weather is sunny.",
        )


@pytest.fixture
def demo_agent(eval_model: str | None) -> _DemoEvalAgent:
    return _DemoEvalAgent(model=eval_model)


@pytest.mark.eval_category("tool_use", "parallelism")
def test_agent_parallelizes_tool_calls(demo_agent: _DemoEvalAgent) -> None:
    """Verifies the agent fetches time and weather in parallel rather than sequentially."""
    result = demo_agent.run("What's the time and weather where I live?")

    assert result.parallel_tool_calls is True


@pytest.mark.eval_category("efficiency")
def test_agent_stays_close_to_ideal_trajectory(demo_agent: _DemoEvalAgent) -> None:
    """Scores one run against a small ideal trajectory budget."""
    result = demo_agent.run("What's the time and weather where I live?")
    score = score_efficiency(
        result,
        {
            "steps": 4,
            "tool_calls": 4,
            "expected_time_seconds": 8,
        },
    )

    assert score["step_ratio"] == pytest.approx(1.0)
    assert score["tool_call_ratio"] == pytest.approx(0.5)
    assert score["latency_ratio"] == pytest.approx(0.9375)


@pytest.mark.eval_category("correctness")
def test_agent_output_semantically_matches_goal(demo_agent: _DemoEvalAgent) -> None:
    """Uses a judge function to check semantic correctness without extra framework code."""
    result = demo_agent.run("What's the time and weather where I live?")

    assert llm_judge(
        result.final_output,
        "Provide both the local time and the weather.",
        judge=lambda prompt: "yes" if "weather" in prompt.lower() else "no",
    )
