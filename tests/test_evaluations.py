"""Tests for the minimal evaluation scaffolding layer."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from harnessiq.evaluations import (
    build_llm_judge_prompt,
    get_duration_seconds,
    get_step_count,
    get_tool_call_count,
    llm_judge,
    score_efficiency,
    uses_parallel_tool_calls,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_efficiency_scoring_reads_generic_run_shapes() -> None:
    run = SimpleNamespace(
        tool_calls=("time.lookup", "weather.lookup"),
        steps=4,
        time=7.5,
        parallel_tool_calls=True,
    )

    score = score_efficiency(
        run,
        {
            "steps": 4,
            "tool_calls": 4,
            "expected_time_seconds": 8,
        },
    )

    assert get_tool_call_count(run) == 2
    assert get_step_count(run) == 4
    assert get_duration_seconds(run) == pytest.approx(7.5)
    assert uses_parallel_tool_calls(run) is True
    assert score["step_ratio"] == pytest.approx(1.0)
    assert score["tool_call_ratio"] == pytest.approx(0.5)
    assert score["latency_ratio"] == pytest.approx(0.9375)


def test_efficiency_scoring_accepts_mapping_aliases() -> None:
    run = {
        "tool_call_count": 3,
        "cycles_completed": 5,
        "duration_seconds": 12.0,
    }
    ideal = {
        "expected_tool_calls": 6,
        "expected_step_count": 10,
        "duration_seconds": 24.0,
    }

    score = score_efficiency(run, ideal)

    assert score["step_ratio"] == pytest.approx(0.5)
    assert score["tool_call_ratio"] == pytest.approx(0.5)
    assert score["latency_ratio"] == pytest.approx(0.5)


def test_llm_judge_accepts_bool_string_and_openai_style_payloads() -> None:
    prompt = build_llm_judge_prompt("The answer is 4 PM and sunny.", "Provide the time and weather.")

    assert "Reply yes or no." in prompt
    assert llm_judge("output", "expected", judge=lambda _: True) is True
    assert llm_judge("output", "expected", judge=lambda _: "yes") is True
    assert llm_judge(
        "output",
        "expected",
        judge=lambda _: {"choices": [{"message": {"content": "Yes"}}]},
    ) is True
    assert llm_judge("output", "expected", judge=lambda _: "no") is False


def test_pytest_plugin_filters_categories_and_exposes_model_fixture(tmp_path: Path) -> None:
    (tmp_path / "conftest.py").write_text(
        "pytest_plugins = ('harnessiq.evaluations.pytest_plugin',)\n",
        encoding="utf-8",
    )
    (tmp_path / "test_evals.py").write_text(
        """
from __future__ import annotations

import pytest


@pytest.mark.eval_category("tool_use")
def test_tool_use_eval(eval_model):
    assert eval_model == "gpt-4o"


@pytest.mark.eval_category("correctness")
def test_correctness_eval():
    assert False, "category filtering should deselect this test"
""".strip(),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(tmp_path),
            "-q",
            "--eval-category",
            "tool_use",
            "--model",
            "gpt-4o",
        ],
        check=False,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "1 passed" in result.stdout
    assert "1 deselected" in result.stdout


def test_repo_eval_examples_run_as_tagged_subset() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/evals",
            "-q",
            "--eval-category",
            "tool_use",
            "--model",
            "gpt-4o",
        ],
        check=False,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "1 passed" in result.stdout
    assert "2 deselected" in result.stdout
