from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harnessiq.formalization.base import BaseFormalizationLayer
from harnessiq.formalization.criteria import (
    AndCriteria,
    ArtifactCriterion,
    CallableCriterion,
    FileCriterion,
    MetricCriterion,
    OrCriteria,
    SingleCriterion,
    StopCriteriaLayer,
)
from harnessiq.formalization.metrics import DeterministicMetricSpec, MetricsLayer
from harnessiq.shared.tools import CONTROL_MARK_COMPLETE, ToolResult


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_metrics_layer(name: str = "calls", initial: int = 0) -> MetricsLayer:
    spec = DeterministicMetricSpec(
        name=name,
        description="Total calls.",
        watch_tool_patterns=("terminal.*",),
        extract_value=lambda k, a, o: 1,
        initial_value=initial,
    )
    return MetricsLayer(metrics=[spec])


def _prepare_metrics(layer: MetricsLayer, memory_path: str) -> None:
    layer.on_agent_prepare(agent_name="agent", memory_path=memory_path)


def _mark_complete_result() -> ToolResult:
    return ToolResult(tool_key=CONTROL_MARK_COMPLETE, output={"status": "done"})


# ── allow_completion on BaseFormalizationLayer ────────────────────────────────

class BaseFormalizationLayerAllowCompletionTests(unittest.TestCase):
    """Verify that the default allow_completion returns (True, '')."""

    class _MinimalLayer(BaseFormalizationLayer):
        def _describe_contract(self):
            return "contract"
        def _describe_rules(self):
            return ()
        def _describe_configuration(self):
            return {}

    def test_default_allows_completion(self) -> None:
        layer = self._MinimalLayer()
        allowed, msg = layer.allow_completion()
        self.assertTrue(allowed)
        self.assertEqual(msg, "")


# ── MetricCriterion ───────────────────────────────────────────────────────────

class MetricCriterionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._ml = _make_metrics_layer("calls", initial=0)
        _prepare_metrics(self._ml, self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _criterion(self, op: str, target: int) -> MetricCriterion:
        return MetricCriterion(
            metric_name="calls",
            operator=op,
            target=target,
            metrics_layer=self._ml,
        )

    def test_gte_not_satisfied_initially(self) -> None:
        c = self._criterion(">=", 5)
        self.assertFalse(c.is_satisfied())

    def test_gte_satisfied_after_update(self) -> None:
        c = self._criterion(">=", 1)
        self._ml.on_tool_result(ToolResult(tool_key="terminal.run", output={}))
        self.assertTrue(c.is_satisfied())

    def test_eq_operator(self) -> None:
        c = self._criterion("==", 0)
        self.assertTrue(c.is_satisfied())

    def test_lt_operator(self) -> None:
        c = self._criterion("<", 5)
        self.assertTrue(c.is_satisfied())

    def test_ne_operator(self) -> None:
        c = self._criterion("!=", 0)
        self.assertFalse(c.is_satisfied())
        self._ml.on_tool_result(ToolResult(tool_key="terminal.run", output={}))
        self.assertTrue(c.is_satisfied())

    def test_unknown_operator_returns_false(self) -> None:
        c = MetricCriterion(
            metric_name="calls", operator="???", target=0, metrics_layer=self._ml
        )
        self.assertFalse(c.is_satisfied())

    def test_unknown_metric_returns_false(self) -> None:
        c = MetricCriterion(
            metric_name="nonexistent", operator=">=", target=0, metrics_layer=self._ml
        )
        self.assertFalse(c.is_satisfied())

    def test_progress_shows_current_and_required(self) -> None:
        c = self._criterion(">=", 10)
        progress = c.progress()
        self.assertIn("calls", progress)
        self.assertIn("10", progress)

    def test_criterion_id_format(self) -> None:
        c = self._criterion(">=", 5)
        self.assertIn("METRIC", c.criterion_id)
        self.assertIn("CALLS", c.criterion_id)


# ── FileCriterion ─────────────────────────────────────────────────────────────

class FileCriterionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._path = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _criterion(self, filename: str = "out.txt", **kwargs) -> FileCriterion:
        c = FileCriterion(
            _criterion_id="FILE-CHECK",
            _description="File must exist.",
            path=str(self._path / filename),
            **kwargs,
        )
        return c

    def test_not_satisfied_when_file_missing(self) -> None:
        c = self._criterion()
        self.assertFalse(c.is_satisfied())

    def test_satisfied_when_file_exists(self) -> None:
        (self._path / "out.txt").write_text("content")
        c = self._criterion()
        self.assertTrue(c.is_satisfied())

    def test_not_satisfied_below_min_lines(self) -> None:
        (self._path / "out.txt").write_text("line1\nline2\n")
        c = self._criterion(min_lines=10)
        self.assertFalse(c.is_satisfied())

    def test_satisfied_at_min_lines(self) -> None:
        content = "\n".join(["line"] * 10) + "\n"
        (self._path / "out.txt").write_text(content)
        c = self._criterion(min_lines=10)
        self.assertTrue(c.is_satisfied())

    def test_not_satisfied_below_min_bytes(self) -> None:
        (self._path / "out.txt").write_bytes(b"hi")
        c = self._criterion(min_bytes=1000)
        self.assertFalse(c.is_satisfied())

    def test_must_exist_false_satisfied_when_missing(self) -> None:
        c = self._criterion(must_exist=False)
        self.assertTrue(c.is_satisfied())

    def test_memory_path_template(self) -> None:
        target = self._path / "output" / "result.txt"
        target.parent.mkdir()
        target.write_text("done")
        c = FileCriterion(
            _criterion_id="X",
            _description="desc",
            path="{memory_path}/output/result.txt",
        )
        c.bind_memory_path(str(self._path))
        self.assertTrue(c.is_satisfied())

    def test_progress_not_exist(self) -> None:
        c = self._criterion()
        self.assertIn("does not exist", c.progress())

    def test_progress_shows_file_exists(self) -> None:
        (self._path / "out.txt").write_text("content")
        c = self._criterion()
        self.assertIn("exists", c.progress())


# ── CallableCriterion ─────────────────────────────────────────────────────────

class CallableCriterionTests(unittest.TestCase):
    def test_satisfied_when_callable_returns_true(self) -> None:
        c = CallableCriterion(
            _criterion_id="CUSTOM",
            _description="Custom check.",
            check=lambda: (True, "all good"),
        )
        self.assertTrue(c.is_satisfied())

    def test_not_satisfied_when_callable_returns_false(self) -> None:
        c = CallableCriterion(
            _criterion_id="CUSTOM",
            _description="Custom check.",
            check=lambda: (False, "not done yet"),
        )
        self.assertFalse(c.is_satisfied())

    def test_progress_from_callable(self) -> None:
        c = CallableCriterion(
            _criterion_id="CUSTOM",
            _description="Custom check.",
            check=lambda: (False, "score: 42/100"),
        )
        self.assertEqual(c.progress(), "score: 42/100")


# ── Expression composition ────────────────────────────────────────────────────

class SingleCriterionExpressionTests(unittest.TestCase):
    def test_satisfied_when_criterion_passes(self) -> None:
        expr = SingleCriterion(
            criterion=CallableCriterion("X", "desc", lambda: (True, "ok"))
        )
        self.assertTrue(expr.is_satisfied())
        self.assertEqual(expr.failing_criteria(), [])

    def test_not_satisfied_when_criterion_fails(self) -> None:
        c = CallableCriterion("X", "desc", lambda: (False, "not ok"))
        expr = SingleCriterion(criterion=c)
        self.assertFalse(expr.is_satisfied())
        self.assertEqual(len(expr.failing_criteria()), 1)

    def test_all_criteria_returns_single(self) -> None:
        c = CallableCriterion("X", "desc", lambda: (True, "ok"))
        expr = SingleCriterion(criterion=c)
        self.assertEqual(expr.all_criteria(), [c])


class AndCriteriaTests(unittest.TestCase):
    def _make(self, *results: bool) -> AndCriteria:
        children = [
            SingleCriterion(CallableCriterion(f"C{i}", "desc", (lambda r: lambda: (r, ""))(r)))
            for i, r in enumerate(results)
        ]
        return AndCriteria(children=children)

    def test_satisfied_when_all_pass(self) -> None:
        self.assertTrue(self._make(True, True, True).is_satisfied())

    def test_not_satisfied_when_any_fails(self) -> None:
        self.assertFalse(self._make(True, False, True).is_satisfied())

    def test_failing_criteria_lists_all_failing(self) -> None:
        expr = self._make(True, False, False)
        failing = expr.failing_criteria()
        self.assertEqual(len(failing), 2)

    def test_all_criteria_returns_all(self) -> None:
        expr = self._make(True, False)
        self.assertEqual(len(expr.all_criteria()), 2)


class OrCriteriaTests(unittest.TestCase):
    def _make(self, *results: bool) -> OrCriteria:
        children = [
            SingleCriterion(CallableCriterion(f"C{i}", "desc", (lambda r: lambda: (r, ""))(r)))
            for i, r in enumerate(results)
        ]
        return OrCriteria(children=children)

    def test_satisfied_when_any_passes(self) -> None:
        self.assertTrue(self._make(False, True, False).is_satisfied())

    def test_not_satisfied_when_all_fail(self) -> None:
        self.assertFalse(self._make(False, False).is_satisfied())

    def test_failing_criteria_empty_when_satisfied(self) -> None:
        expr = self._make(True, False)
        self.assertEqual(expr.failing_criteria(), [])

    def test_failing_criteria_lists_all_when_not_satisfied(self) -> None:
        expr = self._make(False, False)
        failing = expr.failing_criteria()
        self.assertEqual(len(failing), 2)

    def test_nested_and_or(self) -> None:
        c_true = SingleCriterion(CallableCriterion("T", "desc", lambda: (True, "ok")))
        c_false = SingleCriterion(CallableCriterion("F", "desc", lambda: (False, "no")))
        expr = AndCriteria(children=[
            c_true,
            OrCriteria(children=[c_false, c_true]),
        ])
        self.assertTrue(expr.is_satisfied())


# ── StopCriteriaLayer enforcement ─────────────────────────────────────────────

class StopCriteriaLayerMarkCompleteTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._ml = _make_metrics_layer("calls", initial=0)
        _prepare_metrics(self._ml, self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _layer(self, target: int) -> StopCriteriaLayer:
        expr = SingleCriterion(
            MetricCriterion(
                metric_name="calls",
                operator=">=",
                target=target,
                metrics_layer=self._ml,
            )
        )
        return StopCriteriaLayer(expression=expr)

    def test_mark_complete_passes_when_satisfied(self) -> None:
        # Satisfy the criterion first.
        self._ml.on_tool_result(ToolResult(tool_key="terminal.run", output={}))
        layer = self._layer(target=1)
        result = layer.on_tool_result(_mark_complete_result())
        # When satisfied the original result is returned unchanged.
        self.assertEqual(result.tool_key, CONTROL_MARK_COMPLETE)
        self.assertNotIn("error", result.output)

    def test_mark_complete_blocked_when_not_satisfied(self) -> None:
        layer = self._layer(target=5)
        result = layer.on_tool_result(_mark_complete_result())
        self.assertIn("error", result.output)
        self.assertIn("Completion blocked", result.output["error"])

    def test_non_mark_complete_tool_passes_through(self) -> None:
        layer = self._layer(target=5)
        result = ToolResult(tool_key="terminal.run", output={"ok": True})
        returned = layer.on_tool_result(result)
        self.assertIs(returned, result)

    def test_error_message_mentions_criterion_id(self) -> None:
        layer = self._layer(target=5)
        result = layer.on_tool_result(_mark_complete_result())
        self.assertIn("METRIC-CALLS", result.output["error"])

    def test_error_message_includes_progress(self) -> None:
        layer = self._layer(target=5)
        result = layer.on_tool_result(_mark_complete_result())
        self.assertIn("current=0", result.output["error"])


class StopCriteriaLayerAllowCompletionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._ml = _make_metrics_layer("calls", initial=0)
        _prepare_metrics(self._ml, self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _layer(self, target: int) -> StopCriteriaLayer:
        expr = SingleCriterion(
            MetricCriterion(
                metric_name="calls",
                operator=">=",
                target=target,
                metrics_layer=self._ml,
            )
        )
        return StopCriteriaLayer(expression=expr)

    def test_allows_when_satisfied(self) -> None:
        self._ml.on_tool_result(ToolResult(tool_key="terminal.run", output={}))
        layer = self._layer(target=1)
        allowed, msg = layer.allow_completion()
        self.assertTrue(allowed)
        self.assertEqual(msg, "")

    def test_blocks_when_not_satisfied(self) -> None:
        layer = self._layer(target=5)
        allowed, msg = layer.allow_completion()
        self.assertFalse(allowed)
        self.assertIn("Completion blocked", msg)

    def test_block_message_includes_criterion_description(self) -> None:
        layer = self._layer(target=5)
        _, msg = layer.allow_completion()
        self.assertIn("calls", msg)


# ── StopCriteriaLayer describe() and parameter sections ──────────────────────

class StopCriteriaLayerDescribeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._ml = _make_metrics_layer("calls", initial=0)
        _prepare_metrics(self._ml, self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _layer(self) -> StopCriteriaLayer:
        return StopCriteriaLayer(
            expression=SingleCriterion(
                MetricCriterion(
                    metric_name="calls",
                    operator=">=",
                    target=1,
                    metrics_layer=self._ml,
                )
            )
        )

    def test_layer_id(self) -> None:
        self.assertEqual(self._layer().layer_id, "StopCriteriaLayer")

    def test_describe_rules_present(self) -> None:
        rules = self._layer().describe().rules
        rule_ids = [r.rule_id for r in rules]
        self.assertIn("STOP-GATE-MARK-COMPLETE", rule_ids)
        self.assertIn("STOP-GATE-SHOULD-CONTINUE", rule_ids)

    def test_parameter_section_shows_criteria(self) -> None:
        sections = self._layer().get_parameter_sections()
        stop_section = next(s for s in sections if s.title == "Stop Criteria")
        self.assertIn("METRIC-CALLS", stop_section.content)

    def test_parameter_section_shows_satisfied_status(self) -> None:
        self._ml.on_tool_result(ToolResult(tool_key="terminal.run", output={}))
        sections = self._layer().get_parameter_sections()
        stop_section = next(s for s in sections if s.title == "Stop Criteria")
        self.assertIn("satisfied", stop_section.content)


if __name__ == "__main__":
    unittest.main()
