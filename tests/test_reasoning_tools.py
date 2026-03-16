"""Tests for the reasoning lens tool family."""
"""Tests for the injectable reasoning tools."""

from __future__ import annotations

import unittest

from harnessiq.shared.tools import (
    REASONING_ABDUCTIVE_REASONING,
    REASONING_ANALOGY_GENERATION,
    REASONING_ASSUMPTION_SURFACING,
    REASONING_BACKCASTING,
    REASONING_BACKWARD_CHAINING,
    REASONING_BIAS_DETECTION,
    REASONING_BLINDSPOT_CHECK,
    REASONING_BOTTLENECK_IDENTIFICATION,
    REASONING_BUTTERFLY_EFFECT_TRACE,
    REASONING_CONFIDENCE_CALIBRATION,
    REASONING_CONSTRAINT_MAPPING,
    REASONING_COST_BENEFIT_ANALYSIS,
    REASONING_CYNEFIN_CATEGORIZATION,
    REASONING_DEVILS_ADVOCATE,
    REASONING_DIALECTICAL_REASONING,
    REASONING_DIVIDE_AND_CONQUER,
    REASONING_FACT_CHECKING,
    REASONING_FALSIFICATION_TEST,
    REASONING_FEEDBACK_LOOP_IDENTIFICATION,
    REASONING_FIRST_PRINCIPLES,
    REASONING_FORWARD_CHAINING,
    REASONING_GRAPH_OF_THOUGHTS,
    REASONING_HYPOTHESIS_GENERATION,
    REASONING_LATERAL_THINKING,
    REASONING_MEANS_END_ANALYSIS,
    REASONING_MORPHOLOGICAL_ANALYSIS,
    REASONING_NETWORK_MAPPING,
    REASONING_PARETO_ANALYSIS,
    REASONING_PERSONA_ADOPTION,
    REASONING_PLAN_AND_SOLVE,
    REASONING_POST_MORTEM,
    REASONING_PRE_MORTEM,
    REASONING_PROVOCATION_OPERATION,
    REASONING_RED_TEAMING,
    REASONING_ROLE_STORMING,
    REASONING_ROOT_CAUSE_ANALYSIS,
    REASONING_SCAMPER,
    REASONING_SCENARIO_PLANNING,
    REASONING_SECOND_ORDER_EFFECTS,
    REASONING_SELF_CRITIQUE,
    REASONING_SIX_THINKING_HATS,
    REASONING_STAKEHOLDER_ANALYSIS,
    REASONING_STEELMANNING,
    REASONING_STEP_BY_STEP,
    REASONING_SWOT_ANALYSIS,
    REASONING_TRADEOFF_EVALUATION,
    REASONING_TREE_OF_THOUGHTS,
    REASONING_TREND_EXTRAPOLATION,
    REASONING_VARIABLE_ISOLATION,
    REASONING_WORST_IDEA_GENERATION,
)
from harnessiq.tools import create_builtin_registry
from harnessiq.tools.reasoning import create_reasoning_tools


_ALL_KEYS = [
    REASONING_ABDUCTIVE_REASONING,
    REASONING_ANALOGY_GENERATION,
    REASONING_ASSUMPTION_SURFACING,
    REASONING_BACKCASTING,
    REASONING_BACKWARD_CHAINING,
    REASONING_BIAS_DETECTION,
    REASONING_BLINDSPOT_CHECK,
    REASONING_BOTTLENECK_IDENTIFICATION,
    REASONING_BUTTERFLY_EFFECT_TRACE,
    REASONING_CONFIDENCE_CALIBRATION,
    REASONING_CONSTRAINT_MAPPING,
    REASONING_COST_BENEFIT_ANALYSIS,
    REASONING_CYNEFIN_CATEGORIZATION,
    REASONING_DEVILS_ADVOCATE,
    REASONING_DIALECTICAL_REASONING,
    REASONING_DIVIDE_AND_CONQUER,
    REASONING_FACT_CHECKING,
    REASONING_FALSIFICATION_TEST,
    REASONING_FEEDBACK_LOOP_IDENTIFICATION,
    REASONING_FIRST_PRINCIPLES,
    REASONING_FORWARD_CHAINING,
    REASONING_GRAPH_OF_THOUGHTS,
    REASONING_HYPOTHESIS_GENERATION,
    REASONING_LATERAL_THINKING,
    REASONING_MEANS_END_ANALYSIS,
    REASONING_MORPHOLOGICAL_ANALYSIS,
    REASONING_NETWORK_MAPPING,
    REASONING_PARETO_ANALYSIS,
    REASONING_PERSONA_ADOPTION,
    REASONING_PLAN_AND_SOLVE,
    REASONING_POST_MORTEM,
    REASONING_PRE_MORTEM,
    REASONING_PROVOCATION_OPERATION,
    REASONING_RED_TEAMING,
    REASONING_ROLE_STORMING,
    REASONING_ROOT_CAUSE_ANALYSIS,
    REASONING_SCAMPER,
    REASONING_SCENARIO_PLANNING,
    REASONING_SECOND_ORDER_EFFECTS,
    REASONING_SELF_CRITIQUE,
    REASONING_SIX_THINKING_HATS,
    REASONING_STAKEHOLDER_ANALYSIS,
    REASONING_STEELMANNING,
    REASONING_STEP_BY_STEP,
    REASONING_SWOT_ANALYSIS,
    REASONING_TRADEOFF_EVALUATION,
    REASONING_TREE_OF_THOUGHTS,
    REASONING_TREND_EXTRAPOLATION,
    REASONING_VARIABLE_ISOLATION,
    REASONING_WORST_IDEA_GENERATION,
]


class ReasoningToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tools = create_reasoning_tools()
        self.tool_map = {t.key: t for t in self.tools}
        self.registry = create_builtin_registry()

    # ------------------------------------------------------------------
    # Structural invariants
    # ------------------------------------------------------------------

    def test_create_reasoning_tools_returns_50_tools(self) -> None:
        self.assertEqual(len(self.tools), 50)

    def test_all_tool_keys_have_reasoning_prefix(self) -> None:
        non_prefixed = [t.key for t in self.tools if not t.key.startswith("reasoning.")]
        self.assertEqual(non_prefixed, [])

    def test_all_tools_require_intent(self) -> None:
        for tool in self.tools:
            required = tool.definition.input_schema.get("required", [])
            self.assertIn("intent", required, msg=f"Tool '{tool.key}' missing 'intent' in required")

    def test_all_tools_disallow_additional_properties(self) -> None:
        for tool in self.tools:
            self.assertIs(
                tool.definition.input_schema.get("additionalProperties"),
                False,
                msg=f"Tool '{tool.key}' must have additionalProperties=False",
            )

    def test_all_tool_keys_are_unique(self) -> None:
        keys = [t.key for t in self.tools]
        self.assertEqual(len(keys), len(set(keys)))

    def test_all_50_expected_keys_are_present(self) -> None:
        registered_keys = set(t.key for t in self.tools)
        for key in _ALL_KEYS:
            self.assertIn(key, registered_keys, msg=f"Expected key '{key}' not registered")

    # ------------------------------------------------------------------
    # Handler output shape — every tool, intent-only invocation
    # ------------------------------------------------------------------

    def test_all_tools_return_lens_and_reasoning_prompt_on_intent_only_call(self) -> None:
        for tool in self.tools:
            result = tool.handler({"intent": "test intent"})
            self.assertIsInstance(result, dict, msg=f"Tool '{tool.key}' handler did not return a dict")
            self.assertIn("lens", result, msg=f"Tool '{tool.key}' missing 'lens' key in output")
            self.assertIn("reasoning_prompt", result, msg=f"Tool '{tool.key}' missing 'reasoning_prompt' key in output")
            self.assertIsInstance(result["lens"], str, msg=f"Tool '{tool.key}' lens is not a string")
            self.assertIsInstance(result["reasoning_prompt"], str, msg=f"Tool '{tool.key}' reasoning_prompt is not a string")
            self.assertTrue(result["lens"], msg=f"Tool '{tool.key}' lens is empty")
            self.assertTrue(result["reasoning_prompt"], msg=f"Tool '{tool.key}' reasoning_prompt is empty")

    def test_reasoning_prompt_contains_intent_for_all_tools(self) -> None:
        test_intent = "unique-test-intent-string-xyz"
        for tool in self.tools:
            result = tool.handler({"intent": test_intent})
            self.assertIn(
                test_intent,
                result["reasoning_prompt"],
                msg=f"Tool '{tool.key}' reasoning_prompt does not contain the intent",
            )

    def test_all_lens_names_are_unique(self) -> None:
        lens_names = [tool.handler({"intent": "x"})["lens"] for tool in self.tools]
        self.assertEqual(len(lens_names), len(set(lens_names)))

    # ------------------------------------------------------------------
    # Missing required argument raises KeyError
    # ------------------------------------------------------------------

    def test_missing_intent_raises_key_error(self) -> None:
        for tool in self.tools:
            with self.assertRaises((KeyError, ValueError), msg=f"Tool '{tool.key}' did not raise on missing intent"):
                tool.handler({})

    # ------------------------------------------------------------------
    # Category 1 — Core Logical & Sequential
    # ------------------------------------------------------------------

    def test_step_by_step_high_granularity_reflected_in_prompt(self) -> None:
        result = self.tool_map[REASONING_STEP_BY_STEP].handler(
            {"intent": "deploy a microservice", "granularity": "high"}
        )
        self.assertIn("high", result["reasoning_prompt"])
        self.assertIn("micro-action", result["reasoning_prompt"])

    def test_step_by_step_low_granularity_reflected_in_prompt(self) -> None:
        result = self.tool_map[REASONING_STEP_BY_STEP].handler(
            {"intent": "deploy a microservice", "granularity": "low"}
        )
        self.assertIn("low", result["reasoning_prompt"])
        self.assertIn("major phases", result["reasoning_prompt"])

    def test_tree_of_thoughts_branch_factor_in_prompt(self) -> None:
        result = self.tool_map[REASONING_TREE_OF_THOUGHTS].handler(
            {"intent": "choose architecture", "branch_factor": 5, "depth": 3}
        )
        self.assertIn("5", result["reasoning_prompt"])
        self.assertIn("3", result["reasoning_prompt"])

    def test_forward_chaining_starting_facts_in_prompt(self) -> None:
        result = self.tool_map[REASONING_FORWARD_CHAINING].handler(
            {"intent": "close the deal", "starting_facts": ["prospect showed interest", "budget confirmed"]}
        )
        self.assertIn("prospect showed interest", result["reasoning_prompt"])

    def test_backward_chaining_target_goal_in_prompt(self) -> None:
        result = self.tool_map[REASONING_BACKWARD_CHAINING].handler(
            {"intent": "win the account", "target_goal": "signed contract in hand"}
        )
        self.assertIn("signed contract in hand", result["reasoning_prompt"])

    def test_plan_and_solve_milestone_count_in_prompt(self) -> None:
        result = self.tool_map[REASONING_PLAN_AND_SOLVE].handler(
            {"intent": "launch a product", "milestones": 7}
        )
        self.assertIn("7", result["reasoning_prompt"])

    def test_divide_and_conquer_sub_problem_count_in_prompt(self) -> None:
        result = self.tool_map[REASONING_DIVIDE_AND_CONQUER].handler(
            {"intent": "build a data pipeline", "sub_problem_count": 5}
        )
        self.assertIn("5", result["reasoning_prompt"])

    # ------------------------------------------------------------------
    # Category 2 — Analytical & Deconstructive
    # ------------------------------------------------------------------

    def test_root_cause_analysis_fishbone_methodology_in_prompt(self) -> None:
        result = self.tool_map[REASONING_ROOT_CAUSE_ANALYSIS].handler(
            {"intent": "high error rate", "methodology": "fishbone"}
        )
        self.assertIn("fishbone", result["reasoning_prompt"].lower())
        self.assertIn("Ishikawa", result["reasoning_prompt"])

    def test_root_cause_analysis_five_whys_is_default(self) -> None:
        result = self.tool_map[REASONING_ROOT_CAUSE_ANALYSIS].handler({"intent": "service degradation"})
        self.assertIn("5 Whys", result["reasoning_prompt"])

    def test_assumption_surfacing_strictness_in_prompt(self) -> None:
        result = self.tool_map[REASONING_ASSUMPTION_SURFACING].handler(
            {"intent": "expand to new market", "strictness": 0.9}
        )
        self.assertIn("0.9", result["reasoning_prompt"])

    def test_pareto_analysis_apply_80_20_rule_false(self) -> None:
        result = self.tool_map[REASONING_PARETO_ANALYSIS].handler(
            {"intent": "identify top bugs", "apply_80_20_rule": False}
        )
        self.assertIn("without strictly enforcing the 80/20 threshold", result["reasoning_prompt"])

    def test_pareto_analysis_apply_80_20_rule_true_is_default(self) -> None:
        result = self.tool_map[REASONING_PARETO_ANALYSIS].handler({"intent": "identify top bugs"})
        self.assertIn("80/20", result["reasoning_prompt"])

    def test_variable_isolation_target_variable_in_prompt(self) -> None:
        result = self.tool_map[REASONING_VARIABLE_ISOLATION].handler(
            {"intent": "evaluate ad performance", "target_variable": "click-through rate"}
        )
        self.assertIn("click-through rate", result["reasoning_prompt"])

    # ------------------------------------------------------------------
    # Category 3 — Perspective & Adversarial
    # ------------------------------------------------------------------

    def test_devils_advocate_high_aggression_in_prompt(self) -> None:
        result = self.tool_map[REASONING_DEVILS_ADVOCATE].handler(
            {"intent": "this plan is solid", "aggression_level": 9}
        )
        self.assertIn("9", result["reasoning_prompt"])
        self.assertIn("ruthless", result["reasoning_prompt"])

    def test_devils_advocate_low_aggression_in_prompt(self) -> None:
        result = self.tool_map[REASONING_DEVILS_ADVOCATE].handler(
            {"intent": "this plan is solid", "aggression_level": 2}
        )
        self.assertIn("gentle", result["reasoning_prompt"])

    def test_six_thinking_hats_all_colors_produce_distinct_prompts(self) -> None:
        colors = ["red", "white", "black", "yellow", "green", "blue"]
        prompts = set()
        for color in colors:
            result = self.tool_map[REASONING_SIX_THINKING_HATS].handler(
                {"intent": "launch new feature", "hat_color": color}
            )
            self.assertIn(color, result["reasoning_prompt"])
            prompts.add(result["reasoning_prompt"])
        self.assertEqual(len(prompts), 6, "All six hat colors should produce distinct prompts")

    def test_steelmanning_empathy_level_in_prompt(self) -> None:
        result = self.tool_map[REASONING_STEELMANNING].handler(
            {"intent": "opposing argument", "empathy_level": 1.0}
        )
        self.assertIn("1.0", result["reasoning_prompt"])

    def test_red_teaming_attack_vectors_in_prompt(self) -> None:
        result = self.tool_map[REASONING_RED_TEAMING].handler(
            {"intent": "secure the API", "attack_vectors": ["SQL injection", "auth bypass"]}
        )
        self.assertIn("SQL injection", result["reasoning_prompt"])
        self.assertIn("auth bypass", result["reasoning_prompt"])

    def test_persona_adoption_persona_and_tone_in_prompt(self) -> None:
        result = self.tool_map[REASONING_PERSONA_ADOPTION].handler(
            {"intent": "evaluate strategy", "persona_profile": "skeptical CFO", "tone": "terse"}
        )
        self.assertIn("skeptical CFO", result["reasoning_prompt"])
        self.assertIn("terse", result["reasoning_prompt"])

    def test_dialectical_reasoning_thesis_antithesis_in_prompt(self) -> None:
        result = self.tool_map[REASONING_DIALECTICAL_REASONING].handler(
            {"intent": "pricing debate", "thesis": "raise prices", "antithesis": "lower prices"}
        )
        self.assertIn("raise prices", result["reasoning_prompt"])
        self.assertIn("lower prices", result["reasoning_prompt"])

    # ------------------------------------------------------------------
    # Category 4 — Creative & Lateral
    # ------------------------------------------------------------------

    def test_scamper_action_reflected_in_prompt(self) -> None:
        for action in ["substitute", "combine", "adapt", "modify", "put_to_other_use", "eliminate", "reverse"]:
            result = self.tool_map[REASONING_SCAMPER].handler(
                {"intent": "improve onboarding", "action": action}
            )
            self.assertIn(action.upper().replace("_", " "), result["reasoning_prompt"].upper())

    def test_lateral_thinking_stimulus_in_prompt(self) -> None:
        result = self.tool_map[REASONING_LATERAL_THINKING].handler(
            {"intent": "design a better checkout", "random_stimulus": "origami"}
        )
        self.assertIn("origami", result["reasoning_prompt"])

    def test_analogy_generation_domain_and_count_in_prompt(self) -> None:
        result = self.tool_map[REASONING_ANALOGY_GENERATION].handler(
            {"intent": "viral marketing", "target_domain": "evolutionary biology", "count": 4}
        )
        self.assertIn("evolutionary biology", result["reasoning_prompt"])
        self.assertIn("4", result["reasoning_prompt"])

    def test_role_storming_role_in_prompt(self) -> None:
        result = self.tool_map[REASONING_ROLE_STORMING].handler(
            {"intent": "grow the product", "role": "Steve Jobs"}
        )
        self.assertIn("Steve Jobs", result["reasoning_prompt"])

    def test_provocation_operation_stepping_stone_in_prompt(self) -> None:
        result = self.tool_map[REASONING_PROVOCATION_OPERATION].handler(
            {"intent": "reduce churn", "stepping_stone": "users should never be allowed to cancel"}
        )
        self.assertIn("users should never be allowed to cancel", result["reasoning_prompt"])

    # ------------------------------------------------------------------
    # Category 5 — Systems & Complexity
    # ------------------------------------------------------------------

    def test_second_order_effects_time_horizon_in_prompt(self) -> None:
        result = self.tool_map[REASONING_SECOND_ORDER_EFFECTS].handler(
            {"intent": "automate customer support", "time_horizon": "18 months"}
        )
        self.assertIn("18 months", result["reasoning_prompt"])

    def test_feedback_loop_identification_reinforcing_in_prompt(self) -> None:
        result = self.tool_map[REASONING_FEEDBACK_LOOP_IDENTIFICATION].handler(
            {"intent": "viral coefficient", "loop_type": "reinforcing"}
        )
        self.assertIn("reinforcing", result["reasoning_prompt"])

    def test_cynefin_categorization_forced_domain_in_prompt(self) -> None:
        result = self.tool_map[REASONING_CYNEFIN_CATEGORIZATION].handler(
            {"intent": "deal with incident", "domain_force": "chaotic"}
        )
        self.assertIn("chaotic", result["reasoning_prompt"])

    def test_bottleneck_identification_metric_in_prompt(self) -> None:
        result = self.tool_map[REASONING_BOTTLENECK_IDENTIFICATION].handler(
            {"intent": "CI/CD pipeline", "metric": "deployment frequency"}
        )
        self.assertIn("deployment frequency", result["reasoning_prompt"])

    def test_butterfly_effect_max_steps_in_prompt(self) -> None:
        result = self.tool_map[REASONING_BUTTERFLY_EFFECT_TRACE].handler(
            {"intent": "change default rate limit", "max_steps": 8}
        )
        self.assertIn("8", result["reasoning_prompt"])

    # ------------------------------------------------------------------
    # Category 6 — Temporal & Forecasting
    # ------------------------------------------------------------------

    def test_scenario_planning_variables_in_prompt(self) -> None:
        result = self.tool_map[REASONING_SCENARIO_PLANNING].handler(
            {"intent": "market expansion", "variables": ["interest rates", "regulatory changes"]}
        )
        self.assertIn("interest rates", result["reasoning_prompt"])
        self.assertIn("regulatory changes", result["reasoning_prompt"])

    def test_pre_mortem_failure_mode_in_prompt(self) -> None:
        result = self.tool_map[REASONING_PRE_MORTEM].handler(
            {"intent": "product launch", "failure_mode": "total market rejection"}
        )
        self.assertIn("total market rejection", result["reasoning_prompt"])

    def test_post_mortem_retrospective_focus_in_prompt(self) -> None:
        result = self.tool_map[REASONING_POST_MORTEM].handler(
            {"intent": "failed sprint", "retrospective_focus": "communication breakdowns"}
        )
        self.assertIn("communication breakdowns", result["reasoning_prompt"])

    def test_trend_extrapolation_time_delta_in_prompt(self) -> None:
        result = self.tool_map[REASONING_TREND_EXTRAPOLATION].handler(
            {"intent": "AI adoption in enterprise", "time_delta": "5 years"}
        )
        self.assertIn("5 years", result["reasoning_prompt"])

    def test_backcasting_steps_backward_in_prompt(self) -> None:
        result = self.tool_map[REASONING_BACKCASTING].handler(
            {"intent": "achieve market leadership", "steps_backward": 10}
        )
        self.assertIn("10", result["reasoning_prompt"])

    # ------------------------------------------------------------------
    # Category 7 — Evaluative & Corrective
    # ------------------------------------------------------------------

    def test_self_critique_prior_output_in_prompt(self) -> None:
        result = self.tool_map[REASONING_SELF_CRITIQUE].handler(
            {"intent": "review analysis", "prior_output": "The market is definitely growing at 50% YoY."}
        )
        self.assertIn("The market is definitely growing at 50% YoY.", result["reasoning_prompt"])

    def test_self_critique_high_rigor_level_changes_prompt(self) -> None:
        result = self.tool_map[REASONING_SELF_CRITIQUE].handler(
            {"intent": "review", "rigor_level": 9}
        )
        self.assertIn("9", result["reasoning_prompt"])
        self.assertIn("flaw until proven otherwise", result["reasoning_prompt"])

    def test_bias_detection_custom_bias_types_in_prompt(self) -> None:
        result = self.tool_map[REASONING_BIAS_DETECTION].handler(
            {"intent": "evaluate competitor", "bias_types": ["sunken cost", "not invented here"]}
        )
        self.assertIn("sunken cost", result["reasoning_prompt"])
        self.assertIn("not invented here", result["reasoning_prompt"])

    def test_bias_detection_defaults_to_common_biases(self) -> None:
        result = self.tool_map[REASONING_BIAS_DETECTION].handler({"intent": "audit reasoning"})
        self.assertIn("confirmation bias", result["reasoning_prompt"])

    def test_confidence_calibration_evidence_weight_in_prompt(self) -> None:
        result = self.tool_map[REASONING_CONFIDENCE_CALIBRATION].handler(
            {"intent": "product-market fit", "evidence_weight": 0.3}
        )
        self.assertIn("0.3", result["reasoning_prompt"])

    def test_tradeoff_evaluation_options_and_criteria_in_prompt(self) -> None:
        result = self.tool_map[REASONING_TRADEOFF_EVALUATION].handler(
            {
                "intent": "choose database",
                "option_a": "PostgreSQL",
                "option_b": "MongoDB",
                "criteria": ["scalability", "cost", "team expertise"],
            }
        )
        self.assertIn("PostgreSQL", result["reasoning_prompt"])
        self.assertIn("MongoDB", result["reasoning_prompt"])
        self.assertIn("scalability", result["reasoning_prompt"])

    # ------------------------------------------------------------------
    # Category 8 — Scientific & Empirical
    # ------------------------------------------------------------------

    def test_hypothesis_generation_count_in_prompt(self) -> None:
        result = self.tool_map[REASONING_HYPOTHESIS_GENERATION].handler(
            {"intent": "explain the sales drop", "count": 5}
        )
        self.assertIn("5", result["reasoning_prompt"])

    def test_falsification_test_conditions_in_prompt(self) -> None:
        result = self.tool_map[REASONING_FALSIFICATION_TEST].handler(
            {"intent": "social proof drives conversion", "test_conditions": "A/B test with 10k users"}
        )
        self.assertIn("A/B test with 10k users", result["reasoning_prompt"])

    def test_abductive_reasoning_evidence_in_prompt(self) -> None:
        result = self.tool_map[REASONING_ABDUCTIVE_REASONING].handler(
            {"intent": "why did retention drop", "evidence": ["notification rate increased", "support tickets rose"]}
        )
        self.assertIn("notification rate increased", result["reasoning_prompt"])
        self.assertIn("support tickets rose", result["reasoning_prompt"])

    # ------------------------------------------------------------------
    # Registry round-trip — one representative per category
    # ------------------------------------------------------------------

    def test_registry_executes_step_by_step(self) -> None:
        result = self.registry.execute(REASONING_STEP_BY_STEP, {"intent": "write a test"})
        self.assertEqual(result.output["lens"], "step_by_step")
        self.assertIn("write a test", result.output["reasoning_prompt"])

    def test_registry_executes_root_cause_analysis(self) -> None:
        result = self.registry.execute(REASONING_ROOT_CAUSE_ANALYSIS, {"intent": "high p99 latency"})
        self.assertEqual(result.output["lens"], "root_cause_analysis")

    def test_registry_executes_devils_advocate(self) -> None:
        result = self.registry.execute(REASONING_DEVILS_ADVOCATE, {"intent": "our API design is clean"})
        self.assertEqual(result.output["lens"], "devils_advocate")

    def test_registry_executes_scamper(self) -> None:
        result = self.registry.execute(REASONING_SCAMPER, {"intent": "improve login UX", "action": "reverse"})
        self.assertEqual(result.output["lens"], "scamper")
        self.assertIn("REVERSE", result.output["reasoning_prompt"])

    def test_registry_executes_second_order_effects(self) -> None:
        result = self.registry.execute(REASONING_SECOND_ORDER_EFFECTS, {"intent": "remove free tier"})
        self.assertEqual(result.output["lens"], "second_order_effects")

    def test_registry_executes_pre_mortem(self) -> None:
        result = self.registry.execute(REASONING_PRE_MORTEM, {"intent": "feature launch plan"})
        self.assertEqual(result.output["lens"], "pre_mortem")

    def test_registry_executes_self_critique(self) -> None:
        result = self.registry.execute(REASONING_SELF_CRITIQUE, {"intent": "review my last response"})
        self.assertEqual(result.output["lens"], "self_critique")

    def test_registry_executes_hypothesis_generation(self) -> None:
        result = self.registry.execute(REASONING_HYPOTHESIS_GENERATION, {"intent": "explain churn spike"})
        self.assertEqual(result.output["lens"], "hypothesis_generation")

    def test_all_50_reasoning_keys_present_in_builtin_registry(self) -> None:
        for key in _ALL_KEYS:
            self.assertIn(key, self.registry, msg=f"Key '{key}' missing from builtin registry")
