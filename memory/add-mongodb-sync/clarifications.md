## Phase 2

No meaningful ambiguities remained after Phase 1.

Implementation will proceed with these explicit decisions:
- Add a built-in sink type named `mongodb`.
- Configure it with `connection_uri`, `database`, and `collection`.
- Support optional `explode_field` so array-shaped outputs can be inserted as multiple documents when needed.
- Preserve the existing sink contract where output-sink failures are swallowed and do not change run completion.
