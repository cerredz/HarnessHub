"""Tests for the evaluation scaffolding layer."""

from __future__ import annotations

import re

import pytest

from harnessiq.evaluations import (
    CORRECTNESS_CATEGORY,
    EFFICIENCY_CATEGORY,
    OUTPUT_CATEGORY,
    TOOL_USE_CATEGORY,
    EvaluationContext,
    EvaluationRegistry,
    EvaluationToolCall,
    build_correctness_case,
    build_metrics_snapshot,
    build_output_case,
    build_tool_use_case,
    duration_at_most,
    final_output_exists,
    metadata_has_keys,
    output_contains,
    output_contains_all,
    output_field_equals,
    output_matches_regex,
    run_evaluation_case,
    solve_rate_at_least,
    step_count_at_most,
    tool_call_count_at_most,
    tool_called,
    tool_called_at_least,
    tool_called_exactly,
    tool_not_called,
    tools_called_in_order,
)


def _sample_context() -> EvaluationContext:
    return EvaluationContext(
        task="Read a file and summarize it.",
        final_output={
            "summary": {"status": "ok", "text": "The summary is complete and cites the file."},
            "answer": "Complete summary",
        },
        tool_calls=(
            "filesystem.read_text_file",
            {"key": "text.normalize_whitespace", "arguments": {"text": "raw"}},
            EvaluationToolCall(key="prompt.create_system_prompt"),
        ),
        metadata={"model": "demo-model", "trace": {"langsmith_run_id": "run-123"}},
        duration_seconds=6.5,
        expected_duration_seconds=8.0,
        expected_step_count=3,
        expected_tool_calls=3,
    )


def test_context_coerces_tool_calls_and_defaults_step_count() -> None:
    context = _sample_context()

    assert context.step_count == 3
    assert context.tool_keys == (
        "filesystem.read_text_file",
        "text.normalize_whitespace",
        "prompt.create_system_prompt",
    )
    assert context.tool_call_count("filesystem.read_text_file") == 1


@pytest.mark.parametrize(
    ("check_factory", "expected_name"),
    [
        (lambda: final_output_exists(), "final_output_exists"),
        (lambda: output_contains("summary is complete"), "output_contains"),
        (lambda: output_contains_all(["summary", "cites the file"]), "output_contains_all"),
        (lambda: output_matches_regex(r"complete summary", flags=re.IGNORECASE), "output_matches_regex"),
        (lambda: output_field_equals("summary.status", "ok"), "output_field_equals"),
        (lambda: metadata_has_keys("model", "trace.langsmith_run_id"), "metadata_has_keys"),
        (lambda: tool_called("filesystem.read_text_file"), "tool_called"),
        (lambda: tool_not_called("browser.navigate"), "tool_not_called"),
        (lambda: tool_called_exactly("filesystem.read_text_file", 1), "tool_called_exactly"),
        (lambda: tool_called_at_least("text.normalize_whitespace", 1), "tool_called_at_least"),
        (lambda: tool_call_count_at_most(3), "tool_call_count_at_most"),
        (lambda: tools_called_in_order("filesystem.read_text_file", "prompt.create_system_prompt"), "tools_called_in_order"),
        (lambda: step_count_at_most(3), "step_count_at_most"),
        (lambda: duration_at_most(7.0), "duration_at_most"),
        (lambda: solve_rate_at_least(1.0), "solve_rate_at_least"),
    ],
)
def test_general_purpose_checks_pass_for_simple_matching_context(check_factory, expected_name: str) -> None:
    result = check_factory()(_sample_context())

    assert result.name == expected_name
    assert result.passed is True


def test_checks_return_clear_failures_for_non_matching_context() -> None:
    context = EvaluationContext(
        final_output={"summary": {"status": "needs_review"}},
        tool_calls=("browser.navigate",),
        metadata={},
        step_count=5,
        duration_seconds=12.0,
        expected_step_count=3,
    )

    assert output_contains("complete")(context).passed is False
    assert metadata_has_keys("trace.langsmith_run_id")(context).passed is False
    assert tool_not_called("browser.navigate")(context).passed is False
    assert tools_called_in_order("filesystem.read_text_file", "browser.navigate")(context).passed is False
    assert duration_at_most(10.0)(context).passed is False
    assert solve_rate_at_least(1.0)(context).passed is False


def test_registry_and_case_runner_support_category_grouping() -> None:
    registry = EvaluationRegistry()
    correctness_case = build_correctness_case(
        "eval.correctness.final-output",
        "Require final output",
        "Measures whether the agent produces a non-empty final answer.",
        checks=(final_output_exists(),),
    )
    tool_use_case = build_tool_use_case(
        "eval.tool-use.read-first",
        "Require file read before answering",
        "Measures whether the agent reads the file before synthesizing an answer.",
        checks=(tool_called("filesystem.read_text_file"),),
    )
    output_case = build_output_case(
        "eval.output.summary-status",
        "Require output status",
        "Measures whether the final output includes a normalized status field.",
        checks=(output_field_equals("summary.status", "ok"),),
    )

    registry.register_cases(correctness_case, tool_use_case, output_case)

    assert [case.key for case in registry.list_cases()] == [
        "eval.correctness.final-output",
        "eval.tool-use.read-first",
        "eval.output.summary-status",
    ]
    assert [case.key for case in registry.cases_for_category(CORRECTNESS_CATEGORY)] == [
        "eval.correctness.final-output"
    ]
    assert [case.key for case in registry.cases_for_category(TOOL_USE_CATEGORY)] == [
        "eval.tool-use.read-first"
    ]
    assert [case.key for case in registry.cases_for_category(OUTPUT_CATEGORY)] == [
        "eval.output.summary-status"
    ]

    result = run_evaluation_case(tool_use_case, _sample_context())
    assert result.passed is True
    assert result.pass_rate == 1.0
    assert result.metrics["solve_rate"] == pytest.approx(1.0)


def test_build_metrics_snapshot_surfaces_expected_efficiency_metrics() -> None:
    context = _sample_context()

    snapshot = build_metrics_snapshot(context)

    assert snapshot["solve_rate"] == pytest.approx(1.0)
    assert snapshot["step_efficiency_ratio"] == pytest.approx(1.0)
    assert snapshot["tool_call_efficiency_ratio"] == pytest.approx(1.0)
    assert snapshot["duration_efficiency_ratio"] == pytest.approx(8.0 / 6.5)
    assert snapshot["cost_efficiency_ratio"] is None


def test_category_builders_attach_primary_category() -> None:
    efficiency_case = build_correctness_case(
        "eval.correctness.sample",
        "Sample correctness case",
        "Measures a simple correctness behavior.",
        categories=(EFFICIENCY_CATEGORY,),
    )

    assert efficiency_case.categories == (CORRECTNESS_CATEGORY, EFFICIENCY_CATEGORY)


def test_registry_rejects_duplicate_case_keys() -> None:
    registry = EvaluationRegistry()
    case = build_correctness_case(
        "eval.correctness.unique",
        "Unique case",
        "Measures a unique behavior.",
    )

    registry.register_case(case)

    with pytest.raises(ValueError, match="already registered"):
        registry.register_case(case)
