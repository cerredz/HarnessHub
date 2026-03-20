Issue URL: https://github.com/cerredz/HarnessHub/issues/179

PR URL: https://github.com/cerredz/HarnessHub/pull/190

Title: Centralize provider operation metadata and prepared-request types for provider-backed tool surfaces

Intent:
Move provider operation metadata definitions out of provider `operations.py` modules and into `harnessiq/shared/` so request catalogs, operation dataclasses, payload-kind aliases, and prepared-request dataclasses all follow the shared-definition rule.

Scope:
- Move provider operation metadata dataclasses, payload-kind aliases, and operation catalogs into shared modules.
- Move prepared-request dataclasses into shared modules where they are definition-only.
- Keep request-building/validation logic in provider `operations.py`.
- Update provider tools and provider packages to import their operation metadata from the new shared source-of-truth.
- Preserve existing tool names, operation names, request validation behavior, and public exports.

Relevant Files:
- `harnessiq/shared/arcads.py`: add Arcads operation metadata definitions and catalog.
- `harnessiq/shared/attio.py`: add Attio operation metadata definitions and catalog.
- `harnessiq/shared/coresignal.py`: create or expand the shared home for CoreSignal operation metadata.
- `harnessiq/shared/creatify.py`: add Creatify operation metadata definitions and catalog.
- `harnessiq/shared/exa.py`: add Exa operation metadata definitions and catalog.
- `harnessiq/shared/google_drive.py`: add Google Drive operation metadata definitions if they are still provider-local.
- `harnessiq/shared/inboxapp.py`: add InboxApp operation metadata definitions and catalog.
- `harnessiq/shared/instantly.py`: add Instantly operation metadata definitions and catalog.
- `harnessiq/shared/leadiq.py`: create or expand the shared home for LeadIQ operation metadata.
- `harnessiq/shared/lemlist.py`: add Lemlist operation metadata definitions and catalog.
- `harnessiq/shared/outreach.py`: add Outreach operation metadata definitions and catalog.
- `harnessiq/shared/paperclip.py`: add Paperclip operation metadata definitions and catalog.
- `harnessiq/shared/peopledatalabs.py`: create or expand the shared home for PeopleDataLabs operation metadata.
- `harnessiq/shared/phantombuster.py`: create or expand the shared home for PhantomBuster operation metadata.
- `harnessiq/shared/proxycurl.py`: create or expand the shared home for Proxycurl operation metadata.
- `harnessiq/shared/salesforge.py`: create or expand the shared home for Salesforge operation metadata.
- `harnessiq/shared/snovio.py`: create or expand the shared home for Snovio operation metadata.
- `harnessiq/shared/zoominfo.py`: create or expand the shared home for ZoomInfo operation metadata.
- `harnessiq/providers/<provider>/operations.py`: keep validation/request-preparation logic, but import operation metadata and prepared-request types from shared modules.
- `harnessiq/tools/<provider>/operations.py`: ensure tool definitions/factories source operation metadata through the provider moduleâ€™s updated exports without behavior changes.
- `harnessiq/providers/<provider>/__init__.py`: preserve public exports for moved operation metadata types/catalog helpers.
- `tests/test_arcads_provider.py`: update coverage for the shared operation metadata source-of-truth.
- `tests/test_attio_provider.py`: update coverage for the shared operation metadata source-of-truth.
- `tests/test_coresignal_provider.py`: update coverage for the shared operation metadata source-of-truth.
- `tests/test_creatify_provider.py`: update coverage for the shared operation metadata source-of-truth.
- `tests/test_exa_provider.py`: update coverage for the shared operation metadata source-of-truth.
- `tests/test_google_drive_provider.py`: update coverage for the shared operation metadata source-of-truth.
- `tests/test_instantly_provider.py`: update coverage for the shared operation metadata source-of-truth.
- `tests/test_leadiq_provider.py`: update coverage for the shared operation metadata source-of-truth.
- `tests/test_lemlist_provider.py`: update coverage for the shared operation metadata source-of-truth.
- `tests/test_outreach_provider.py`: update coverage for the shared operation metadata source-of-truth.
- `tests/test_paperclip_provider.py`: update coverage for the shared operation metadata source-of-truth.
- `tests/test_peopledatalabs_provider.py`: update coverage for the shared operation metadata source-of-truth.
- `tests/test_phantombuster_provider.py`: update coverage for the shared operation metadata source-of-truth.
- `tests/test_proxycurl_provider.py`: update coverage for the shared operation metadata source-of-truth.
- `tests/test_salesforge_provider.py`: update coverage for the shared operation metadata source-of-truth.
- `tests/test_snovio_provider.py`: update coverage for the shared operation metadata source-of-truth.
- `tests/test_zoominfo_provider.py`: update coverage for the shared operation metadata source-of-truth.

Approach:
Separate pure metadata from execution logic. Each provider-specific shared module should own the declarative operation catalog and any associated immutable types (`PayloadKind`, `*Operation`, `*PreparedRequest`), while provider `operations.py` remains the home for validation, path/query normalization, and request assembly. Where a provider already has a small amount of metadata, prefer expanding a provider-specific shared module instead of introducing a generic mega-module.

Assumptions:
- Prepared-request dataclasses are considered definition-only shared types because they are immutable data carriers without execution behavior.
- Provider `operations.py` modules can import shared metadata without circular imports if the shared modules do not import provider runtime code.
- Compatibility re-exports from provider packages are required to avoid breaking downstream imports.

Acceptance Criteria:
- [ ] Provider operation metadata types and catalogs no longer originate in provider `operations.py` modules.
- [ ] Provider request-preparation behavior remains unchanged apart from import paths.
- [ ] Provider-backed tool factories continue to expose the same tool keys and operation names.
- [ ] Targeted provider and tool tests for the touched providers pass.

Verification Steps:
- Run targeted provider tests for each touched provider family.
- Run targeted tool tests for provider-backed tool factories that depend on moved metadata.
- Run import smoke checks for provider packages and their tool packages.

Dependencies:
- Ticket 2 should land first so provider shared modules already exist for the per-provider definitions.

Drift Guard:
This ticket must not redesign provider APIs, rename operations, or change request validation rules. It is strictly about relocating immutable operation-definition ownership to `harnessiq/shared/` and preserving behavior.

