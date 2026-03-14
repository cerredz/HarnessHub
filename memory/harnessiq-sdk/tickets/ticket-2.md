Title: Add PyPI-style packaging metadata and installation smoke coverage
Issue URL: Not created; `gh` is unavailable in this environment.

Intent: Convert the renamed `harnessiq` package into a buildable, installable SDK distribution suitable for wheel/sdist-based consumption.

Scope:
- Add standard Python packaging metadata and package discovery.
- Define the runtime dependency set required by the SDK.
- Add packaging/install smoke coverage that validates the built package can be imported as `harnessiq`.
- Do not expand the documentation beyond packaging-adjacent installation details required by the build.

Relevant Files:
- `pyproject.toml`: define the build backend, project metadata, dependencies, and package inclusion rules.
- `README.md`: provide packaging-facing summary text suitable for the project metadata long description and install snippet.
- `tests/` or a new packaging smoke test module: validate that the package imports correctly from the installed/buildable layout.
- Optional packaging support files if required by the chosen backend.

Approach:
- Use a standard, minimal PyPI-friendly build backend with explicit project metadata.
- Package the renamed `harnessiq` source tree as the distribution payload.
- Keep runtime dependencies minimal and aligned with actual imports; treat provider logic as shipped code, not separate packages.
- Add a smoke test that verifies the `harnessiq` package surface imports successfully after the packaging layout is in place.

Assumptions:
- PyPI-style readiness means standard build metadata and wheel/sdist compatibility, not necessarily immediate publication.
- `langsmith` remains the only mandatory third-party runtime dependency in this repo.
- Optional extras are not required unless the implementation reveals a concrete need.

Acceptance Criteria:
- [ ] A `pyproject.toml` exists and can build/package the SDK.
- [ ] The project metadata names the distribution appropriately for `Harnessiq`.
- [ ] The package discovery configuration includes the `harnessiq` source tree.
- [ ] The README includes installation guidance appropriate for the package metadata.
- [ ] Automated verification covers import/install smoke behavior for the packaged SDK.

Verification Steps:
- Static analysis: manually review packaging metadata for correctness; no linter is configured.
- Type checking: no configured type checker; verify package importability through tests/build output.
- Unit tests: run the full test suite with the packaging changes in place.
- Integration and contract tests: build the package and verify `harnessiq` imports from the resulting distribution context or equivalent smoke check.
- Smoke/manual verification: run `python -m build` and inspect that wheel/sdist generation completes successfully.

Dependencies: Ticket 1.

Drift Guard: This ticket must not redesign agent/tool APIs or broaden the docs into a full developer guide. It is strictly about making the SDK buildable and installable in a standard Python packaging workflow.
