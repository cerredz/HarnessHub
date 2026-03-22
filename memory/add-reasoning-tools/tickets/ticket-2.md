# Ticket 2: Implement harnessiq/tools/reasoning/ package

## Title
Implement the reasoning lens tool package with all 50 tools.

## Intent
Create the `harnessiq/tools/reasoning/` package containing all 50 reasoning lens tools. Each tool accepts `intent: str` plus optional lens-specific parameters and returns `{"lens": str, "reasoning_prompt": str}` — a formatted cognitive scaffold the agent uses to generate its next reasoning pass. This is the core deliverable of the entire feature.

## Scope
- **In scope**: `harnessiq/tools/reasoning/__init__.py`, `harnessiq/tools/reasoning/lenses.py`, all 50 tool definitions and handlers, `create_reasoning_tools()` factory function.
- **Out of scope**: Registry wiring in `builtin.py`, changes to `harnessiq/tools/__init__.py`, tests, file index updates.

## Relevant Files
- **NEW** `harnessiq/tools/reasoning/__init__.py`
- **NEW** `harnessiq/tools/reasoning/lenses.py`

## Approach

### Package structure
- `lenses.py` contains all 50 private handler functions (`_step_by_step`, ...), a shared helper `_build_definition()` for constructing `ToolDefinition` objects, shared argument-extraction helpers (`_require_string`, `_require_optional_string`, `_require_bool`, `_require_int`, `_require_optional_list`), and the public `create_reasoning_tools()` factory.
- `__init__.py` re-exports `create_reasoning_tools` and all 50 key constants imported from `harnessiq.shared.tools`.

### Return contract
Every handler returns:
```python
{"lens": "<lens_name>", "reasoning_prompt": "<formatted instruction string>"}
```
The `reasoning_prompt` tells the agent how to apply the cognitive lens to the stated intent. It incorporates the tool description, the provided intent, and any lens-specific parameter values.

### Parameter conventions
- `intent: str` — always required. The subject, question, or problem the agent should reason about.
- All other parameters are optional. Defaults are chosen to make each tool usable with intent-only invocation.
- List-typed parameters (e.g., `starting_facts`, `attack_vectors`) use JSON schema `{"type": "array", "items": {"type": "string"}}`.
- Float parameters (e.g., `strictness`, `empathy_level`) use `{"type": "number"}`.
- Enum parameters use `{"type": "string", "enum": [...]}`.
- The invalid Python identifier `80_20_focus` from pareto_analysis is named `apply_80_20_rule` in the schema.

### Tool catalog (50 tools across 8 categories)

**Category 1 — Core Logical & Sequential**
1. `step_by_step` — Linear, chronological execution. Params: `granularity: enum[high,medium,low]`.
2. `tree_of_thoughts` — Multiple branching reasoning paths. Params: `branch_factor: int`, `depth: int`.
3. `graph_of_thoughts` — Non-linear reasoning graph. Params: `node_types: list[str]`, `edges: list[str]`.
4. `forward_chaining` — Data-driven rule application toward goal. Params: `starting_facts: list[str]`, `target_state: str`.
5. `backward_chaining` — Goal-driven backward derivation. Params: `target_goal: str`, `known_facts: list[str]`.
6. `plan_and_solve` — Blueprint then execution. Params: `milestones: int`.
7. `means_end_analysis` — Continuously reduce distance to goal. Params: `current_state: str`, `goal_state: str`, `allowed_moves: list[str]`.
8. `divide_and_conquer` — Recursive decomposition. Params: `sub_problem_count: int`.

**Category 2 — Analytical & Deconstructive**
9. `first_principles` — Strip to undeniable fundamentals. Params: `depth_of_reduction: int`.
10. `root_cause_analysis` — Dig past symptoms. Params: `methodology: enum[5_whys,fishbone]`.
11. `assumption_surfacing` — Surface unstated beliefs. Params: `strictness: number`.
12. `swot_analysis` — Strengths/Weaknesses/Opportunities/Threats. Params: `internal_focus_weight: number`.
13. `cost_benefit_analysis` — Weigh positive outcomes vs costs. Params: `timeframe: str`, `metrics: list[str]`.
14. `pareto_analysis` — Identify the 20% causing 80% of effects. Params: `apply_80_20_rule: bool`.
15. `constraint_mapping` — Map all limitations. Params: `hard_vs_soft: bool`.
16. `variable_isolation` — Isolate a single changing variable. Params: `target_variable: str`.

**Category 3 — Perspective & Adversarial**
17. `devils_advocate` — Attack proposed solution to find fatal flaws. Params: `aggression_level: int`.
18. `steelmanning` — Build the strongest possible opposing view. Params: `empathy_level: number`.
19. `red_teaming` — Simulate adversarial attack on a plan. Params: `attack_vectors: list[str]`.
20. `persona_adoption` — Filter reasoning through a specific persona. Params: `persona_profile: str`, `tone: str`.
21. `six_thinking_hats` — Force reasoning through one De Bono hat. Params: `hat_color: enum[red,white,black,yellow,green,blue]`.
22. `stakeholder_analysis` — Evaluate impact on every involved party. Params: `stakeholder_list: list[str]`.
23. `dialectical_reasoning` — Thesis vs antithesis → synthesis. Params: `thesis: str`, `antithesis: str`.
24. `blindspot_check` — Scan for what is not being discussed. Params: `domain: str`.

