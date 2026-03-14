## Harnessiq SDK Clarifications

### Open Questions

1. Import and distribution identity
   - Ambiguity: the task names the SDK `Harnessiq`, but the repo currently uses `src.*` imports and `HarnessHub` naming in docs/comments.
   - Why it matters: this determines whether I should do a full package rename, create a stable `harnessiq` facade over the current code, or keep internal names and only change packaging metadata.
   - Options:
     - A. External users import `harnessiq.*`, while internal implementation may remain under the current source tree if needed.
     - B. Rename the codebase package/import root itself to `harnessiq.*` everywhere.
     - C. Keep `src.*` internally and expose only a thin installable `harnessiq` wrapper for users.

2. Public SDK surface
   - Ambiguity: “agents and injectible tools (core functionalities), and just this repo in general” can be interpreted narrowly or broadly.
   - Why it matters: this decides which modules become supported public API and which remain internal implementation details.
   - Options:
     - A. Expose curated public modules only: `harnessiq.agents`, `harnessiq.tools`, `harnessiq.providers`, and selected shared runtime types.
     - B. Expose nearly all existing modules as public SDK surface.
     - C. Expose only the agent/tool layer now and keep providers/shared internals mostly private.

3. Concrete agent support level
   - Ambiguity: should existing concrete harnesses like `LinkedInJobApplierAgent` and `BaseEmailAgent` be first-class supported SDK features, or examples/reference implementations built on top of the reusable runtime?
   - Why it matters: this changes how much I stabilize/document those APIs versus keeping the SDK centered on primitives and composition.
   - Options:
     - A. Treat current agents as first-class supported SDK exports.
     - B. Treat them as reference implementations/examples, with the runtime/tool abstractions as the primary SDK.
     - C. Support both, but document the primitives as the main extension point.

4. Packaging target
   - Ambiguity: the task asks to “setup the SDK” but does not say whether you want local editable installs only or a package layout suitable for publishing.
   - Why it matters: this determines packaging metadata completeness, versioning expectations, and whether I should optimize for `pip install -e .` only or for eventual private/public distribution.
   - Options:
     - A. Optimize for local repo installs and immediate developer consumption.
     - B. Make it publication-ready for a private package index/GitHub Packages.
     - C. Make it publication-ready for PyPI-style distribution.

5. Examples and docs depth
   - Ambiguity: external usability depends heavily on docs, but the task does not specify the minimum acceptable onboarding surface.
   - Why it matters: the difference between “installable package exists” and “people can actually use it” is usually example-driven documentation.
   - Options:
     - A. Minimal: install instructions plus one short usage example.
     - B. Practical: install instructions plus examples for using tools, composing an agent, and using an existing concrete harness.
     - C. Broad: practical docs plus packaging/versioning guidance and extension patterns.

### Responses

1. Import and distribution identity
   - Response: rename the internal package to match `harnessiq`.

2. Public SDK surface
   - Response: focus the public SDK on agents and tools, while still enabling the agents to use the provider-backed capabilities they currently rely on.

3. Concrete agent support level
   - Response: existing concrete agents should be first-class supported SDK exports.

4. Packaging target
   - Response: package it for PyPI-style distribution.

5. Examples and docs depth
   - Response: provide minimal install docs plus a few example usage docs.

### Implications

- The implementation should do a real package rename from `src` to `harnessiq`, not just add a facade layer.
- The stable public API should be curated around:
  - `harnessiq.agents`
  - `harnessiq.tools`
  - supporting runtime types needed to use those layers successfully
- Provider modules do not need to be marketed as the primary SDK surface, but the SDK must still ship the provider support code the agents/tools rely on.
- Concrete agent exports such as `LinkedInJobApplierAgent` and `BaseEmailAgent` should remain directly importable from the SDK package.
- Packaging work should target a standard Python build backend and wheel/sdist friendly layout suitable for `pip install harnessiq`.
- Documentation should cover:
  - package installation,
  - basic tool-registry usage,
  - basic agent usage,
  - using at least one concrete first-class agent surface.
