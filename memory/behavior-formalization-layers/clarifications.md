# Clarifications

1. Runtime alignment
   Ambiguity: the design places behavior layers under `harnessiq/interfaces/formalization/behaviors/`, but `BaseAgent` still consumes the legacy `harnessiq.formalization` stack.
   Why it matters: this determines whether I only add the new behavior package, or also migrate/bridge the runtime so `behaviors=` is actually first-class and public imports stay coherent.
   Resolution: redesign the behavior surface to the design doc and bridge the runtime to it.
   Implication: the new behavior package under `harnessiq/interfaces/formalization/behaviors/` becomes the implementation target, and the runtime/public exports should be updated so this package is first-class rather than purely decorative.

2. Argument-aware enforcement
   Ambiguity: the design doc relies on argument-aware enforcement for retries, stuck detection, and scope guards, but current layer hooks only expose tool keys and tool results, not the original `ToolCall`.
   Why it matters: without runtime expansion, several concrete behavior classes cannot be implemented faithfully.
   Resolution: yes, extend the runtime so behavior layers can inspect full `ToolCall` data.
   Implication: I should add a pre-execution and/or richer post-execution hook path that can see tool arguments, rather than approximating retry/stuck/scope behavior from transcript state alone.

3. Constructor sugar scope
   Ambiguity: the design doc adds `behaviors=`, and also references artifact ordering, but those artifact sugar parameters do not currently exist in `BaseAgent`.
   Why it matters: implementing literal ordering semantics may require adjacent artifact-layer constructor work that is not otherwise part of behavior layers.
   Resolution: add only `behaviors=` in this task.
   Implication: I should not add `input_artifacts=` or `output_artifacts=` sugar as adjacent work here.

4. Concrete implementation breadth
   Ambiguity: the module layout names 21 concrete behavior classes across seven categories.
   Why it matters: this changes ticket count, implementation order, and the amount of runtime API expansion required.
   Resolution: implement the full matrix from the design doc.
   Implication: ticketing should cover both the shared runtime foundation and all concrete category implementations.

5. Compatibility surface
   Ambiguity: should the new behavior classes also be exposed through legacy-style import paths such as `harnessiq.formalization`, or only through `harnessiq.interfaces.formalization`?
   Why it matters: backward compatibility affects export changes, tests, and whether I need to bridge the older package.
   Resolution: export through both.
   Implication: the new behavior classes should be available from the newer `interfaces` surface and from legacy-compatible exports where practical.