from harnessiq.shared.tools import REASON_BRAINSTORM, REASON_CHAIN_OF_THOUGHT, REASON_CRITIQUE
from harnessiq.tools import create_reasoning_tools
from harnessiq.tools.reasoning import brainstorm, chain_of_thought, critique
from harnessiq.tools.registry import ToolRegistry, ToolValidationError


class TestReasoningToolsRegistry(unittest.TestCase):
    """Verify factory output and registry integration."""

    def setUp(self) -> None:
        self.tools = create_reasoning_tools()

    def test_factory_returns_three_tools(self) -> None:
        self.assertEqual(len(self.tools), 3)

    def test_factory_returns_stable_key_order(self) -> None:
        keys = tuple(t.key for t in self.tools)
        self.assertEqual(keys, (REASON_BRAINSTORM, REASON_CHAIN_OF_THOUGHT, REASON_CRITIQUE))

    def test_tools_register_without_conflict(self) -> None:
        registry = ToolRegistry(self.tools)
        self.assertIn(REASON_BRAINSTORM, registry)
        self.assertIn(REASON_CHAIN_OF_THOUGHT, registry)
        self.assertIn(REASON_CRITIQUE, registry)

    def test_constants_exported_from_tools_package(self) -> None:
        from harnessiq.tools import REASON_BRAINSTORM as B
        from harnessiq.tools import REASON_CHAIN_OF_THOUGHT as C
        from harnessiq.tools import REASON_CRITIQUE as R

        self.assertEqual(B, "reason.brainstorm")
        self.assertEqual(C, "reason.chain_of_thought")
        self.assertEqual(R, "reason.critique")

    def test_tools_require_mandatory_arguments_via_registry(self) -> None:
        registry = ToolRegistry(self.tools)
        with self.assertRaises(ToolValidationError):
            registry.execute(REASON_BRAINSTORM, {})
        with self.assertRaises(ToolValidationError):
            registry.execute(REASON_CHAIN_OF_THOUGHT, {})
        with self.assertRaises(ToolValidationError):
            registry.execute(REASON_CRITIQUE, {})


