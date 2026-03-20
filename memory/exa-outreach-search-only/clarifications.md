## Clarifying Questions

1. Should `search_only=True` make `email_data` and Resend wiring optional, or do you want them to remain required-but-ignored?
   - Why this matters: the current SDK constructor rejects empty `email_data`, and the CLI currently hard-requires both `--resend-credentials-factory` and `--email-data-factory`.
   - Recommended option: make both optional in search-only mode so users can run a pure lead-discovery flow without supplying email assets they will never use.
   - User response: Yes, it should make them optional.

2. For the CLI, do you want `search_only` exposed as a runtime parameter (`--runtime-param search_only=true`) or as a dedicated top-level flag on `configure`/`run`?
   - Why this matters: the current outreach CLI persists runtime behavior through normalized runtime parameters, while a dedicated flag would create a second configuration pattern for the same command family.
   - Recommended option: keep the SDK constructor parameter explicit, and expose the CLI version through the existing runtime-parameter channel to stay consistent with current CLI architecture.
   - User response: Use the recommended runtime-parameter approach.

3. In search-only mode, should the agent still receive email-template context and template tools, or should those also be removed from the tool/context surface alongside Resend?
   - Why this matters: the current prompt and parameter sections are email-centric. Leaving template tools/context available invites unnecessary template selection behavior even if sending is disabled.
   - Recommended option: remove Resend tools and template-selection tools/context from the search-only surface so the mode is deterministic and semantically clean.
   - User response: Yes, all email-related tools should be removed in search-only mode.

## Follow-On Implications

- The SDK constructor must treat `search_only` as a first-class top-level behavior switch and allow `email_data=()` plus absent Resend credentials/clients in that mode.
- The ExaOutreach tool registry must branch by mode:
  - normal mode: Exa + email-template + Resend + lead/email logging tools
  - search-only mode: Exa + lead logging only, with no template-selection tools and no Resend tool surface
- The prompt and parameter sections must branch by mode so the model is not instructed to perform email work when `search_only=True`.
- CLI configuration should persist `search_only` inside the existing outreach runtime-parameter map and allow `outreach run` to omit the Resend and email-template factories when that persisted or overridden runtime parameter is true.
