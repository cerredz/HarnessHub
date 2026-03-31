from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from harnessiq.formalization.metrics import (
    DeterministicMetricSpec,
    MetricsLayer,
    ModelReportedMetricSpec,
)
from harnessiq.formalization.metrics.store import MetricStore
from harnessiq.shared.tools import ToolResult


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tool_result(key: str, output: object) -> ToolResult:
    return ToolResult(tool_key=key, output=output)


def _make_deterministic(
    name: str = "calls",
    description: str = "Total calls.",
    patterns: tuple[str, ...] = ("terminal.*",),
    extractor=None,
    aggregation: str = "increment",
    initial_value: object = 0,
    visible: bool = True,
) -> DeterministicMetricSpec:
    if extractor is None:
        extractor = lambda key, args, out: 1
    return DeterministicMetricSpec(
        name=name,
        description=description,
        watch_tool_patterns=patterns,
        extract_value=extractor,
        aggregation=aggregation,
        initial_value=initial_value,
        visible=visible,
    )


def _make_model_reported(
    name: str = "confidence",
    description: str = "Confidence score.",
    value_type: str = "float",
    initial_value: object = 0.0,
    visible: bool = True,
) -> ModelReportedMetricSpec:
    return ModelReportedMetricSpec(
        name=name,
        description=description,
        value_type=value_type,
        initial_value=initial_value,
        visible=visible,
    )


# ── Spec validation ───────────────────────────────────────────────────────────

class DeterministicMetricSpecTests(unittest.TestCase):
    def test_valid_spec(self) -> None:
        spec = _make_deterministic()
        self.assertEqual(spec.name, "calls")
        self.assertEqual(spec.aggregation, "increment")

    def test_blank_name_raises(self) -> None:
        with self.assertRaises(ValueError):
            _make_deterministic(name="  ")

    def test_blank_description_raises(self) -> None:
        with self.assertRaises(ValueError):
            _make_deterministic(description="  ")

    def test_empty_patterns_raises(self) -> None:
        with self.assertRaises(ValueError):
            _make_deterministic(patterns=())

    def test_non_callable_extract_value_raises(self) -> None:
        with self.assertRaises((ValueError, TypeError)):
            DeterministicMetricSpec(
                name="x",
                description="x",
                watch_tool_patterns=("a",),
                extract_value="not_callable",  # type: ignore[arg-type]
            )

    def test_spec_is_frozen(self) -> None:
        spec = _make_deterministic()
        with self.assertRaises((AttributeError, TypeError)):
            spec.name = "other"  # type: ignore[misc]


class ModelReportedMetricSpecTests(unittest.TestCase):
    def test_valid_spec(self) -> None:
        spec = _make_model_reported()
        self.assertEqual(spec.name, "confidence")
        self.assertEqual(spec.aggregation, "set")
        self.assertEqual(spec.value_type, "float")

    def test_blank_name_raises(self) -> None:
        with self.assertRaises(ValueError):
            _make_model_reported(name="  ")

    def test_blank_description_raises(self) -> None:
        with self.assertRaises(ValueError):
            _make_model_reported(description="  ")


# ── MetricStore ───────────────────────────────────────────────────────────────

class MetricStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._path = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_get_returns_default_for_unknown_key(self) -> None:
        store = MetricStore(self._path)
        self.assertEqual(store.get("missing", 99), 99)

    def test_set_and_get(self) -> None:
        store = MetricStore(self._path)
        store.set("x", 42)
        self.assertEqual(store.get("x", 0), 42)

    def test_values_persist_across_instances(self) -> None:
        store1 = MetricStore(self._path)
        store1.set("y", 100)
        store2 = MetricStore(self._path)
        self.assertEqual(store2.get("y", 0), 100)

    def test_increment_aggregation(self) -> None:
        store = MetricStore(self._path)
        store.apply_aggregation("n", 5, "increment", 0)
        store.apply_aggregation("n", 3, "increment", 0)
        self.assertEqual(store.get("n", 0), 8)

    def test_set_aggregation_replaces(self) -> None:
        store = MetricStore(self._path)
        store.apply_aggregation("n", 5, "set", 0)
        store.apply_aggregation("n", 3, "set", 0)
        self.assertEqual(store.get("n", 0), 3)

    def test_max_aggregation(self) -> None:
        store = MetricStore(self._path)
        store.apply_aggregation("n", 5, "max", 0)
        store.apply_aggregation("n", 3, "max", 0)
        self.assertEqual(store.get("n", 0), 5)

    def test_min_aggregation(self) -> None:
        store = MetricStore(self._path)
        # Seed with a high initial value so min tracking is meaningful.
        store.set("n", 100)
        store.apply_aggregation("n", 5, "min", 100)
        store.apply_aggregation("n", 3, "min", 100)
        self.assertEqual(store.get("n", 0), 3)

    def test_last_aggregation_is_alias_for_set(self) -> None:
        store = MetricStore(self._path)
        store.apply_aggregation("n", 10, "last", 0)
        store.apply_aggregation("n", 7, "last", 0)
        self.assertEqual(store.get("n", 0), 7)

    def test_all_returns_snapshot(self) -> None:
        store = MetricStore(self._path)
        store.set("a", 1)
        store.set("b", 2)
        self.assertEqual(store.all(), {"a": 1, "b": 2})

    def test_json_file_written(self) -> None:
        store = MetricStore(self._path)
        store.set("x", 123)
        data = json.loads((self._path / "metrics_store.json").read_text())
        self.assertEqual(data["x"], 123)


# ── MetricsLayer construction ──────────────────────────────────────────────────

class MetricsLayerConstructionTests(unittest.TestCase):
    def test_empty_metrics_raises(self) -> None:
        with self.assertRaises(ValueError):
            MetricsLayer(metrics=[])

    def test_duplicate_name_raises(self) -> None:
        with self.assertRaises(ValueError):
            MetricsLayer(metrics=[_make_deterministic(name="x"), _make_deterministic(name="x")])

    def test_layer_id(self) -> None:
        layer = MetricsLayer(metrics=[_make_deterministic()])
        self.assertEqual(layer.layer_id, "MetricsLayer")

    def test_mixed_metrics_accepted(self) -> None:
        layer = MetricsLayer(
            metrics=[_make_deterministic(name="calls"), _make_model_reported(name="confidence")]
        )
        self.assertIsNotNone(layer)


# ── MetricsLayer lifecycle ────────────────────────────────────────────────────

class MetricsLayerLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._memory_path = self._tmpdir.name

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _prepare(self, layer: MetricsLayer) -> None:
        layer.on_agent_prepare(agent_name="test-agent", memory_path=self._memory_path)

    def test_get_value_returns_none_before_prepare(self) -> None:
        layer = MetricsLayer(metrics=[_make_deterministic(name="x", initial_value=0)])
        self.assertIsNone(layer.get_value("x"))

    def test_get_value_returns_initial_after_prepare(self) -> None:
        layer = MetricsLayer(metrics=[_make_deterministic(name="x", initial_value=5)])
        self._prepare(layer)
        self.assertEqual(layer.get_value("x"), 5)

    def test_get_value_returns_none_for_unknown_metric(self) -> None:
        layer = MetricsLayer(metrics=[_make_deterministic(name="x")])
        self._prepare(layer)
        self.assertIsNone(layer.get_value("unknown"))

    def test_all_values_after_prepare(self) -> None:
        layer = MetricsLayer(
            metrics=[
                _make_deterministic(name="a", initial_value=1),
                _make_model_reported(name="b", initial_value=0.0),
            ]
        )
        self._prepare(layer)
        vals = layer.all_values()
        self.assertEqual(vals["a"], 1)
        self.assertEqual(vals["b"], 0.0)


# ── Deterministic metric tracking via on_tool_result ──────────────────────────

class MetricsLayerDeterministicTrackingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._memory_path = self._tmpdir.name

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _make_and_prepare(self, spec: DeterministicMetricSpec) -> MetricsLayer:
        layer = MetricsLayer(metrics=[spec])
        layer.on_agent_prepare(agent_name="agent", memory_path=self._memory_path)
        return layer

    def test_matching_tool_key_updates_metric(self) -> None:
        spec = _make_deterministic(
            name="calls",
            patterns=("terminal.*",),
            extractor=lambda k, a, o: 1,
        )
        layer = self._make_and_prepare(spec)
        layer.on_tool_result(_tool_result("terminal.run", {}))
        self.assertEqual(layer.get_value("calls"), 1)

    def test_non_matching_tool_key_skips(self) -> None:
        spec = _make_deterministic(
            name="calls",
            patterns=("terminal.*",),
            extractor=lambda k, a, o: 1,
        )
        layer = self._make_and_prepare(spec)
        layer.on_tool_result(_tool_result("artifact.write_json", {}))
        self.assertEqual(layer.get_value("calls"), 0)

    def test_extractor_returning_none_skips_update(self) -> None:
        spec = _make_deterministic(
            name="calls",
            patterns=("terminal.*",),
            extractor=lambda k, a, o: None,
        )
        layer = self._make_and_prepare(spec)
        layer.on_tool_result(_tool_result("terminal.run", {}))
        self.assertEqual(layer.get_value("calls"), 0)

    def test_extractor_exception_skips_update(self) -> None:
        def bad_extractor(k, a, o):
            raise RuntimeError("boom")
        spec = _make_deterministic(
            name="calls",
            patterns=("terminal.*",),
            extractor=bad_extractor,
        )
        layer = self._make_and_prepare(spec)
        layer.on_tool_result(_tool_result("terminal.run", {}))
        self.assertEqual(layer.get_value("calls"), 0)

    def test_increment_aggregation_accumulates(self) -> None:
        spec = _make_deterministic(
            name="calls",
            patterns=("terminal.*",),
            extractor=lambda k, a, o: 1,
            aggregation="increment",
        )
        layer = self._make_and_prepare(spec)
        layer.on_tool_result(_tool_result("terminal.run", {}))
        layer.on_tool_result(_tool_result("terminal.run", {}))
        layer.on_tool_result(_tool_result("terminal.run", {}))
        self.assertEqual(layer.get_value("calls"), 3)

    def test_on_tool_result_returns_result_unchanged(self) -> None:
        spec = _make_deterministic(name="x", patterns=("a.*",), extractor=lambda k, a, o: 1)
        layer = self._make_and_prepare(spec)
        result = _tool_result("a.run", {"payload": 42})
        returned = layer.on_tool_result(result)
        self.assertIs(returned, result)

    def test_wildcard_pattern_matches_multiple_tools(self) -> None:
        spec = _make_deterministic(
            name="all_calls",
            patterns=("*",),
            extractor=lambda k, a, o: 1,
        )
        layer = self._make_and_prepare(spec)
        layer.on_tool_result(_tool_result("terminal.run", {}))
        layer.on_tool_result(_tool_result("artifact.write", {}))
        self.assertEqual(layer.get_value("all_calls"), 2)


# ── Model-reported metrics via handle_model_report ───────────────────────────

class MetricsLayerModelReportedTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._memory_path = self._tmpdir.name

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _make_and_prepare(self, spec: ModelReportedMetricSpec) -> MetricsLayer:
        layer = MetricsLayer(metrics=[spec])
        layer.on_agent_prepare(agent_name="agent", memory_path=self._memory_path)
        return layer

    def test_report_float_metric(self) -> None:
        spec = _make_model_reported(name="confidence", value_type="float", initial_value=0.0)
        layer = self._make_and_prepare(spec)
        result = layer.handle_model_report("confidence", 0.85)
        self.assertEqual(result["status"], "recorded")
        self.assertAlmostEqual(result["value"], 0.85)
        self.assertAlmostEqual(layer.get_value("confidence"), 0.85)

    def test_report_int_metric(self) -> None:
        spec = _make_model_reported(name="score", value_type="int", initial_value=0)
        layer = self._make_and_prepare(spec)
        result = layer.handle_model_report("score", 7)
        self.assertEqual(result["status"], "recorded")
        self.assertEqual(result["value"], 7)

    def test_report_string_metric(self) -> None:
        spec = _make_model_reported(name="phase", value_type="string", initial_value="")
        layer = self._make_and_prepare(spec)
        result = layer.handle_model_report("phase", "research")
        self.assertEqual(result["status"], "recorded")

    def test_wrong_type_returns_error(self) -> None:
        spec = _make_model_reported(name="confidence", value_type="float", initial_value=0.0)
        layer = self._make_and_prepare(spec)
        result = layer.handle_model_report("confidence", "not_a_float")
        self.assertIn("error", result)

    def test_unknown_metric_returns_error(self) -> None:
        spec = _make_model_reported(name="confidence")
        layer = self._make_and_prepare(spec)
        result = layer.handle_model_report("nonexistent", 0.5)
        self.assertIn("error", result)

    def test_report_deterministic_metric_returns_error(self) -> None:
        det = _make_deterministic(name="calls")
        mr = _make_model_reported(name="confidence")
        layer = MetricsLayer(metrics=[det, mr])
        layer.on_agent_prepare(agent_name="agent", memory_path=self._memory_path)
        result = layer.handle_model_report("calls", 1)
        self.assertIn("error", result)


