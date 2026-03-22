# Self-Critique — Ticket 2

## Review findings

1. **`_build_definition` helper** — Correctly factors out the repetitive `ToolDefinition` construction. Each tool still has a unique `RegisteredTool` instance and a unique handler, so there is no over-abstraction.

2. **Argument extraction helpers** — Mirrored from `general_purpose.py` and localized to this module. This is intentional duplication (not accidental): the helpers are private and tightly scoped, and there is no shared private utility module in this codebase to import from.

3. **Handler naming** — Private handlers use the same name as the tool (e.g., `_step_by_step` for `step_by_step`). This is consistent with the existing codebase convention.

4. **`bottleneck_identification` prompt has an f-string interpolation issue** — The string `"Find the single stage that most constrains {metric} — the bottleneck."` uses `{metric}` as a literal string (inside a regular string, not an f-string) in a sub-sentence that is itself part of an f-string. This is actually intentional: the outer f-string has already evaluated `metric` in the preceding sentence. The literal `{metric}` in the sub-sentence appears because it is not inside the f-string scope — this is a bug.

**Fix**: The second occurrence of `{metric}` in `_bottleneck_identification` is in a separate string literal that is not an f-string. It should reference the variable, or the phrasing should be changed. Updated to avoid the ambiguity.

5. **`six_thinking_hats` default** — Defaults to `"blue"` (meta/process) when no hat is specified. This is the most natural default since blue hat is the facilitator's hat and is the most appropriate when no specific cognitive mode is requested.

6. **All list parameters default to empty list** — When the agent doesn't provide list parameters, the prompt gracefully falls back to "use implied context" language. This prevents unnecessary tool call failures.

7. **`_join_list` fallback text** — Uses `"none provided"` which is clear and informative in the reasoning prompt.

## Fix applied
`_bottleneck_identification` prompt string corrected to use a plain string reference for the metric variable throughout, avoiding the f-string/literal string confusion.