class TestBrainstormTool(unittest.TestCase):
    """Unit tests for the brainstorm handler."""

    def test_minimal_call_returns_reasoning_instruction(self) -> None:
        result = brainstorm({"topic": "TikTok hooks"})
        self.assertIn("reasoning_instruction", result)
        self.assertIsInstance(result["reasoning_instruction"], str)

    def test_instruction_contains_topic(self) -> None:
        result = brainstorm({"topic": "product demo scripts"})
        self.assertIn("product demo scripts", result["reasoning_instruction"])

    def test_instruction_contains_default_count(self) -> None:
        result = brainstorm({"topic": "hooks"})
        self.assertIn("10", result["reasoning_instruction"])

    def test_custom_count_reflected_in_instruction(self) -> None:
        result = brainstorm({"topic": "hooks", "count": 15})
        self.assertIn("15", result["reasoning_instruction"])

    def test_context_included_when_provided(self) -> None:
        result = brainstorm({"topic": "hooks", "context": "B2B SaaS audience"})
        self.assertIn("B2B SaaS audience", result["reasoning_instruction"])

    def test_constraints_included_when_provided(self) -> None:
        result = brainstorm({"topic": "hooks", "constraints": "must be under 30 words"})
        self.assertIn("must be under 30 words", result["reasoning_instruction"])

    def test_context_absent_when_not_provided(self) -> None:
        result = brainstorm({"topic": "hooks"})
        self.assertNotIn("Context:", result["reasoning_instruction"])

    def test_constraints_absent_when_not_provided(self) -> None:
        result = brainstorm({"topic": "hooks"})
        self.assertNotIn("Constraints:", result["reasoning_instruction"])

    def test_count_below_minimum_raises(self) -> None:
        with self.assertRaises(ValueError, msg="count=4 should be rejected"):
            brainstorm({"topic": "hooks", "count": 4})

    def test_count_above_maximum_raises(self) -> None:
        with self.assertRaises(ValueError):
            brainstorm({"topic": "hooks", "count": 26})

    def test_count_at_minimum_boundary_accepted(self) -> None:
        result = brainstorm({"topic": "hooks", "count": 5})
        self.assertIn("5", result["reasoning_instruction"])

    def test_count_at_maximum_boundary_accepted(self) -> None:
        result = brainstorm({"topic": "hooks", "count": 25})
        self.assertIn("25", result["reasoning_instruction"])

    def test_empty_topic_raises(self) -> None:
        with self.assertRaises(ValueError):
            brainstorm({"topic": ""})

    def test_whitespace_only_topic_raises(self) -> None:
        with self.assertRaises(ValueError):
            brainstorm({"topic": "   "})

    def test_boolean_count_raises(self) -> None:
        with self.assertRaises(ValueError):
            brainstorm({"topic": "hooks", "count": True})

    def test_instruction_header_present(self) -> None:
        result = brainstorm({"topic": "hooks"})
        self.assertIn("[REASONING: BRAINSTORM]", result["reasoning_instruction"])


