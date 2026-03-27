Title: Add the core evaluation package scaffold

Intent:
Create a first-class `harnessiq.evaluations` runtime surface that establishes the repository’s long-term evaluation architecture without locking the codebase into a heavyweight execution model too early.

Scope:
- Create the new `harnessiq/evaluations/` package.
- Add shared evaluation data models, registry primitives, and baseline metrics utilities.
- Add category-oriented subpackages so future evaluations are grouped by behavior.
- Do not add live model integrations, CI runners, or external tracing integrations.

Relevant Files:
- `harnessiq/evaluations/__init__.py`: public export surface for evaluation primitives.
- `harnessiq/evaluations/models.py`: typed data models for evaluation inputs and outcomes.
- `harnessiq/evaluations/registry.py`: case/spec registration helpers.
- `harnessiq/evaluations/metrics.py`: basic correctness/efficiency metric helpers.
- `harnessiq/evaluations/boilerplate.py`: ergonomic constructors for future evaluation cases.
- `harnessiq/evaluations/correctness/*`: correctness category scaffold.
- `harnessiq/evaluations/tool_use/*`: tool-use category scaffold.
- `harnessiq/evaluations/efficiency/*`: efficiency category scaffold.
- `harnessiq/evaluations/output/*`: output-quality category scaffold.

Approach:
Introduce a small, typed domain model that can describe an evaluation run independently of any specific runner. Expose category packages and simple registry helpers so future evals can be added as composable callables with metadata, docstrings, and tags.

Assumptions:
- Evaluation cases should remain plain Python callables for now.
- Category separation should reflect behaviors the team cares about in production, not data provenance.

Acceptance Criteria:
- [ ] `harnessiq/evaluations/` exists as a public package.
- [ ] Shared evaluation models and registry primitives are available for future extension.
- [ ] Category subpackages exist and make the intended taxonomy obvious.
- [ ] The package avoids coupling to a specific external evaluation service.

Verification Steps:
- Run targeted tests covering the new evaluation models and package surface.
- Import the new package directly from Python and confirm expected exports resolve.

Dependencies:
- None.

Drift Guard:
This ticket must not introduce a real benchmark corpus, external network dependencies, or a production runner. It establishes architecture and reusable primitives only.
