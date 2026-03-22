Issue URL: https://github.com/cerredz/HarnessHub/issues/178

Title: Centralize provider endpoint constants and provider credential/config definitions under shared

Intent:
Make `harnessiq/shared/` the single source of truth for provider-side endpoint/config constants and provider credential/config dataclasses, including providers that currently keep those definitions inline inside `api.py` or `client.py`.

Scope:
- Move remaining provider endpoint/version/token/scope/mime constants into shared definitions.
- Move provider credential/config dataclasses out of provider `client.py` files and into shared modules.
- Update provider `api.py` and `client.py` files to import these definitions from `harnessiq/shared/`.
- Preserve public provider package exports by re-exporting from existing package surfaces where required.
- Do not move behavior-heavy client methods or request-execution logic into `shared/`.

Relevant Files:
- `harnessiq/shared/providers.py`: extend the generic shared provider constant surface with any remaining default endpoint/version constants.
- `harnessiq/shared/arcads.py`: create the shared home for Arcads credentials/config definitions.
- `harnessiq/shared/attio.py`: create the shared home for Attio constants and credentials/config definitions.
- `harnessiq/shared/creatify.py`: create the shared home for Creatify credentials/config definitions.
- `harnessiq/shared/exa.py`: create the shared home for Exa credentials/config definitions.
- `harnessiq/shared/google_drive.py`: create or expand the shared home for Google Drive provider definitions if constants/configs need a provider-specific shared module.
- `harnessiq/shared/inboxapp.py`: create the shared home for InboxApp constants and credentials/config definitions.
- `harnessiq/shared/instantly.py`: create the shared home for Instantly credentials/config definitions.
- `harnessiq/shared/lemlist.py`: create the shared home for Lemlist credentials/config definitions.
- `harnessiq/shared/outreach.py`: create the shared home for Outreach credentials/config definitions.
- `harnessiq/shared/paperclip.py`: create the shared home for Paperclip constants and credentials/config definitions.
- `harnessiq/shared/serper.py`: create the shared home for Serper constants and credentials/config definitions.
- `harnessiq/providers/arcads/api.py`: import endpoint constants from shared definitions.
- `harnessiq/providers/arcads/client.py`: import Arcads credentials/config from shared definitions.
- `harnessiq/providers/attio/api.py`: import endpoint constants from shared definitions.
- `harnessiq/providers/attio/client.py`: import Attio credentials/config from shared definitions.
- `harnessiq/providers/creatify/client.py`: import Creatify credentials/config from shared definitions.
- `harnessiq/providers/exa/client.py`: import Exa credentials/config from shared definitions.
- `harnessiq/providers/google_drive/api.py`: import any moved Google Drive constants from shared definitions.
- `harnessiq/providers/google_drive/client.py`: import Google Drive credentials/config from shared definitions if moved.
- `harnessiq/providers/inboxapp/api.py`: import endpoint constants from shared definitions.
- `harnessiq/providers/inboxapp/client.py`: import InboxApp credentials/config from shared definitions.
- `harnessiq/providers/instantly/client.py`: import Instantly credentials/config from shared definitions.
- `harnessiq/providers/lemlist/client.py`: import Lemlist credentials/config from shared definitions.
- `harnessiq/providers/outreach/client.py`: import Outreach credentials/config from shared definitions.
- `harnessiq/providers/paperclip/api.py`: import endpoint constants from shared definitions.
- `harnessiq/providers/paperclip/client.py`: import Paperclip credentials/config from shared definitions.
- `harnessiq/providers/serper/api.py`: import endpoint constants from shared definitions.
- `harnessiq/providers/serper/client.py`: import Serper credentials/config from shared definitions.
- `harnessiq/providers/<provider>/__init__.py`: preserve public exports for any moved constants/configs.
- `tests/test_arcads_provider.py`: update imports/assertions if constant/config ownership changes.
- `tests/test_attio_provider.py`: update imports/assertions if constant/config ownership changes.
- `tests/test_creatify_provider.py`: update imports/assertions if constant/config ownership changes.
- `tests/test_exa_provider.py`: update imports/assertions if constant/config ownership changes.
- `tests/test_google_drive_provider.py`: update imports/assertions if constant/config ownership changes.
- `tests/test_instantly_provider.py`: update imports/assertions if constant/config ownership changes.
- `tests/test_lemlist_provider.py`: update imports/assertions if constant/config ownership changes.
- `tests/test_outreach_provider.py`: update imports/assertions if constant/config ownership changes.
- `tests/test_paperclip_provider.py`: update imports/assertions if constant/config ownership changes.

Approach:
Use small provider-specific modules in `harnessiq/shared/` for definitions that are too large or provider-specific to belong in the generic `shared/providers.py` file. Keep `shared/providers.py` focused on generic aliases and cross-provider constants, while each provider-specific shared module becomes the home for that providerâ€™s endpoint defaults and credential/config dataclass. Update provider packages to re-export from those shared definitions so the public API remains stable.

Assumptions:
- Provider credential/config dataclasses are considered shared architectural definitions even when currently used by only one provider package.
- Creating provider-specific shared modules is preferable to turning `shared/providers.py` into a monolith.
- Behavior-heavy client methods remain in provider packages.

Acceptance Criteria:
- [ ] No provider package keeps default endpoint/version/scope/token constants inline when they belong in `harnessiq/shared/`.
- [ ] No standalone provider credential/config dataclass remains defined in a provider `client.py`.
- [ ] Provider package public exports continue to expose the moved constants/configs.
- [ ] Targeted provider tests covering the touched providers pass.

Verification Steps:
- Run targeted provider tests for every provider touched by this ticket.
- Run import smoke checks for each touched provider package and package-level exports.
- Run SDK package-surface tests that cover provider exports.

Dependencies:
- Ticket 1 is independent, but this ticket can proceed without it.

Drift Guard:
This ticket must not redesign provider clients, alter request payload semantics, or change tool behavior. It is limited to relocating definition ownership for constants and config dataclasses while preserving behavior and package imports.