class TestChainOfThoughtTool(unittest.TestCase):
    """Unit tests for the chain_of_thought handler."""

    def test_minimal_call_returns_reasoning_instruction(self) -> None:
        result = chain_of_thought({"task": "decide the best script angle"})
        self.assertIn("reasoning_instruction", result)
        self.assertIsInstance(result["reasoning_instruction"], str)

    def test_instruction_contains_task(self) -> None:
        result = chain_of_thought({"task": "evaluate audience fit"})
        self.assertIn("evaluate audience fit", result["reasoning_instruction"])

    def test_default_steps_reflected(self) -> None:
        result = chain_of_thought({"task": "plan"})
        self.assertIn("5", result["reasoning_instruction"])

    def test_custom_steps_reflected(self) -> None:
        result = chain_of_thought({"task": "plan", "steps": 7})
        self.assertIn("7", result["reasoning_instruction"])

    def test_context_included_when_provided(self) -> None:
        result = chain_of_thought({"task": "plan", "context": "enterprise market"})
        self.assertIn("enterprise market", result["reasoning_instruction"])

    def test_context_absent_when_not_provided(self) -> None:
        result = chain_of_thought({"task": "plan"})
        self.assertNotIn("Context:", result["reasoning_instruction"])

    def test_steps_below_minimum_raises(self) -> None:
        with self.assertRaises(ValueError):
            chain_of_thought({"task": "plan", "steps": 2})

    def test_steps_above_maximum_raises(self) -> None:
        with self.assertRaises(ValueError):
            chain_of_thought({"task": "plan", "steps": 11})

    def test_steps_at_boundaries_accepted(self) -> None:
        result_min = chain_of_thought({"task": "plan", "steps": 3})
        result_max = chain_of_thought({"task": "plan", "steps": 10})
        self.assertIn("3", result_min["reasoning_instruction"])
        self.assertIn("10", result_max["reasoning_instruction"])

    def test_empty_task_raises(self) -> None:
        with self.assertRaises(ValueError):
            chain_of_thought({"task": ""})

    def test_instruction_header_present(self) -> None:
        result = chain_of_thought({"task": "plan"})
        self.assertIn("[REASONING: CHAIN OF THOUGHT]", result["reasoning_instruction"])


