Title: Add the Paperclip provider core

Intent:
Introduce a first-class Paperclip provider package that models Paperclip’s JSON control-plane API in the same style as the existing Harnessiq providers, so higher layers can consume it without ad hoc HTTP logic.

Issue URL:
https://github.com/cerredz/HarnessHub/issues/166

Scope:
- Add `harnessiq.providers.paperclip` with API helpers, credentials, client, operation catalog, and public exports.
- Cover the curated JSON-first Paperclip surface: companies, agents, issues, approvals, activity, and costs.
- Add focused provider tests for credentials, catalog lookup, request preparation, auth headers, and client/tool execution paths.
- Do not implement multipart upload endpoints for attachments or company logos in this ticket.
- Do not change agent runtime behavior in Harnessiq.

Relevant Files:
- `harnessiq/providers/paperclip/__init__.py`: curated public exports for the new provider family.
- `harnessiq/providers/paperclip/api.py`: Paperclip base URL and auth header helpers.
- `harnessiq/providers/paperclip/client.py`: `PaperclipCredentials` and `PaperclipClient`.
- `harnessiq/providers/paperclip/operations.py`: declarative operation catalog and prepared-request assembly.
- `tests/test_paperclip_provider.py`: provider-focused unit tests.

Approach:
Mirror the strongest existing provider pattern used by Exa/Creatify/Google Drive. Define a declarative `PaperclipOperation` model that captures HTTP method, path template, required path params, query support, payload rules, and whether `X-Paperclip-Run-Id` is meaningful. Keep the transport JSON-only and let multipart endpoints remain intentionally unsupported. Accept a bearer token through `PaperclipCredentials`, with `base_url` defaulting to Paperclip’s documented local API root. Validate inputs locally and return prepared requests with resolved paths and headers.

Assumptions:
- The upstream Paperclip REST docs in `master` are the source of truth for the supported endpoint set.
- A bearer token is sufficient for Harnessiq usage; session-cookie board auth is out of scope.
- JSON endpoints provide the highest-value initial integration and align with current Harnessiq transport abstractions.

Acceptance Criteria:
- [ ] `harnessiq.providers.paperclip` exists and is importable.
- [ ] Paperclip credentials validate blank token/base URL/timeout inputs consistently with existing providers.
- [ ] The Paperclip operation catalog includes the curated JSON endpoint set for companies, agents, issues, approvals, activity, and costs.
- [ ] `PaperclipClient.prepare_request()` resolves paths, query parameters, payloads, and headers correctly.
- [ ] Mutating operations can include `X-Paperclip-Run-Id` when provided.
- [ ] Provider tests cover happy paths and key failure modes for credential validation, unknown operations, missing path params, and invalid payload usage.

Verification Steps:
- Run focused provider tests for `tests/test_paperclip_provider.py`.
- Run any related provider catalog/tool execution tests impacted by the new provider.
- Smoke-check imports from `harnessiq.providers.paperclip`.

Dependencies:
- None

Drift Guard:
This ticket must not add the provider to the public tool catalog yet, must not introduce multipart upload support, and must not reach into agent runtime code. It is limited to the provider-layer contract and its direct tests.
