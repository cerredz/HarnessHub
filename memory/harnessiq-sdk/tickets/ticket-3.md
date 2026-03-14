Title: Document minimal SDK installation and example usage
Issue URL: Not created; `gh` is unavailable in this environment.

Intent: Give external users just enough documentation to install `Harnessiq` and start using the supported agents and tool layer without needing to reverse-engineer the repo.

Scope:
- Add minimal installation instructions.
- Add a few concise example documents covering tool usage, agent usage, and at least one first-class concrete agent surface.
- Keep docs lightweight and SDK-focused.
- Do not create a large documentation site or full extension guide.

Relevant Files:
- `README.md`: add install instructions and a brief SDK overview.
- `docs/` or `examples/` markdown files: add a few targeted usage examples.

Approach:
- Keep the README short and oriented around install plus import examples.
- Add separate example docs so the README does not become overloaded.
- Ensure examples use the stable `harnessiq` import path and first-class exported surfaces.
- Prefer examples that demonstrate both tool composition and concrete agent instantiation.

Assumptions:
- Minimal docs plus a few examples are sufficient for this pass.
- The examples should reflect the curated public API from Tickets 1 and 2, not internal implementation modules.

Acceptance Criteria:
- [ ] The README explains what `Harnessiq` is and how to install it.
- [ ] The README includes at least one short import/usage example using `harnessiq`.
- [ ] Additional example docs cover tool usage and agent usage.
- [ ] At least one example covers a first-class concrete agent export.
- [ ] The documented imports match the implemented SDK surface.

Verification Steps:
- Static analysis: manually review examples for consistency with the implemented package surface.
- Type checking: no configured type checker; validate examples against the real imports and call signatures.
- Unit tests: run the full test suite to ensure docs-driven API assumptions remain accurate.
- Integration and contract tests: use smoke verification to import the documented symbols.
- Smoke/manual verification: execute or mentally trace each documented import example against the implemented SDK surface.

Dependencies: Ticket 1, Ticket 2.

Drift Guard: This ticket must not add broad product marketing copy, a docs framework, or unrelated tutorials. It should stay focused on installation and a few practical SDK examples.