class TestCritiqueTool(unittest.TestCase):
    """Unit tests for the critique handler."""

    def test_minimal_call_returns_reasoning_instruction(self) -> None:
        result = critique({"content": "Here is my TikTok script draft."})
        self.assertIn("reasoning_instruction", result)
        self.assertIsInstance(result["reasoning_instruction"], str)

    def test_default_aspects_present(self) -> None:
        result = critique({"content": "draft script"})
        instruction = result["reasoning_instruction"]
        self.assertIn("correctness", instruction)
        self.assertIn("clarity", instruction)
        self.assertIn("completeness", instruction)
        self.assertIn("potential improvements", instruction)

    def test_custom_aspects_replace_defaults(self) -> None:
        result = critique({"content": "draft", "aspects": ["tone", "length"]})
        instruction = result["reasoning_instruction"]
        self.assertIn("tone", instruction)
        self.assertIn("length", instruction)
        self.assertNotIn("correctness", instruction)

    def test_content_preview_included(self) -> None:
        result = critique({"content": "short script text"})
        self.assertIn("short script text", result["reasoning_instruction"])

    def test_long_content_truncated_in_preview(self) -> None:
        long_content = "a" * 400
        result = critique({"content": long_content})
        self.assertIn("...", result["reasoning_instruction"])
        # The full content should NOT appear verbatim (it's been truncated)
        self.assertNotIn("a" * 400, result["reasoning_instruction"])

    def test_empty_content_raises(self) -> None:
        with self.assertRaises(ValueError):
            critique({"content": ""})

    def test_empty_aspects_list_raises(self) -> None:
        with self.assertRaises(ValueError):
            critique({"content": "draft", "aspects": []})

    def test_non_string_aspects_raises(self) -> None:
        with self.assertRaises(ValueError):
            critique({"content": "draft", "aspects": [1, 2, 3]})

    def test_non_list_aspects_raises(self) -> None:
        with self.assertRaises(ValueError):
            critique({"content": "draft", "aspects": "correctness"})

    def test_instruction_header_present(self) -> None:
        result = critique({"content": "draft"})
        self.assertIn("[REASONING: CRITIQUE]", result["reasoning_instruction"])

    def test_instruction_is_string_key_only(self) -> None:
        result = critique({"content": "draft"})
        self.assertEqual(set(result.keys()), {"reasoning_instruction"})