**Category 4 — Creative & Lateral**
25. `scamper` — Structured brainstorming via one SCAMPER action. Params: `action: enum[substitute,combine,adapt,modify,put_to_other_use,eliminate,reverse]`.
26. `lateral_thinking` — Use a random stimulus to force new connections. Params: `random_stimulus: str`.
27. `analogy_generation` — Map problem structure to a different domain. Params: `target_domain: str`, `count: int`.
28. `morphological_analysis` — Combine attributes across problem dimensions. Params: `dimensions: list[str]`.
29. `worst_idea_generation` — Intentionally brainstorm terrible ideas then invert. Params: `constraints: str`.
30. `provocation_operation` — State something deliberately illogical to spark new reasoning. Params: `stepping_stone: str`.
31. `role_storming` — Brainstorm in character as a specific role. Params: `role: str`.

**Category 5 — Systems & Complexity**
32. `second_order_effects` — Analyze the consequence of the consequence. Params: `time_horizon: str`.
33. `feedback_loop_identification` — Find runaway or self-correcting cycles. Params: `loop_type: enum[balancing,reinforcing]`.
34. `cynefin_categorization` — Determine what problem-solving domain applies. Params: `domain_force: enum[clear,complicated,complex,chaotic]`.
35. `network_mapping` — Map how nodes are connected and information flows. Params: `degree_of_separation: int`.
36. `butterfly_effect_trace` — Extrapolate how a minor change cascades. Params: `max_steps: int`.
37. `bottleneck_identification` — Find the single throughput-limiting step. Params: `metric: str`.

**Category 6 — Temporal & Forecasting**
38. `scenario_planning` — Generate multiple divergent plausible futures. Params: `variables: list[str]`, `timeline: str`.
39. `pre_mortem` — Assume failure then work backward to root cause. Params: `failure_mode: str`.
40. `post_mortem` — Analyze a past event for actionable lessons. Params: `retrospective_focus: str`.
41. `trend_extrapolation` — Push current data into the future. Params: `time_delta: str`.
42. `backcasting` — Define ideal future then trace steps backward to today. Params: `steps_backward: int`.

**Category 7 — Evaluative & Corrective**
43. `self_critique` — Review own prior output for logical fallacies. Params: `prior_output: str`, `rigor_level: int`.
44. `bias_detection` — Scan reasoning for cognitive biases. Params: `bias_types: list[str]`.
45. `fact_checking` — Evaluate objective claims for accuracy. Params: `claims: list[str]`, `strictness: number`.
46. `confidence_calibration` — Output a calibrated certainty percentage with justification. Params: `evidence_weight: number`.
47. `tradeoff_evaluation` — Systematically compare two viable paths. Params: `option_a: str`, `option_b: str`, `criteria: list[str]`.

**Category 8 — Scientific & Empirical**
48. `hypothesis_generation` — Create testable, falsifiable explanations. Params: `count: int`.
49. `falsification_test` — Determine evidence required to disprove a theory. Params: `test_conditions: str`.
50. `abductive_reasoning` — Infer the best explanation from available evidence. Params: `evidence: list[str]`.

## Assumptions
- Ticket 1 is complete; all 50 `REASONING_*` constants are importable from `harnessiq.shared.tools`.
- All lens-specific parameters are optional (default values applied in handlers).
- `reasoning_prompt` strings should be rich enough to anchor the agent's cognitive frame without being so long they dominate the context window.

## Acceptance Criteria
- [ ] `harnessiq/tools/reasoning/__init__.py` exists and exports `create_reasoning_tools`.
- [ ] `harnessiq/tools/reasoning/lenses.py` exists with all 50 handlers and the `create_reasoning_tools()` factory.
- [ ] `create_reasoning_tools()` returns a `tuple` of exactly 50 `RegisteredTool` objects.
- [ ] All 50 tool keys match their corresponding constants from `harnessiq/shared/tools.py`.
- [ ] Every tool has `intent` as the sole required parameter.
- [ ] Every handler returns a `dict` with `"lens"` and `"reasoning_prompt"` keys.
- [ ] `additionalProperties: False` in every input schema.
- [ ] No handler raises on a valid intent-only call with all other parameters omitted.

## Verification Steps
1. `python -c "from harnessiq.tools.reasoning import create_reasoning_tools; tools = create_reasoning_tools(); print(len(tools))"` → `50`.
2. `python -m py_compile harnessiq/tools/reasoning/lenses.py` → no errors.
3. `python -m mypy harnessiq/tools/reasoning/` → no type errors.
4. Manually invoke 3–5 representative handlers with intent-only arguments and inspect output shape.

## Dependencies
Ticket 1.

## Drift Guard
This ticket must not modify `builtin.py`, `harnessiq/tools/__init__.py`, or any test files. It delivers the reasoning package in isolation.