# ── metrics.report tool ───────────────────────────────────────────────────────

class MetricsLayerToolTests(unittest.TestCase):
    def test_no_tools_when_no_model_reported(self) -> None:
        layer = MetricsLayer(metrics=[_make_deterministic()])
        tools = layer.get_formalization_tools()
        self.assertEqual(len(tools), 0)

    def test_report_tool_contributed_when_model_reported_present(self) -> None:
        from harnessiq.shared.tools import RegisteredTool
        layer = MetricsLayer(metrics=[_make_model_reported()])
        tools = layer.get_formalization_tools()
        self.assertEqual(len(tools), 1)
        self.assertIsInstance(tools[0], RegisteredTool)
        self.assertEqual(tools[0].definition.key, "metrics.report")


# ── Parameter sections ────────────────────────────────────────────────────────

class MetricsLayerParameterSectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._memory_path = self._tmpdir.name

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_no_metrics_section_before_prepare(self) -> None:
        layer = MetricsLayer(metrics=[_make_deterministic(visible=True)])
        sections = layer.get_parameter_sections()
        titles = [s.title for s in sections]
        self.assertNotIn("Metrics", titles)

    def test_metrics_section_after_prepare(self) -> None:
        layer = MetricsLayer(metrics=[_make_deterministic(visible=True)])
        layer.on_agent_prepare(agent_name="agent", memory_path=self._memory_path)
        sections = layer.get_parameter_sections()
        titles = [s.title for s in sections]
        self.assertIn("Metrics", titles)

    def test_invisible_metric_excluded(self) -> None:
        layer = MetricsLayer(metrics=[_make_deterministic(name="hidden", visible=False)])
        layer.on_agent_prepare(agent_name="agent", memory_path=self._memory_path)
        sections = layer.get_parameter_sections()
        titles = [s.title for s in sections]
        self.assertNotIn("Metrics", titles)

    def test_metrics_section_content_includes_unit(self) -> None:
        spec = DeterministicMetricSpec(
            name="git_commits",
            description="Total commits.",
            watch_tool_patterns=("terminal.*",),
            extract_value=lambda k, a, o: 1,
            unit="commits",
        )
        layer = MetricsLayer(metrics=[spec])
        layer.on_agent_prepare(agent_name="agent", memory_path=self._memory_path)
        sections = layer.get_parameter_sections()
        metrics_section = next(s for s in sections if s.title == "Metrics")
        self.assertIn("commits", metrics_section.content)


# ── describe() output ─────────────────────────────────────────────────────────

class MetricsLayerDescribeTests(unittest.TestCase):
    def test_describe_identity_mentions_metric_names(self) -> None:
        layer = MetricsLayer(
            metrics=[
                _make_deterministic(name="calls"),
                _make_model_reported(name="confidence"),
            ]
        )
        desc = layer.describe()
        self.assertIn("calls", desc.identity)
        self.assertIn("confidence", desc.identity)

    def test_describe_rules_for_deterministic(self) -> None:
        layer = MetricsLayer(metrics=[_make_deterministic(name="calls")])
        rules = layer.describe().rules
        rule_ids = [r.rule_id for r in rules]
        self.assertIn("METRIC-TRACK-CALLS", rule_ids)

    def test_describe_rules_for_model_reported(self) -> None:
        layer = MetricsLayer(metrics=[_make_model_reported(name="confidence")])
        rules = layer.describe().rules
        rule_ids = [r.rule_id for r in rules]
        self.assertIn("METRIC-REPORT-TOOL", rule_ids)


if __name__ == "__main__":
    unittest.main()
