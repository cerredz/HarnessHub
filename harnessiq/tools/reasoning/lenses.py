"""
===============================================================================
File: harnessiq/tools/reasoning/lenses.py

What this file does:
- Implements part of the reasoning-tool surface used to make agent thinking
  steps more structured and inspectable.
- Reasoning lens tool definitions, handlers, and factory.

Use cases:
- Use these helpers when a harness needs explicit reasoning tools instead of
  relying only on free-form assistant text.

How to use it:
- Register these tools through the built-in tool catalog or a custom registry
  composition.

Intent:
- Expose reasoning support as deterministic tools so the SDK can guide thinking
  without hiding behavior in prompts alone.
===============================================================================
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

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
    RegisteredTool,
    ToolArguments,
    ToolDefinition,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_INTENT_PROPERTY: dict[str, object] = {
    "type": "string",
    "description": "The subject, question, or problem to reason about.",
}


def _build_definition(
    *,
    key: str,
    name: str,
    description: str,
    extra_properties: dict[str, object] | None = None,
    extra_required: Sequence[str] = (),
) -> ToolDefinition:
    properties: dict[str, object] = {"intent": _INTENT_PROPERTY}
    if extra_properties:
        properties.update(extra_properties)
    required = ["intent", *extra_required]
    return ToolDefinition(
        key=key,
        name=name,
        description=description,
        input_schema={
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    )


def _require_string(arguments: ToolArguments, key: str) -> str:
    value = arguments[key]
    if not isinstance(value, str):
        raise ValueError(f"The '{key}' argument must be a string.")
    return value


def _require_optional_string(arguments: ToolArguments, key: str) -> str | None:
    if key not in arguments or arguments[key] is None:
        return None
    value = arguments[key]
    if not isinstance(value, str):
        raise ValueError(f"The '{key}' argument must be a string when provided.")
    return value


def _require_bool(arguments: ToolArguments, key: str, *, default: bool) -> bool:
    if key not in arguments or arguments[key] is None:
        return default
    value = arguments[key]
    if not isinstance(value, bool):
        raise ValueError(f"The '{key}' argument must be a boolean.")
    return value


def _require_int(arguments: ToolArguments, key: str, *, default: int) -> int:
    if key not in arguments or arguments[key] is None:
        return default
    value = arguments[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"The '{key}' argument must be an integer.")
    return value


def _require_number(arguments: ToolArguments, key: str, *, default: float) -> float:
    if key not in arguments or arguments[key] is None:
        return default
    value = arguments[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"The '{key}' argument must be a number.")
    return float(value)


def _require_optional_list(arguments: ToolArguments, key: str) -> list[Any]:
    if key not in arguments or arguments[key] is None:
        return []
    value = arguments[key]
    if not isinstance(value, list):
        raise ValueError(f"The '{key}' argument must be a list when provided.")
    return value


def _join_list(items: list[Any], *, fallback: str = "none provided") -> str:
    if not items:
        return fallback
    return ", ".join(str(item) for item in items)


def _lens_response(lens: str, reasoning_prompt: str) -> dict[str, str]:
    return {"lens": lens, "reasoning_prompt": reasoning_prompt}


# ---------------------------------------------------------------------------
# Category 1 — Core Logical & Sequential
# ---------------------------------------------------------------------------


def _step_by_step(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    granularity = _require_optional_string(arguments, "granularity") or "medium"
    granularity_guidance = {
        "high": "List every micro-action; do not skip intermediate steps even if they seem obvious.",
        "medium": "Group related actions into meaningful steps; balance detail with readability.",
        "low": "Outline only the major phases; suppress fine-grained sub-steps.",
    }.get(granularity, "Group related actions into meaningful steps; balance detail with readability.")
    prompt = (
        f"Apply step-by-step reasoning to: {intent!r}\n\n"
        f"Granularity level: {granularity}. {granularity_guidance}\n"
        "Work through this linearly and chronologically. Each step must build cleanly on the previous. "
        "Number your steps and begin each with an active verb."
    )
    return _lens_response("step_by_step", prompt)


def _tree_of_thoughts(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    branch_factor = _require_int(arguments, "branch_factor", default=3)
    depth = _require_int(arguments, "depth", default=2)
    prompt = (
        f"Apply tree-of-thoughts reasoning to: {intent!r}\n\n"
        f"Generate {branch_factor} distinct reasoning branches at each level, "
        f"exploring {depth} level(s) of depth before selecting the most promising path. "
        "For each branch, briefly describe the approach, evaluate its strengths and weaknesses, "
        "then prune inferior branches. Commit to the best-supported conclusion and explain why it won."
    )
    return _lens_response("tree_of_thoughts", prompt)


def _graph_of_thoughts(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    node_types = _require_optional_list(arguments, "node_types")
    edges = _require_optional_list(arguments, "edges")
    node_desc = f"Node types to consider: {_join_list(node_types)}." if node_types else ""
    edge_desc = f"Relevant relationships or edges: {_join_list(edges)}." if edges else ""
    prompt = (
        f"Apply graph-of-thoughts reasoning to: {intent!r}\n\n"
        "Map the reasoning as a non-linear graph where ideas can merge, loop back, or branch. "
        f"{node_desc} {edge_desc}".strip() + "\n"
        "Identify key nodes (concepts, entities, decisions), draw the connections between them, "
        "note any cycles or convergences, and derive your conclusion from the overall graph structure."
    )
    return _lens_response("graph_of_thoughts", prompt)


def _forward_chaining(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    starting_facts = _require_optional_list(arguments, "starting_facts")
    target_state = _require_optional_string(arguments, "target_state") or "a well-reasoned conclusion"
    facts_desc = f"Starting facts: {_join_list(starting_facts)}." if starting_facts else "Begin with the available facts embedded in the intent."
    prompt = (
        f"Apply forward-chaining reasoning to: {intent!r}\n\n"
        f"{facts_desc}\n"
        f"Target state: {target_state!r}.\n"
        "Starting from the known facts, apply inference rules step by step to derive new facts. "
        "Continue chaining until you reach the target state or exhaust available inferences. "
        "Show each derivation explicitly."
    )
    return _lens_response("forward_chaining", prompt)


def _backward_chaining(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    target_goal = _require_optional_string(arguments, "target_goal") or intent
    known_facts = _require_optional_list(arguments, "known_facts")
    facts_desc = f"Known facts: {_join_list(known_facts)}." if known_facts else "Use the facts implied by the intent."
    prompt = (
        f"Apply backward-chaining reasoning to: {intent!r}\n\n"
        f"Target goal: {target_goal!r}.\n"
        f"{facts_desc}\n"
        "Starting from the desired goal, work backward. For each sub-goal, ask: what must be true "
        "for this to hold? Continue decomposing until you reach facts that are already known or provable. "
        "Trace the full chain of dependencies."
    )
    return _lens_response("backward_chaining", prompt)


def _plan_and_solve(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    milestones = _require_int(arguments, "milestones", default=3)
    prompt = (
        f"Apply plan-and-solve reasoning to: {intent!r}\n\n"
        f"Phase 1 — Blueprint: Design a plan with {milestones} concrete milestones. "
        "Define what success looks like at each milestone before writing a single execution step.\n\n"
        "Phase 2 — Execution: With the blueprint fixed, work through each milestone in sequence. "
        "Do not revise the plan during execution; surface deviations as explicit notes."
    )
    return _lens_response("plan_and_solve", prompt)


def _means_end_analysis(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    current_state = _require_optional_string(arguments, "current_state") or "the current situation as described"
    goal_state = _require_optional_string(arguments, "goal_state") or "the desired outcome"
    allowed_moves = _require_optional_list(arguments, "allowed_moves")
    moves_desc = f"Allowed moves or operations: {_join_list(allowed_moves)}." if allowed_moves else ""
    prompt = (
        f"Apply means-end analysis to: {intent!r}\n\n"
        f"Current state: {current_state}\n"
        f"Goal state: {goal_state}\n"
        f"{moves_desc}\n"
        "At each step, calculate the gap between the current state and the goal state. "
        "Select the move that most reduces this gap. Repeat until the goal is reached or no further reduction is possible."
    ).strip()
    return _lens_response("means_end_analysis", prompt)


def _divide_and_conquer(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    sub_problem_count = _require_int(arguments, "sub_problem_count", default=3)
    prompt = (
        f"Apply divide-and-conquer reasoning to: {intent!r}\n\n"
        f"Decompose the problem into exactly {sub_problem_count} independent sub-problems. "
        "Solve each sub-problem in isolation without referencing the others. "
        "Once all sub-problems are solved, combine the solutions into a coherent whole. "
        "If a sub-problem is still complex, apply the same decomposition recursively."
    )
    return _lens_response("divide_and_conquer", prompt)


# ---------------------------------------------------------------------------
# Category 2 — Analytical & Deconstructive
# ---------------------------------------------------------------------------


def _first_principles(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    depth_of_reduction = _require_int(arguments, "depth_of_reduction", default=3)
    prompt = (
        f"Apply first-principles reasoning to: {intent!r}\n\n"
        f"Reduce the problem to its most fundamental, undeniable truths over {depth_of_reduction} layer(s) of reduction. "
        "At each layer, ask: 'What assumptions am I still making?' and strip them away. "
        "Do not accept conventional wisdom or analogies — only what can be directly observed or logically proven. "
        "Rebuild your answer from these bare foundations upward."
    )
    return _lens_response("first_principles", prompt)


def _root_cause_analysis(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    methodology = _require_optional_string(arguments, "methodology") or "5_whys"
    if methodology == "fishbone":
        method_guidance = (
            "Use the fishbone (Ishikawa) diagram method. Identify the main problem, "
            "then map contributing causes across six categories: People, Process, Equipment, "
            "Materials, Environment, and Management. Find the root cause at the end of the longest causal chain."
        )
    else:
        method_guidance = (
            "Use the 5 Whys method. State the problem, then ask 'Why?' five times in succession. "
            "Each answer becomes the subject of the next 'Why?' Do not stop at symptoms."
        )
    prompt = (
        f"Apply root-cause analysis to: {intent!r}\n\n"
        f"Methodology: {methodology}.\n{method_guidance}"
    )
    return _lens_response("root_cause_analysis", prompt)


def _assumption_surfacing(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    strictness = _require_number(arguments, "strictness", default=0.7)
    prompt = (
        f"Apply assumption-surfacing reasoning to: {intent!r}\n\n"
        f"Strictness level: {strictness:.1f} (0.0 = surface only obvious assumptions, 1.0 = surface every unstated belief). "
        "List all assumptions embedded in the premise — things that must be true for the reasoning to hold. "
        "Classify each assumption as: (a) well-supported, (b) uncertain, or (c) likely false. "
        "Flag any assumption whose falsification would invalidate the entire argument."
    )
    return _lens_response("assumption_surfacing", prompt)


def _swot_analysis(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    internal_focus_weight = _require_number(arguments, "internal_focus_weight", default=0.5)
    external_weight = 1.0 - internal_focus_weight
    prompt = (
        f"Apply SWOT analysis to: {intent!r}\n\n"
        f"Weight internal factors (Strengths/Weaknesses) at {internal_focus_weight:.0%} "
        f"and external factors (Opportunities/Threats) at {external_weight:.0%}.\n\n"
        "Strengths: internal advantages that create value.\n"
        "Weaknesses: internal limitations that reduce capability.\n"
        "Opportunities: external conditions that can be exploited.\n"
        "Threats: external forces that could cause harm.\n\n"
        "After listing all four quadrants, synthesize the most important strategic insight."
    )
    return _lens_response("swot_analysis", prompt)


def _cost_benefit_analysis(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    timeframe = _require_optional_string(arguments, "timeframe") or "unspecified timeframe"
    metrics = _require_optional_list(arguments, "metrics")
    metrics_desc = f"Evaluate using these metrics: {_join_list(metrics)}." if metrics else "Use qualitative and quantitative metrics as appropriate."
    prompt = (
        f"Apply cost-benefit analysis to: {intent!r}\n\n"
        f"Timeframe: {timeframe}.\n{metrics_desc}\n\n"
        "List all identifiable benefits (direct, indirect, tangible, intangible) and assign relative magnitudes. "
        "List all identifiable costs (time, resources, risk, opportunity cost) and assign relative magnitudes. "
        "Compute the net balance and state whether the benefits outweigh the costs. "
        "Note any costs or benefits that are difficult to quantify but material to the decision."
    )
    return _lens_response("cost_benefit_analysis", prompt)


def _pareto_analysis(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    apply_80_20_rule = _require_bool(arguments, "apply_80_20_rule", default=True)
    rule_guidance = (
        "Strictly apply the 80/20 rule: identify the 20% of causes responsible for 80% of effects. "
        "Discard the long tail of minor contributors and focus exclusively on the vital few."
        if apply_80_20_rule
        else "Identify the highest-leverage causes without strictly enforcing the 80/20 threshold."
    )
    prompt = (
        f"Apply Pareto analysis to: {intent!r}\n\n"
        f"{rule_guidance}\n"
        "List all contributing factors and rank them by their impact. "
        "Draw a clear line between the vital few and the trivial many. "
        "Recommend focusing effort only on the factors above the line."
    )
    return _lens_response("pareto_analysis", prompt)


def _constraint_mapping(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    hard_vs_soft = _require_bool(arguments, "hard_vs_soft", default=True)
    classify_desc = (
        "Classify each constraint as either HARD (non-negotiable, cannot be broken) "
        "or SOFT (flexible, can be relaxed under the right conditions)."
        if hard_vs_soft
        else "List all constraints without classification."
    )
    prompt = (
        f"Apply constraint mapping to: {intent!r}\n\n"
        f"{classify_desc}\n"
        "Enumerate every limitation, restriction, or boundary that applies. "
        "For soft constraints, note under what conditions they could be relaxed. "
        "After the full inventory, identify which constraints most limit the solution space."
    )
    return _lens_response("constraint_mapping", prompt)


def _variable_isolation(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    target_variable = _require_optional_string(arguments, "target_variable") or "the primary unknown"
    prompt = (
        f"Apply variable-isolation reasoning to: {intent!r}\n\n"
        f"Target variable to isolate: {target_variable!r}.\n"
        "Enumerate all other variables in the system and declare them held constant for this analysis. "
        "Reason about the effect of the target variable alone. "
        "Then identify which held-constant variables, if released, would most change your conclusion."
    )
    return _lens_response("variable_isolation", prompt)


# ---------------------------------------------------------------------------
# Category 3 — Perspective & Adversarial
# ---------------------------------------------------------------------------


def _devils_advocate(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    aggression_level = _require_int(arguments, "aggression_level", default=5)
    aggression_guidance = (
        "Be ruthless: attack every assumption, magnify every weakness, and treat no part of the argument as sacred."
        if aggression_level >= 8
        else "Be firm but fair: identify genuine weaknesses without inventing problems."
        if aggression_level >= 4
        else "Be gentle: note potential concerns without strongly attacking the core argument."
    )
    prompt = (
        f"Apply devil's advocate reasoning to: {intent!r}\n\n"
        f"Aggression level: {aggression_level}/10. {aggression_guidance}\n"
        "Your job is to find every reason why this argument, plan, or idea could fail. "
        "Identify logical fallacies, unexamined risks, overlooked stakeholders, and fatal flaws. "
        "Do not offer constructive alternatives — only attack."
    )
    return _lens_response("devils_advocate", prompt)


def _steelmanning(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    empathy_level = _require_number(arguments, "empathy_level", default=0.8)
    prompt = (
        f"Apply steelmanning reasoning to: {intent!r}\n\n"
        f"Empathy level: {empathy_level:.1f} (0.0 = minimal, 1.0 = maximum charitable interpretation).\n"
        "Construct the absolute strongest, most coherent, most compelling version of the opposing view. "
        "Attribute the best possible motives and the most well-informed reasoning to those who hold it. "
        "Only after presenting the strongest version should you engage with it critically."
    )
    return _lens_response("steelmanning", prompt)


def _red_teaming(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    attack_vectors = _require_optional_list(arguments, "attack_vectors")
    vectors_desc = f"Priority attack vectors: {_join_list(attack_vectors)}." if attack_vectors else "Consider all plausible attack vectors."
    prompt = (
        f"Apply red-teaming reasoning to: {intent!r}\n\n"
        f"{vectors_desc}\n"
        "Assume the role of a sophisticated adversary whose goal is to exploit, break, or subvert this plan or system. "
        "Identify the highest-value attack surfaces, the most plausible failure scenarios, and the defenses that are weakest. "
        "For each identified vulnerability, estimate the effort required to exploit it and its potential impact."
    )
    return _lens_response("red_teaming", prompt)


def _persona_adoption(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    persona_profile = _require_optional_string(arguments, "persona_profile") or "a domain expert"
    tone = _require_optional_string(arguments, "tone") or "authentic to the persona"
    prompt = (
        f"Apply persona-adoption reasoning to: {intent!r}\n\n"
        f"Persona: {persona_profile}.\nTone: {tone}.\n"
        "Filter every aspect of your reasoning through this persona's worldview, knowledge base, "
        "biases, incentives, and vocabulary. Do not break character. "
        "Your analysis should reflect how this specific persona would genuinely think, prioritize, and conclude."
    )
    return _lens_response("persona_adoption", prompt)


def _six_thinking_hats(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    hat_color = _require_optional_string(arguments, "hat_color") or "blue"
    hat_guidance = {
        "white": "White Hat — Facts only. Report what is known, what data exists, and what gaps remain. No opinions or interpretations.",
        "red": "Red Hat — Emotions and intuition. Express gut reactions, feelings, and hunches without justification.",
        "black": "Black Hat — Pessimism and caution. Identify risks, downsides, dangers, and reasons why this could fail.",
        "yellow": "Yellow Hat — Optimism and value. Identify benefits, advantages, and reasons why this could succeed.",
        "green": "Green Hat — Creativity and alternatives. Generate new ideas, possibilities, and provocative options.",
        "blue": "Blue Hat — Process and meta-cognition. Manage the thinking process, summarize, and decide what thinking is needed next.",
    }.get(hat_color, "Apply the chosen thinking hat lens to frame your analysis.")
    prompt = (
        f"Apply six-thinking-hats reasoning ({hat_color} hat) to: {intent!r}\n\n"
        f"{hat_guidance}\n"
        "Stay strictly within this hat's perspective. Do not blend in the perspectives of other hats."
    )
    return _lens_response("six_thinking_hats", prompt)


def _stakeholder_analysis(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    stakeholder_list = _require_optional_list(arguments, "stakeholder_list")
    stakeholders_desc = f"Stakeholders to analyze: {_join_list(stakeholder_list)}." if stakeholder_list else "Identify all relevant stakeholders from the context."
    prompt = (
        f"Apply stakeholder analysis to: {intent!r}\n\n"
        f"{stakeholders_desc}\n"
        "For each stakeholder: identify their interests, their power/influence level, "
        "how this decision affects them, what they would want, and any conflicts of interest with other stakeholders. "
        "Conclude with a summary of the net stakeholder landscape and which groups require the most attention."
    )
    return _lens_response("stakeholder_analysis", prompt)


def _dialectical_reasoning(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    thesis = _require_optional_string(arguments, "thesis") or "the primary position suggested by the intent"
    antithesis = _require_optional_string(arguments, "antithesis") or "the strongest opposing position"
    prompt = (
        f"Apply dialectical reasoning to: {intent!r}\n\n"
        f"Thesis: {thesis}\n"
        f"Antithesis: {antithesis}\n\n"
        "Step 1 — Thesis: Present the thesis in its strongest form.\n"
        "Step 2 — Antithesis: Present the antithesis in its strongest form, as a genuine challenge to the thesis.\n"
        "Step 3 — Synthesis: Identify the contradiction and resolve it into a higher-order synthesis that preserves "
        "the truth in both positions while transcending their conflict."
    )
    return _lens_response("dialectical_reasoning", prompt)


def _blindspot_check(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    domain = _require_optional_string(arguments, "domain") or "the relevant domain"
    prompt = (
        f"Apply blindspot-check reasoning to: {intent!r}\n\n"
        f"Domain context: {domain}.\n"
        "Scan the current reasoning specifically for what is NOT being discussed. "
        "Ask: What perspectives are absent? What stakeholders are invisible? What time horizons are ignored? "
        "What assumptions are so embedded they are invisible? What evidence would change this analysis if it existed? "
        "Surface each blindspot as a named gap, and estimate how much it could change the conclusion if addressed."
    )
    return _lens_response("blindspot_check", prompt)


# ---------------------------------------------------------------------------
# Category 4 — Creative & Lateral
# ---------------------------------------------------------------------------


def _scamper(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    action = _require_optional_string(arguments, "action") or "substitute"
    action_guidance = {
        "substitute": "SUBSTITUTE: What components, materials, processes, or rules can be replaced with something different?",
        "combine": "COMBINE: What elements can be merged, blended, or joined to create something new?",
        "adapt": "ADAPT: What can be adjusted, modified, or repurposed from another context?",
        "modify": "MODIFY: What can be magnified, minimized, rearranged, or otherwise altered in form or function?",
        "put_to_other_use": "PUT TO OTHER USE: How can this be used in a context for which it was not originally designed?",
        "eliminate": "ELIMINATE: What can be removed, simplified, or stripped away to make this leaner?",
        "reverse": "REVERSE: What happens if you flip, invert, or do the opposite of the current approach?",
    }.get(action, f"Apply the SCAMPER action '{action}' to explore new possibilities.")
    prompt = (
        f"Apply SCAMPER ({action}) brainstorming to: {intent!r}\n\n"
        f"{action_guidance}\n"
        "Generate at least three distinct ideas using only this SCAMPER operator. "
        "Do not drift into other SCAMPER categories. Evaluate the most promising idea at the end."
    )
    return _lens_response("scamper", prompt)


def _lateral_thinking(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    random_stimulus = _require_optional_string(arguments, "random_stimulus") or "a random unrelated concept"
    prompt = (
        f"Apply lateral thinking to: {intent!r}\n\n"
        f"Random stimulus: {random_stimulus!r}.\n"
        "Force a connection between the problem and this unrelated stimulus. "
        "Do not rationalize or pre-filter — pursue the connection even if it seems absurd. "
        "Use the unexpected association to arrive at a solution path you would not have found through direct analysis."
    )
    return _lens_response("lateral_thinking", prompt)


def _analogy_generation(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    target_domain = _require_optional_string(arguments, "target_domain") or "an unrelated domain"
    count = _require_int(arguments, "count", default=3)
    prompt = (
        f"Apply analogy generation to: {intent!r}\n\n"
        f"Map the structure of this problem to {target_domain!r}. Generate {count} distinct analogies.\n"
        "For each analogy, show: (a) the structural correspondence between the original problem and the analogous domain, "
        "(b) what the analogy reveals that direct analysis would miss, and "
        "(c) a concrete insight or solution path inspired by the analogy."
    )
    return _lens_response("analogy_generation", prompt)


def _morphological_analysis(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    dimensions = _require_optional_list(arguments, "dimensions")
    dims_desc = f"Problem dimensions to analyze: {_join_list(dimensions)}." if dimensions else "Identify the key dimensions of the problem yourself."
    prompt = (
        f"Apply morphological analysis to: {intent!r}\n\n"
        f"{dims_desc}\n"
        "Break the problem into its core dimensions. For each dimension, list all plausible attribute values. "
        "Then explore non-obvious combinations of attributes across dimensions to generate novel solutions. "
        "Highlight the combination with the highest potential that would not emerge from conventional thinking."
    )
    return _lens_response("morphological_analysis", prompt)


def _worst_idea_generation(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    constraints = _require_optional_string(arguments, "constraints") or "none specified"
    prompt = (
        f"Apply worst-idea generation to: {intent!r}\n\n"
        f"Constraints to observe: {constraints}.\n"
        "Phase 1 — Brainstorm the worst, most counterproductive, most absurd ideas possible. "
        "Deliberately try to make things worse. Quantity over quality. No idea is too bad.\n\n"
        "Phase 2 — Invert each bad idea. Transform the terrible idea into its productive opposite. "
        "Some of the best solutions emerge from this reversal. "
        "Select the two or three inverted ideas with the most unexpected potential."
    )
    return _lens_response("worst_idea_generation", prompt)


def _provocation_operation(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    stepping_stone = _require_optional_string(arguments, "stepping_stone") or "a deliberately illogical provocation"
    prompt = (
        f"Apply provocation operation (PO) reasoning to: {intent!r}\n\n"
        f"Provocative statement: {stepping_stone!r}\n"
        "Do not judge or reject this statement. Treat it as a stepping stone. "
        "Follow wherever the thought leads, even through illogical territory. "
        "The goal is not to defend the provocation but to use the mental disruption it creates "
        "to find a novel angle on the problem that logical analysis would never reach."
    )
    return _lens_response("provocation_operation", prompt)


def _role_storming(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    role = _require_optional_string(arguments, "role") or "an innovative domain expert"
    prompt = (
        f"Apply role-storming to: {intent!r}\n\n"
        f"Brainstorm fully in character as: {role!r}.\n"
        "How would this specific person approach this problem? What do they know that a generalist doesn't? "
        "What assumptions would they immediately challenge? What solutions would they naturally gravitate toward? "
        "Generate ideas as this person would generate them — not how you think they would, but how they would."
    )
    return _lens_response("role_storming", prompt)


# ---------------------------------------------------------------------------
# Category 5 — Systems & Complexity
# ---------------------------------------------------------------------------


def _second_order_effects(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    time_horizon = _require_optional_string(arguments, "time_horizon") or "medium term"
    prompt = (
        f"Apply second-order effects reasoning to: {intent!r}\n\n"
        f"Time horizon: {time_horizon}.\n"
        "First, identify the direct first-order effects of the action or decision. "
        "Then, for each first-order effect, ask: 'And then what happens?' — tracing the causal chain forward. "
        "Continue to at least second-order effects. Flag any third-order effects that are significant. "
        "Identify which downstream effects are most likely to surprise the decision-maker."
    )
    return _lens_response("second_order_effects", prompt)


def _feedback_loop_identification(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    loop_type = _require_optional_string(arguments, "loop_type") or "both"
    loop_guidance = {
        "reinforcing": "Focus on reinforcing (positive feedback) loops — self-amplifying cycles that cause exponential growth or collapse.",
        "balancing": "Focus on balancing (negative feedback) loops — self-correcting cycles that stabilize the system.",
        "both": "Identify both reinforcing and balancing loops, noting how they interact.",
    }.get(loop_type, "Identify feedback loops of any type.")
    prompt = (
        f"Apply feedback-loop identification to: {intent!r}\n\n"
        f"{loop_guidance}\n"
        "Map the system: identify the key variables, show how each variable influences the others, "
        "and trace the closed loops. For each loop: name it, describe its behavior, "
        "and predict whether it will amplify or dampen change over time."
    )
    return _lens_response("feedback_loop_identification", prompt)


def _cynefin_categorization(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    domain_force = _require_optional_string(arguments, "domain_force")
    if domain_force:
        domain_guidance = f"Force classification into the '{domain_force}' domain and reason accordingly."
    else:
        domain_guidance = "Determine the correct domain based on the characteristics of the situation."
    domain_descriptions = (
        "Clear: known cause-effect; apply best practices. "
        "Complicated: knowable cause-effect; analyze then apply good practices. "
        "Complex: emergent cause-effect; probe, sense, respond. "
        "Chaotic: no cause-effect; act to stabilize, then sense."
    )
    prompt = (
        f"Apply Cynefin categorization to: {intent!r}\n\n"
        f"{domain_guidance}\n"
        f"Domain reference: {domain_descriptions}\n"
        "Justify the domain classification with evidence from the situation. "
        "Then state the appropriate decision-making approach that the domain prescribes."
    )
    return _lens_response("cynefin_categorization", prompt)


def _network_mapping(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    degree_of_separation = _require_int(arguments, "degree_of_separation", default=2)
    prompt = (
        f"Apply network mapping to: {intent!r}\n\n"
        f"Map connections up to {degree_of_separation} degree(s) of separation from the central entity or concept.\n"
        "Identify all nodes (entities, concepts, actors, systems), draw the edges (relationships, dependencies, flows) "
        "between them, and characterize each edge (strength, direction, type). "
        "Identify the highest-degree nodes (hubs), the bridges between clusters, "
        "and any nodes whose removal would fragment the network."
    )
    return _lens_response("network_mapping", prompt)


def _butterfly_effect_trace(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    max_steps = _require_int(arguments, "max_steps", default=5)
    prompt = (
        f"Apply butterfly-effect tracing to: {intent!r}\n\n"
        f"Trace up to {max_steps} causal steps from the initial small change.\n"
        "Begin with the minor variable or event. At each step, ask: what does this change trigger in the broader system? "
        "Trace the cascade through feedback loops, amplifying mechanisms, and systemic dependencies. "
        "Identify the step where the change becomes irreversible or where it reaches a critical threshold."
    )
    return _lens_response("butterfly_effect_trace", prompt)


def _bottleneck_identification(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    metric = _require_optional_string(arguments, "metric") or "overall throughput"
    prompt = (
        f"Apply bottleneck identification to: {intent!r}\n\n"
        f"Optimization metric: {metric}.\n"
        "Map the full process or system pipeline. For each stage, estimate its capacity relative to demand. "
        f"Identify the single stage that most constrains {metric} — the bottleneck. "
        "Quantify how much improvement is theoretically available if the bottleneck is eliminated. "
        "Then identify the next bottleneck that would emerge after the primary one is resolved."
    )
    return _lens_response("bottleneck_identification", prompt)


# ---------------------------------------------------------------------------
# Category 6 — Temporal & Forecasting
# ---------------------------------------------------------------------------


def _scenario_planning(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    variables = _require_optional_list(arguments, "variables")
    timeline = _require_optional_string(arguments, "timeline") or "the relevant time horizon"
    vars_desc = f"Key uncertainty variables: {_join_list(variables)}." if variables else "Identify the two most uncertain and most impactful variables."
    prompt = (
        f"Apply scenario planning to: {intent!r}\n\n"
        f"Timeline: {timeline}.\n{vars_desc}\n\n"
        "Construct three to four distinct, plausible future scenarios by varying the key uncertainty axes. "
        "Each scenario must be internally consistent and named with a memorable label. "
        "For each scenario, describe: the triggering conditions, the state of the world at the end of the timeline, "
        "and the strategic implications for the decision at hand."
    )
    return _lens_response("scenario_planning", prompt)


def _pre_mortem(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    failure_mode = _require_optional_string(arguments, "failure_mode") or "a comprehensive failure"
    prompt = (
        f"Apply pre-mortem analysis to: {intent!r}\n\n"
        f"Assume the following has already happened: {failure_mode}.\n"
        "The plan has failed spectacularly. It is now one year in the future. "
        "Working backward from this confirmed failure, identify the most likely causes. "
        "What early warning signs were ignored? What assumptions proved wrong? "
        "What risks were underestimated? Rank causes by their contribution to the failure."
    )
    return _lens_response("pre_mortem", prompt)


def _post_mortem(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    retrospective_focus = _require_optional_string(arguments, "retrospective_focus") or "all aspects of the event"
    prompt = (
        f"Apply post-mortem analysis to: {intent!r}\n\n"
        f"Retrospective focus: {retrospective_focus}.\n"
        "Analyze the event with no defensive rationalizations. "
        "What actually happened (timeline of events)? What went well and why? What went wrong and why? "
        "What was within our control vs. outside it? "
        "Extract three to five specific, actionable lessons that directly change future behavior. "
        "State each lesson as: 'Next time, we will [specific action] because [specific evidence from this event].'"
    )
    return _lens_response("post_mortem", prompt)


def _trend_extrapolation(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    time_delta = _require_optional_string(arguments, "time_delta") or "the next 3–5 years"
    prompt = (
        f"Apply trend extrapolation to: {intent!r}\n\n"
        f"Project the current trajectory forward across: {time_delta}.\n"
        "Identify the dominant trends currently in motion. For each trend, extrapolate its trajectory "
        "assuming no disruptive changes (linear or exponential as appropriate). "
        "State the projected state at the end of the time delta. "
        "Then identify which assumptions in the extrapolation are most likely to be violated."
    )
    return _lens_response("trend_extrapolation", prompt)


def _backcasting(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    steps_backward = _require_int(arguments, "steps_backward", default=5)
    prompt = (
        f"Apply backcasting to: {intent!r}\n\n"
        f"Define the ideal future state implied by the intent. "
        f"Trace {steps_backward} steps backward from that future to the present day.\n"
        "At each step backward, ask: 'What had to be true one step earlier for this state to be reachable?' "
        "Work all the way back to the current situation. "
        "The result is a roadmap of prerequisites — work the steps forward as your plan of action."
    )
    return _lens_response("backcasting", prompt)


# ---------------------------------------------------------------------------
# Category 7 — Evaluative & Corrective
# ---------------------------------------------------------------------------


def _self_critique(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    prior_output = _require_optional_string(arguments, "prior_output") or "the prior reasoning output for this task"
    rigor_level = _require_int(arguments, "rigor_level", default=7)
    prompt = (
        f"Apply self-critique to: {intent!r}\n\n"
        f"Prior output to review: {prior_output!r}\n"
        f"Rigor level: {rigor_level}/10.\n"
        "Review the prior output as a skeptical peer reviewer. Check for: logical fallacies, unsupported claims, "
        "missed edge cases, instructions not followed, internal contradictions, and over-confident assertions. "
        f"{'Assume every sentence has a flaw until proven otherwise.' if rigor_level >= 8 else 'Focus on material weaknesses only.'}\n"
        "For each flaw found, state it clearly and propose a specific correction."
    )
    return _lens_response("self_critique", prompt)


def _bias_detection(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    bias_types = _require_optional_list(arguments, "bias_types")
    default_biases = "confirmation bias, anchoring, availability heuristic, sunk cost fallacy, survivorship bias"
    biases_desc = f"Scan for these specific biases: {_join_list(bias_types)}." if bias_types else f"Scan for common cognitive biases including: {default_biases}."
    prompt = (
        f"Apply bias detection to: {intent!r}\n\n"
        f"{biases_desc}\n"
        "For each bias found: name it, quote the specific part of the reasoning it affects, "
        "explain why it qualifies as this bias, and estimate its impact on the conclusion. "
        "At the end, state which single bias most distorts the overall analysis."
    )
    return _lens_response("bias_detection", prompt)


def _fact_checking(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    claims = _require_optional_list(arguments, "claims")
    strictness = _require_number(arguments, "strictness", default=0.8)
    claims_desc = f"Claims to evaluate: {_join_list(claims)}." if claims else "Extract and evaluate all objective claims embedded in the intent."
    prompt = (
        f"Apply fact-checking reasoning to: {intent!r}\n\n"
        f"{claims_desc}\n"
        f"Strictness level: {strictness:.1f} (0.0 = accept plausible claims, 1.0 = demand strong evidence for every claim).\n"
        "For each claim: classify it as factual, opinion, or mixed; evaluate its likelihood of being true "
        "based on available knowledge; flag any claim where confidence is below 0.7; "
        "and note what evidence would increase or decrease confidence in the claim."
    )
    return _lens_response("fact_checking", prompt)


def _confidence_calibration(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    evidence_weight = _require_number(arguments, "evidence_weight", default=0.5)
    prompt = (
        f"Apply confidence calibration to: {intent!r}\n\n"
        f"Evidence weight provided: {evidence_weight:.1f} (0.0 = no evidence, 1.0 = overwhelming evidence).\n"
        "State your central assertion about the intent clearly. "
        "Then assign a confidence percentage (0–100%) to this assertion. "
        "Justify the percentage: what evidence supports it, what evidence could change it, "
        "and what is the range of plausible confidence given the available evidence? "
        "Avoid overconfidence — if evidence is sparse, the confidence range should be wide."
    )
    return _lens_response("confidence_calibration", prompt)


def _tradeoff_evaluation(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    option_a = _require_optional_string(arguments, "option_a") or "Option A (first viable path)"
    option_b = _require_optional_string(arguments, "option_b") or "Option B (second viable path)"
    criteria = _require_optional_list(arguments, "criteria")
    criteria_desc = f"Evaluation criteria: {_join_list(criteria)}." if criteria else "Choose the most relevant evaluation criteria."
    prompt = (
        f"Apply tradeoff evaluation to: {intent!r}\n\n"
        f"Option A: {option_a}\nOption B: {option_b}\n{criteria_desc}\n\n"
        "Neither option is perfect. Your job is not to declare a winner but to make the tradeoffs explicit. "
        "For each criterion, score both options and note what must be sacrificed by choosing one over the other. "
        "Conclude with a recommendation that acknowledges the sacrifice it requires."
    )
    return _lens_response("tradeoff_evaluation", prompt)


# ---------------------------------------------------------------------------
# Category 8 — Scientific & Empirical
# ---------------------------------------------------------------------------


def _hypothesis_generation(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    count = _require_int(arguments, "count", default=3)
    prompt = (
        f"Apply hypothesis generation to: {intent!r}\n\n"
        f"Generate {count} distinct, testable, falsifiable hypotheses that could explain the observation or answer the question.\n"
        "Each hypothesis must: (a) be stated as a specific, directional claim, "
        "(b) be falsifiable — describe what evidence would prove it wrong, "
        "(c) differ meaningfully from the other hypotheses (no rewording of the same idea). "
        "Rank the hypotheses by prior plausibility and note which is most amenable to testing."
    )
    return _lens_response("hypothesis_generation", prompt)


def _falsification_test(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    test_conditions = _require_optional_string(arguments, "test_conditions") or "standard empirical conditions"
    prompt = (
        f"Apply falsification testing to: {intent!r}\n\n"
        f"Test conditions: {test_conditions}.\n"
        "Treat the intent as a theory to be challenged, not defended. "
        "Determine what specific, observable evidence would be required to disprove this theory. "
        "Design at least two distinct tests, each targeting a different vulnerability in the theory. "
        "For each test: state the prediction the theory makes, state what outcome would falsify it, "
        "and assess how practically feasible the test is."
    )
    return _lens_response("falsification_test", prompt)


def _abductive_reasoning(arguments: ToolArguments) -> dict[str, str]:
    intent = _require_string(arguments, "intent")
    evidence = _require_optional_list(arguments, "evidence")
    evidence_desc = f"Available evidence: {_join_list(evidence)}." if evidence else "Use the evidence implied by the intent."
    prompt = (
        f"Apply abductive reasoning to: {intent!r}\n\n"
        f"{evidence_desc}\n"
        "Generate the simplest and most likely explanation that accounts for all available evidence. "
        "Do not require complete proof — inference to the best explanation is the goal. "
        "List at least three candidate explanations, rank them by explanatory power and parsimony, "
        "and justify why the top-ranked explanation is most plausible given the evidence. "
        "Note what additional evidence would confirm or overturn this inference."
    )
    return _lens_response("abductive_reasoning", prompt)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_reasoning_tools() -> tuple[RegisteredTool, ...]:
    """Return the full set of 50 registered reasoning lens tools."""
    return (
        # --- Category 1: Core Logical & Sequential ---
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_STEP_BY_STEP,
                name="step_by_step",
                description=(
                    "Force linear, chronological execution by breaking a task into numbered steps. "
                    "Each step is a discrete, actionable unit that builds on the previous. "
                    "Use this lens when you need strict sequential discipline and cannot afford to skip ahead."
                ),
                extra_properties={
                    "granularity": {
                        "type": "string",
                        "enum": ["high", "medium", "low"],
                        "description": "Level of detail: high lists micro-actions, low outlines major phases.",
                    },
                },
            ),
            handler=_step_by_step,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_TREE_OF_THOUGHTS,
                name="tree_of_thoughts",
                description=(
                    "Generate multiple possible reasoning paths, exploring branches before committing to a final answer. "
                    "Useful when the problem space has many viable directions and premature commitment leads to dead ends. "
                    "Prune inferior branches explicitly before selecting the winning path."
                ),
                extra_properties={
                    "branch_factor": {
                        "type": "integer",
                        "description": "Number of distinct branches to generate at each decision point.",
                    },
                    "depth": {
                        "type": "integer",
                        "description": "Number of branching levels to explore before converging.",
                    },
                },
            ),
            handler=_tree_of_thoughts,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_GRAPH_OF_THOUGHTS,
                name="graph_of_thoughts",
                description=(
                    "Map non-linear reasoning relationships where paths can merge, loop back, or split. "
                    "Unlike tree-of-thoughts, ideas in this lens are nodes in a graph — they can be revisited, "
                    "combined, or derived from multiple predecessors. Use when reasoning is inherently networked."
                ),
                extra_properties={
                    "node_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Types of nodes to include in the graph (e.g., concepts, decisions, entities).",
                    },
                    "edges": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Relationship types to model as edges between nodes.",
                    },
                },
            ),
            handler=_graph_of_thoughts,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_FORWARD_CHAINING,
                name="forward_chaining",
                description=(
                    "Start with available facts and apply inference rules to derive new facts until a goal is reached. "
                    "Data-driven: the reasoning is pushed forward by what is known, not pulled by the goal. "
                    "Use when you have a rich set of starting facts and want to discover emergent conclusions."
                ),
                extra_properties={
                    "starting_facts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Known facts available at the start of the reasoning chain.",
                    },
                    "target_state": {
                        "type": "string",
                        "description": "The desired goal state or conclusion to reach.",
                    },
                },
            ),
            handler=_forward_chaining,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_BACKWARD_CHAINING,
                name="backward_chaining",
                description=(
                    "Start with the desired goal and work backward to determine what facts must be true to achieve it. "
                    "Goal-driven: the reasoning is pulled by the target state. "
                    "Use when you know exactly what outcome you want and need to identify the prerequisite conditions."
                ),
                extra_properties={
                    "target_goal": {
                        "type": "string",
                        "description": "The desired goal or conclusion to work backward from.",
                    },
                    "known_facts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Facts already established that can serve as terminal nodes in the chain.",
                    },
                },
            ),
            handler=_backward_chaining,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_PLAN_AND_SOLVE,
                name="plan_and_solve",
                description=(
                    "Separate reasoning into two distinct phases: first design a complete blueprint, then execute it. "
                    "This lens prevents the common error of planning while doing, which causes drift. "
                    "The blueprint is fixed before execution begins; deviations are noted, not silently absorbed."
                ),
                extra_properties={
                    "milestones": {
                        "type": "integer",
                        "description": "Number of concrete milestones to define in the plan phase.",
                    },
                },
            ),
            handler=_plan_and_solve,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_MEANS_END_ANALYSIS,
                name="means_end_analysis",
                description=(
                    "Continuously calculate the distance between the current state and the goal state, "
                    "then select the action that most reduces that distance. "
                    "Use when the problem has a well-defined current state, a clear goal state, "
                    "and a bounded set of possible moves or operations."
                ),
                extra_properties={
                    "current_state": {
                        "type": "string",
                        "description": "Description of the current situation.",
                    },
                    "goal_state": {
                        "type": "string",
                        "description": "Description of the desired end state.",
                    },
                    "allowed_moves": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Operations or moves available to reduce the gap between states.",
                    },
                },
            ),
            handler=_means_end_analysis,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_DIVIDE_AND_CONQUER,
                name="divide_and_conquer",
                description=(
                    "Recursively break a complex problem into smaller, independent sub-problems. "
                    "Solve each sub-problem in isolation, then combine the results into a coherent whole. "
                    "Use when the problem can be cleanly partitioned and each partition can be solved independently."
                ),
                extra_properties={
                    "sub_problem_count": {
                        "type": "integer",
                        "description": "Number of independent sub-problems to decompose into.",
                    },
                },
            ),
            handler=_divide_and_conquer,
        ),
        # --- Category 2: Analytical & Deconstructive ---
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_FIRST_PRINCIPLES,
                name="first_principles",
                description=(
                    "Strip a problem down to its most fundamental, undeniable truths, discarding all assumptions. "
                    "Rebuild the answer from bare foundations. This lens is the antidote to analogical thinking "
                    "and conventional wisdom. Use when standard approaches have been exhausted or are known to be flawed."
                ),
                extra_properties={
                    "depth_of_reduction": {
                        "type": "integer",
                        "description": "Number of layers of assumption to strip away before rebuilding.",
                    },
                },
            ),
            handler=_first_principles,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_ROOT_CAUSE_ANALYSIS,
                name="root_cause_analysis",
                description=(
                    "Dig past symptoms to find the core origin of a problem. "
                    "Supports both 5 Whys (iterative causal questioning) and fishbone/Ishikawa (categorical mapping). "
                    "Use when a problem keeps recurring because surface fixes are addressing symptoms, not causes."
                ),
                extra_properties={
                    "methodology": {
                        "type": "string",
                        "enum": ["5_whys", "fishbone"],
                        "description": "Root-cause method: 5_whys for iterative questioning, fishbone for categorical mapping.",
                    },
                },
            ),
            handler=_root_cause_analysis,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_ASSUMPTION_SURFACING,
                name="assumption_surfacing",
                description=(
                    "Identify and list all unstated beliefs required for a given premise to be true. "
                    "Classifies assumptions as well-supported, uncertain, or likely false. "
                    "Use before committing to a plan or argument to expose hidden dependencies that could invalidate it."
                ),
                extra_properties={
                    "strictness": {
                        "type": "number",
                        "description": "0.0 surfaces only obvious assumptions; 1.0 surfaces every unstated belief.",
                    },
                },
            ),
            handler=_assumption_surfacing,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_SWOT_ANALYSIS,
                name="swot_analysis",
                description=(
                    "Evaluate Strengths, Weaknesses, Opportunities, and Threats in a structured four-quadrant analysis. "
                    "Internal factors (S/W) reflect the entity's own capabilities; external factors (O/T) reflect the environment. "
                    "Use for strategic decisions where understanding both internal and external forces is critical."
                ),
                extra_properties={
                    "internal_focus_weight": {
                        "type": "number",
                        "description": "0.0 focuses entirely on external factors; 1.0 focuses entirely on internal factors. Default 0.5.",
                    },
                },
            ),
            handler=_swot_analysis,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_COST_BENEFIT_ANALYSIS,
                name="cost_benefit_analysis",
                description=(
                    "Weigh positive outcomes against negative costs — time, compute, resources, and opportunity cost. "
                    "Covers both tangible and intangible factors. "
                    "Use before committing to a course of action when resource trade-offs need to be made explicit."
                ),
                extra_properties={
                    "timeframe": {
                        "type": "string",
                        "description": "Time horizon over which to evaluate costs and benefits.",
                    },
                    "metrics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific metrics to use when quantifying costs and benefits.",
                    },
                },
            ),
            handler=_cost_benefit_analysis,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_PARETO_ANALYSIS,
                name="pareto_analysis",
                description=(
                    "Identify the 20% of causes that produce 80% of the effects. "
                    "Focuses attention on the vital few rather than the trivial many. "
                    "Use when resources are constrained and maximum leverage must be identified quickly."
                ),
                extra_properties={
                    "apply_80_20_rule": {
                        "type": "boolean",
                        "description": "When true, strictly enforce the 80/20 threshold. When false, identify high-leverage causes without a fixed ratio.",
                    },
                },
            ),
            handler=_pareto_analysis,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_CONSTRAINT_MAPPING,
                name="constraint_mapping",
                description=(
                    "Map out all limitations, distinguishing between unbreakable hard constraints and flexible soft constraints. "
                    "Reveals the true solution space after all restrictions are accounted for. "
                    "Use at the start of any design or planning task to prevent building solutions that violate unbreakable rules."
                ),
                extra_properties={
                    "hard_vs_soft": {
                        "type": "boolean",
                        "description": "When true, classify each constraint as hard (non-negotiable) or soft (flexible).",
                    },
                },
            ),
            handler=_constraint_mapping,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_VARIABLE_ISOLATION,
                name="variable_isolation",
                description=(
                    "Hold all factors constant to observe the impact of a single changing variable. "
                    "Emulates controlled experimental reasoning in contexts where true experiments cannot be run. "
                    "Use when a complex multi-factor system makes it impossible to know which variable is driving an outcome."
                ),
                extra_properties={
                    "target_variable": {
                        "type": "string",
                        "description": "The specific variable to isolate and analyze.",
                    },
                },
            ),
            handler=_variable_isolation,
        ),
        # --- Category 3: Perspective & Adversarial ---
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_DEVILS_ADVOCATE,
                name="devils_advocate",
                description=(
                    "Actively attack a proposed solution with the intent of finding fatal flaws. "
                    "The goal is not to be constructive but to stress-test the argument to its breaking point. "
                    "Use before committing to a plan to surface vulnerabilities that uncritical agreement would miss."
                ),
                extra_properties={
                    "aggression_level": {
                        "type": "integer",
                        "description": "1–10 scale: 1 is gentle probing, 10 is ruthless deconstruction of every claim.",
                    },
                },
            ),
            handler=_devils_advocate,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_STEELMANNING,
                name="steelmanning",
                description=(
                    "Construct the absolute strongest, most compelling version of an opposing view before engaging with it. "
                    "The opposite of a straw man: give the opposing argument every benefit of the doubt. "
                    "Use when you suspect your reasoning is dismissing a position without genuinely engaging with its best form."
                ),
                extra_properties={
                    "empathy_level": {
                        "type": "number",
                        "description": "0.0 = minimal charitable interpretation; 1.0 = maximum charitable interpretation.",
                    },
                },
            ),
            handler=_steelmanning,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_RED_TEAMING,
                name="red_teaming",
                description=(
                    "Simulate an adversarial attack on a plan or system to test its defenses. "
                    "Takes the role of a sophisticated adversary seeking to exploit, break, or subvert the plan. "
                    "Use for security-sensitive plans, strategies with high failure costs, or systems exposed to hostile actors."
                ),
                extra_properties={
                    "attack_vectors": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific attack surfaces or exploit categories to prioritize.",
                    },
                },
            ),
            handler=_red_teaming,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_PERSONA_ADOPTION,
                name="persona_adoption",
                description=(
                    "Filter reasoning entirely through the worldview, biases, and knowledge of a specific persona. "
                    "Produces analysis that reflects how that person would genuinely think — not how you imagine they would. "
                    "Use when you need to anticipate how a specific stakeholder, expert, or adversary would respond."
                ),
                extra_properties={
                    "persona_profile": {
                        "type": "string",
                        "description": "Description of the persona whose perspective to adopt.",
                    },
                    "tone": {
                        "type": "string",
                        "description": "Tone or voice to use that is authentic to the persona.",
                    },
                },
            ),
            handler=_persona_adoption,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_SIX_THINKING_HATS,
                name="six_thinking_hats",
                description=(
                    "Force reasoning strictly through one of Edward de Bono's six thinking hats: "
                    "white (facts), red (emotions), black (pessimism), yellow (optimism), green (creativity), blue (process). "
                    "Each hat activates a distinct cognitive mode. "
                    "Use when parallel thinking needs to be separated into clean, non-contradictory streams."
                ),
                extra_properties={
                    "hat_color": {
                        "type": "string",
                        "enum": ["red", "white", "black", "yellow", "green", "blue"],
                        "description": "The thinking hat to wear: white=facts, red=emotion, black=risk, yellow=value, green=creativity, blue=process.",
                    },
                },
            ),
            handler=_six_thinking_hats,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_STAKEHOLDER_ANALYSIS,
                name="stakeholder_analysis",
                description=(
                    "Evaluate how a decision or action impacts every involved party. "
                    "Maps interests, influence levels, conflicts, and requirements for each stakeholder. "
                    "Use before any decision with broad organizational or social impact to avoid blind spots in stakeholder coverage."
                ),
                extra_properties={
                    "stakeholder_list": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Names or descriptions of stakeholders to analyze.",
                    },
                },
            ),
            handler=_stakeholder_analysis,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_DIALECTICAL_REASONING,
                name="dialectical_reasoning",
                description=(
                    "Pit two opposing ideas (thesis and antithesis) against each other to synthesize a superior conclusion. "
                    "The synthesis must transcend the contradiction, preserving truth from both sides. "
                    "Use when two valid but conflicting positions need to be reconciled into higher-order understanding."
                ),
                extra_properties={
                    "thesis": {
                        "type": "string",
                        "description": "The primary position to be defended and challenged.",
                    },
                    "antithesis": {
                        "type": "string",
                        "description": "The opposing position that challenges the thesis.",
                    },
                },
            ),
            handler=_dialectical_reasoning,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_BLINDSPOT_CHECK,
                name="blindspot_check",
                description=(
                    "Scan an argument or plan specifically for what is not being discussed. "
                    "Surfaces absent perspectives, invisible stakeholders, ignored time horizons, and embedded assumptions. "
                    "Use after other reasoning lenses to catch what they collectively missed."
                ),
                extra_properties={
                    "domain": {
                        "type": "string",
                        "description": "Domain or context in which to look for characteristic blindspots.",
                    },
                },
            ),
            handler=_blindspot_check,
        ),
        # --- Category 4: Creative & Lateral ---
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_SCAMPER,
                name="scamper",
                description=(
                    "A structured brainstorming method for modifying existing ideas using one of seven operators: "
                    "Substitute, Combine, Adapt, Modify, Put to other use, Eliminate, Reverse. "
                    "Each operator forces a specific type of creative transformation. "
                    "Use when incremental improvement of an existing idea is needed but direct brainstorming is stalled."
                ),
                extra_properties={
                    "action": {
                        "type": "string",
                        "enum": ["substitute", "combine", "adapt", "modify", "put_to_other_use", "eliminate", "reverse"],
                        "description": "The SCAMPER operator to apply.",
                    },
                },
            ),
            handler=_scamper,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_LATERAL_THINKING,
                name="lateral_thinking",
                description=(
                    "Use a completely unrelated word or concept as a forcing function to discover new connections. "
                    "The random stimulus disrupts habitual reasoning patterns and opens unexpected solution paths. "
                    "Use when direct analysis has reached a local optimum and a conceptual reset is needed."
                ),
                extra_properties={
                    "random_stimulus": {
                        "type": "string",
                        "description": "An unrelated concept or word to use as a creative forcing function.",
                    },
                },
            ),
            handler=_lateral_thinking,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_ANALOGY_GENERATION,
                name="analogy_generation",
                description=(
                    "Map the structure of a problem to a completely different industry or discipline. "
                    "Each analogy reveals structural similarities that unlock solution paths invisible from within the original domain. "
                    "Use when domain-specific expertise has been exhausted and cross-domain insights are needed."
                ),
                extra_properties={
                    "target_domain": {
                        "type": "string",
                        "description": "The unrelated domain to map the problem structure onto.",
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of distinct analogies to generate.",
                    },
                },
            ),
            handler=_analogy_generation,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_MORPHOLOGICAL_ANALYSIS,
                name="morphological_analysis",
                description=(
                    "Break a problem into independent dimensions and force combinations of attributes to generate novel solutions. "
                    "Systematically explores the entire design space rather than converging prematurely. "
                    "Use when the solution space is large and conventional search has missed viable combinations."
                ),
                extra_properties={
                    "dimensions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "The problem dimensions to populate with alternative attribute values.",
                    },
                },
            ),
            handler=_morphological_analysis,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_WORST_IDEA_GENERATION,
                name="worst_idea_generation",
                description=(
                    "Intentionally brainstorm the worst, most counterproductive solutions, then invert them. "
                    "Bypasses mental blocks by removing the pressure to be correct. "
                    "Use when conventional brainstorming is producing only safe, incremental ideas."
                ),
                extra_properties={
                    "constraints": {
                        "type": "string",
                        "description": "Any constraints the inverted ideas must still respect.",
                    },
                },
            ),
            handler=_worst_idea_generation,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_PROVOCATION_OPERATION,
                name="provocation_operation",
                description=(
                    "State something deliberately illogical or impossible as a stepping stone to new ideas. "
                    "The provocation is not meant to be believed — it disrupts habitual thought to open new pathways. "
                    "Based on Edward de Bono's PO (Provocative Operation) technique. "
                    "Use when logic has exhausted the obvious options and a conceptual disruption is needed."
                ),
                extra_properties={
                    "stepping_stone": {
                        "type": "string",
                        "description": "The deliberately illogical or impossible statement to use as the provocative stepping stone.",
                    },
                },
            ),
            handler=_provocation_operation,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_ROLE_STORMING,
                name="role_storming",
                description=(
                    "Brainstorm fully in character as a specific role, person, or archetype. "
                    "Generates ideas that the agent's default perspective would never produce. "
                    "Use when diversity of perspective is needed and direct brainstorming produces homogeneous output."
                ),
                extra_properties={
                    "role": {
                        "type": "string",
                        "description": "The role, person, or archetype to adopt while brainstorming.",
                    },
                },
            ),
            handler=_role_storming,
        ),
        # --- Category 5: Systems & Complexity ---
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_SECOND_ORDER_EFFECTS,
                name="second_order_effects",
                description=(
                    "Analyze not just the immediate consequence of an action, but the consequence of the consequence. "
                    "First-order thinking is intuitive; second-order thinking is where counterintuitive insights live. "
                    "Use before any decision with significant downstream impact to avoid unintended consequences."
                ),
                extra_properties={
                    "time_horizon": {
                        "type": "string",
                        "description": "The time window over which to trace downstream effects.",
                    },
                },
            ),
            handler=_second_order_effects,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_FEEDBACK_LOOP_IDENTIFICATION,
                name="feedback_loop_identification",
                description=(
                    "Look for runaway reinforcing cycles or self-correcting balancing mechanisms within a process or system. "
                    "Feedback loops explain why systems behave differently from their component parts. "
                    "Use when a system is behaving unexpectedly and linear cause-effect analysis has failed to explain it."
                ),
                extra_properties={
                    "loop_type": {
                        "type": "string",
                        "enum": ["balancing", "reinforcing"],
                        "description": "Focus on balancing loops (self-correcting) or reinforcing loops (self-amplifying).",
                    },
                },
            ),
            handler=_feedback_loop_identification,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_CYNEFIN_CATEGORIZATION,
                name="cynefin_categorization",
                description=(
                    "Determine which Cynefin domain the situation belongs to — Clear, Complicated, Complex, or Chaotic — "
                    "and apply the problem-solving approach that domain prescribes. "
                    "Using best practices in a complex domain, or experimental probing in a clear domain, leads to failure. "
                    "Use at the start of any problem to avoid mismatched reasoning strategies."
                ),
                extra_properties={
                    "domain_force": {
                        "type": "string",
                        "enum": ["clear", "complicated", "complex", "chaotic"],
                        "description": "Force the classification into a specific Cynefin domain instead of deriving it.",
                    },
                },
            ),
            handler=_cynefin_categorization,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_NETWORK_MAPPING,
                name="network_mapping",
                description=(
                    "Map how different nodes — people, concepts, systems, or organizations — are connected "
                    "and how information, resources, or influence flows between them. "
                    "Reveals structural properties like hubs, bridges, and isolated clusters. "
                    "Use when understanding the relational structure of a system is as important as understanding its components."
                ),
                extra_properties={
                    "degree_of_separation": {
                        "type": "integer",
                        "description": "How many hops to trace from the central entity when mapping connections.",
                    },
                },
            ),
            handler=_network_mapping,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_BUTTERFLY_EFFECT_TRACE,
                name="butterfly_effect_trace",
                description=(
                    "Take a minor variable change and extrapolate how it could cascade into a major system-wide impact. "
                    "Traces amplifying feedback, threshold effects, and non-linear dynamics. "
                    "Use when a small decision or change has been dismissed as inconsequential "
                    "but may interact with the broader system in ways that are not immediately obvious."
                ),
                extra_properties={
                    "max_steps": {
                        "type": "integer",
                        "description": "Maximum number of causal steps to trace through the system.",
                    },
                },
            ),
            handler=_butterfly_effect_trace,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_BOTTLENECK_IDENTIFICATION,
                name="bottleneck_identification",
                description=(
                    "Identify the single step in a pipeline or process that dictates the maximum throughput of the entire system. "
                    "Based on the Theory of Constraints: the output of the whole system is bounded by its weakest link. "
                    "Use when a process is underperforming and it is unclear which stage to optimize first."
                ),
                extra_properties={
                    "metric": {
                        "type": "string",
                        "description": "The performance metric the bottleneck is constraining (e.g., throughput, latency, cost).",
                    },
                },
            ),
            handler=_bottleneck_identification,
        ),
        # --- Category 6: Temporal & Forecasting ---
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_SCENARIO_PLANNING,
                name="scenario_planning",
                description=(
                    "Generate multiple divergent, plausible futures based on how key uncertainty variables resolve. "
                    "Scenarios are not predictions — they are structured stories that force strategy to be robust across multiple futures. "
                    "Use when the future is genuinely uncertain and strategy must be resilient to multiple outcomes."
                ),
                extra_properties={
                    "variables": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key uncertainty variables that will define which scenario unfolds.",
                    },
                    "timeline": {
                        "type": "string",
                        "description": "The time horizon over which scenarios are projected.",
                    },
                },
            ),
            handler=_scenario_planning,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_PRE_MORTEM,
                name="pre_mortem",
                description=(
                    "Assume a plan has already failed spectacularly and work backward to figure out what killed it. "
                    "Surfaces risks that optimism and groupthink would otherwise suppress. "
                    "Use before committing to a plan to identify the most likely failure modes while there is still time to address them."
                ),
                extra_properties={
                    "failure_mode": {
                        "type": "string",
                        "description": "The specific type of failure to assume has already occurred.",
                    },
                },
            ),
            handler=_pre_mortem,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_POST_MORTEM,
                name="post_mortem",
                description=(
                    "Analyze a past event — success or failure — to extract highly specific, actionable lessons. "
                    "Distinguishes what was within control from what was not. "
                    "Use after any significant outcome to convert experience into durable organizational knowledge."
                ),
                extra_properties={
                    "retrospective_focus": {
                        "type": "string",
                        "description": "The specific aspect of the event to focus the retrospective analysis on.",
                    },
                },
            ),
            handler=_post_mortem,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_TREND_EXTRAPOLATION,
                name="trend_extrapolation",
                description=(
                    "Take current data points and project them into the future, assuming no disruptive changes. "
                    "Establishes a baseline trajectory against which disruptions and interventions can be measured. "
                    "Use when you need a default forecast before layering in assumptions about change."
                ),
                extra_properties={
                    "time_delta": {
                        "type": "string",
                        "description": "The time window to project current trends forward across.",
                    },
                },
            ),
            handler=_trend_extrapolation,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_BACKCASTING,
                name="backcasting",
                description=(
                    "Define a highly specific, ideal future state and trace the exact steps backward to the present day. "
                    "Unlike forecasting, which extrapolates from today, backcasting starts from the desired future. "
                    "Use when you know what success looks like but not how to get there."
                ),
                extra_properties={
                    "steps_backward": {
                        "type": "integer",
                        "description": "Number of backward steps to trace from the future state to the present.",
                    },
                },
            ),
            handler=_backcasting,
        ),
        # --- Category 7: Evaluative & Corrective ---
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_SELF_CRITIQUE,
                name="self_critique",
                description=(
                    "Review prior output as a skeptical peer reviewer, actively searching for logical fallacies, "
                    "unsupported claims, missed instructions, and internal contradictions. "
                    "The agent evaluates its own reasoning rather than proceeding with unjustified confidence. "
                    "Use after any substantial reasoning pass to prevent compounding errors."
                ),
                extra_properties={
                    "prior_output": {
                        "type": "string",
                        "description": "The previous reasoning or output to review critically.",
                    },
                    "rigor_level": {
                        "type": "integer",
                        "description": "1–10 scale: 1 notes only obvious errors, 10 treats every sentence as suspect.",
                    },
                },
            ),
            handler=_self_critique,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_BIAS_DETECTION,
                name="bias_detection",
                description=(
                    "Scan reasoning for cognitive biases including confirmation bias, anchoring, availability heuristic, "
                    "sunk cost fallacy, and survivorship bias. "
                    "Names each bias, quotes the affected reasoning, and estimates its impact on the conclusion. "
                    "Use when a reasoning chain has reached a suspiciously convenient conclusion."
                ),
                extra_properties={
                    "bias_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific cognitive biases to scan for. If empty, scans for common biases.",
                    },
                },
            ),
            handler=_bias_detection,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_FACT_CHECKING,
                name="fact_checking",
                description=(
                    "Isolate objective claims within reasoning and evaluate their probability of being true "
                    "based on training knowledge and internal consistency. "
                    "Classifies claims as factual, opinion, or mixed, and flags low-confidence assertions. "
                    "Use before presenting conclusions that depend on empirical claims."
                ),
                extra_properties={
                    "claims": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific claims to evaluate. If empty, claims are extracted from the intent.",
                    },
                    "strictness": {
                        "type": "number",
                        "description": "0.0 accepts plausible claims; 1.0 demands strong evidence for every claim.",
                    },
                },
            ),
            handler=_fact_checking,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_CONFIDENCE_CALIBRATION,
                name="confidence_calibration",
                description=(
                    "Output a calibrated percentage of certainty alongside an assertion, then justify that percentage. "
                    "Separates what is known from what is inferred. Resists both overconfidence and epistemic cowardice. "
                    "Use when the agent must make a probabilistic claim and the uncertainty should be explicit."
                ),
                extra_properties={
                    "evidence_weight": {
                        "type": "number",
                        "description": "0.0 = no supporting evidence available; 1.0 = overwhelming supporting evidence.",
                    },
                },
            ),
            handler=_confidence_calibration,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_TRADEOFF_EVALUATION,
                name="tradeoff_evaluation",
                description=(
                    "Systematically compare two viable paths, acknowledging that neither is perfect "
                    "and making explicit what must be sacrificed when choosing one over the other. "
                    "Prevents false dichotomies and forces acknowledgment of the true cost of each option. "
                    "Use when a decision involves two genuinely viable alternatives with different strengths."
                ),
                extra_properties={
                    "option_a": {
                        "type": "string",
                        "description": "Description of the first option.",
                    },
                    "option_b": {
                        "type": "string",
                        "description": "Description of the second option.",
                    },
                    "criteria": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Evaluation criteria to use when comparing the two options.",
                    },
                },
            ),
            handler=_tradeoff_evaluation,
        ),
        # --- Category 8: Scientific & Empirical ---
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_HYPOTHESIS_GENERATION,
                name="hypothesis_generation",
                description=(
                    "Create testable, falsifiable explanations for a given observation or question. "
                    "Each hypothesis must be specific, directional, and meaningfully distinct from the others. "
                    "Use when an observation needs multiple competing explanations before committing to one."
                ),
                extra_properties={
                    "count": {
                        "type": "integer",
                        "description": "Number of distinct hypotheses to generate.",
                    },
                },
            ),
            handler=_hypothesis_generation,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_FALSIFICATION_TEST,
                name="falsification_test",
                description=(
                    "Determine what specific, observable evidence would be required to disprove a theory. "
                    "Grounds reasoning in Popperian epistemology: an unfalsifiable claim is not a scientific claim. "
                    "Use to stress-test theories and identify what observations would force the agent to revise its conclusions."
                ),
                extra_properties={
                    "test_conditions": {
                        "type": "string",
                        "description": "The empirical or experimental conditions under which falsification tests should be designed.",
                    },
                },
            ),
            handler=_falsification_test,
        ),
        RegisteredTool(
            definition=_build_definition(
                key=REASONING_ABDUCTIVE_REASONING,
                name="abductive_reasoning",
                description=(
                    "Infer the simplest and most likely explanation that accounts for all available evidence. "
                    "Inference to the best explanation: neither deductive certainty nor inductive generalization, "
                    "but the most coherent and parsimonious account of what is observed. "
                    "Use when you have partial evidence and need the most defensible conclusion before more data is available."
                ),
                extra_properties={
                    "evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Available evidence items to reason from.",
                    },
                },
            ),
            handler=_abductive_reasoning,
        ),
    )


__all__ = ["create_reasoning_tools"]
