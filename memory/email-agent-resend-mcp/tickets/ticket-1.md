Title: Add a Resend operation catalog, client, and MCP-style tooling surface
Intent: Give the tooling layer a first-class outbound email/delivery integration that can execute the current Resend API surface through a single authenticated tool, making email operations available to harnesses without embedding HTTP logic in agents.
Scope:
- Add a new `src/tools/resend.py` module with a reusable credentials/client abstraction, an explicit Resend operation catalog, and a `RegisteredTool` factory for the tool layer.
- Cover the current stable Resend capabilities needed for email delivery and adjacent management workflows: emails, batch send, attachments, receiving, domains, API keys, segments/audiences, contacts/contact topics, contact properties, broadcasts, templates, topics, and webhooks.
- Keep the interface fakeable for unit tests through an injectable request executor.
- Do not add the Resend tool to the global built-in registry, since it requires credentials.
Relevant Files:
- `src/tools/resend.py`: new Resend credentials/client/operation catalog/tool factory module.
- `src/tools/__init__.py`: export the new Resend helpers.
- `src/providers/http.py`: improve provider-name inference for Resend-backed transport failures.
- `tests/test_resend_tools.py`: add Resend client/tool coverage with fake executors.
- `tests/test_provider_base.py`: extend shared transport coverage for the Resend host inference change if needed.
Approach: Represent the Resend API as explicit operation descriptors containing the HTTP method, path template, path parameters, payload/query support, and operation metadata. Expose a single `resend.request` tool whose `operation` argument is validated against that catalog and whose handler delegates to a reusable `ResendClient`. Preserve maintainability by centralizing endpoint metadata and using the existing stdlib JSON request executor rather than introducing an SDK dependency.
Assumptions:
- A single MCP-style request tool is the cleanest expression of "all Resend capabilities" in this local tooling runtime.
- Stable/current official Resend capabilities are the target, not speculative future beta endpoints.
- The operation catalog should expose audience aliases even though Audiences are deprecated in favor of Segments, because the user asked for comprehensive API coverage.
Acceptance Criteria:
- [ ] `src/tools/resend.py` exposes a reusable `ResendClient`, explicit operation catalog metadata, and a `create_resend_tools()` factory.
- [ ] The `resend.request` tool can execute send, batch, list, retrieve, update, delete, and auxiliary Resend operations through an injected executor.
- [ ] Send and batch-send flows support Resend-specific headers such as `Idempotency-Key` and `x-batch-validation`.
- [ ] Resend transport failures are labeled as `resend` rather than a generic provider in shared HTTP errors.
- [ ] Unit tests cover representative operations, path/query/payload handling, and failure validation without live network calls.
Verification Steps:
- Run `python -m unittest tests.test_resend_tools tests.test_provider_base`.
- Run `python -m unittest`.
- Manually inspect the exported tooling surface in `src/tools/__init__.py`.
Dependencies: None.
Drift Guard: This ticket must not add a concrete email campaign agent, alter the built-in registry to require credentials, or introduce a third-party Resend SDK dependency. The goal is a reusable local tool/client surface only.