class TestReasoningToolsSchema(unittest.TestCase):
    """Verify tool definitions have correct schema structure."""

    def setUp(self) -> None:
        self.tools = {t.key: t for t in create_reasoning_tools()}

    def _schema(self, key: str) -> dict:
        return self.tools[key].definition.input_schema

    def test_all_schemas_disallow_additional_properties(self) -> None:
        for key, tool in self.tools.items():
            self.assertFalse(
                tool.definition.input_schema.get("additionalProperties", True),
                f"{key} should have additionalProperties=False",
            )

    def test_brainstorm_required_fields(self) -> None:
        schema = self._schema(REASON_BRAINSTORM)
        self.assertEqual(schema["required"], ["topic"])

    def test_chain_of_thought_required_fields(self) -> None:
        schema = self._schema(REASON_CHAIN_OF_THOUGHT)
        self.assertEqual(schema["required"], ["task"])

    def test_critique_required_fields(self) -> None:
        schema = self._schema(REASON_CRITIQUE)
        self.assertEqual(schema["required"], ["content"])

    def test_brainstorm_optional_fields_present(self) -> None:
        props = self._schema(REASON_BRAINSTORM)["properties"]
        self.assertIn("count", props)
        self.assertIn("context", props)
        self.assertIn("constraints", props)

    def test_chain_of_thought_optional_fields_present(self) -> None:
        props = self._schema(REASON_CHAIN_OF_THOUGHT)["properties"]
        self.assertIn("steps", props)
        self.assertIn("context", props)

    def test_critique_optional_aspects_field_present(self) -> None:
        props = self._schema(REASON_CRITIQUE)["properties"]
        self.assertIn("aspects", props)
        self.assertEqual(props["aspects"]["type"], "array")


if __name__ == "__main__":
    unittest.main()
