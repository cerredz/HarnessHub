Title: Update SDK docs and verification for the new customization surface

Intent:
Ensure the public SDK documentation and test suite reflect the updated extension points so users can discover and rely on them.

Scope:
- Update README and focused docs pages for custom tools, custom sinks, and runtime configuration.
- Add or update tests covering the new helper exports and public usage patterns.
- Do not broaden scope into unrelated package or CLI documentation.

Relevant Files:
- `README.md`: document the unified customization path.
- `docs/agent-runtime.md`: document runtime helpers for parameter sections and tool injection.
- `docs/output-sinks.md`: document sink registration and custom sink construction.
- `docs/tools.md`: document tool-composition helpers and concrete agent injection.
- Test files touched by Tickets 1 and 2.

Approach:
Show one coherent example for each customization type: define a custom tool and inject it into an agent, define/register a custom sink, and build durable parameter sections through the shared runtime helper. Keep the docs concise and aligned with the actual public exports.

Assumptions:
- The README is the primary SDK discovery surface, with the focused docs pages serving as detailed references.

Acceptance Criteria:
- [ ] README and focused docs mention the new sink registration story.
- [ ] README and focused docs show the standardized custom-tool injection story.
- [ ] Examples use current public imports and match implemented behavior.
- [ ] Tests cover the documented public helpers.

Verification Steps:
- Run the targeted tests updated by Tickets 1 and 2.
- Manually inspect the updated docs examples for import validity against the codebase.

Dependencies:
- Ticket 1.
- Ticket 2.

Drift Guard:
This ticket must not become a broad documentation rewrite. It is limited to the new extensibility surfaces added for sinks, tools, and runtime helpers.
