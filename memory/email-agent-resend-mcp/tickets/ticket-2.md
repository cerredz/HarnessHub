Title: Add an abstract email-capable agent base that composes the Resend tool
Intent: Create a reusable agent harness that future outbound-email or outreach agents can subclass, so email delivery logic lives once in a stable base class instead of being reimplemented in each domain-specific harness.
Scope:
- Add a new abstract agent module in `src/agents/` that composes the Resend tool surface and provides email-oriented system-prompt/parameter scaffolding.
- Export the new agent classes/config publicly.
- Add focused unit tests using a minimal concrete test subclass and fake model/executor behavior.
- Do not create a concrete production email campaign agent or new persistence model in this ticket.
Relevant Files:
- `src/agents/email.py`: new abstract email base agent and related config types.
- `src/agents/__init__.py`: export the email agent surface.
- `tests/test_email_agent.py`: add email-harness-focused tests.
- `artifacts/file_index.md`: reflect the new tests/memory artifact and keep the index aligned with current architecture.
Approach: Build the new class on top of `BaseAgent`, mirroring the repo’s current harness style. The class should own Resend credentials/client wiring and default behavioral rules for outbound email workflows, while leaving identity/objective and extra parameter sections overridable through abstract hooks. Tests should instantiate a small subclass to confirm the new base class remains reusable rather than over-specialized.
Assumptions:
- The base class should remain abstract even after this task; tests can supply the minimal concrete subclass needed for verification.
- Masked credentials are acceptable in model context so the harness can communicate its configured transport without exposing secrets.
- Reusing the generic `ToolRegistry` composition pattern is preferable to introducing a parallel agent-specific registry abstraction.
Acceptance Criteria:
- [ ] `src/agents/email.py` defines an abstract reusable email-capable base agent built on `BaseAgent`.
- [ ] The email base agent automatically composes the Resend tool factory and exposes a stable email-oriented system prompt scaffold.
- [ ] The agent accepts Resend credentials as constructor/runtime configuration.
- [ ] Tests verify the agent includes the Resend tool, injects masked credential parameters, and can execute a representative send-email tool call through the agent loop.
- [ ] Public `src/agents/__init__.py` exports stay coherent.
Verification Steps:
- Run `python -m unittest tests.test_email_agent`.
- Run `python -m unittest`.
- Manually inspect `src/agents/__init__.py` and `artifacts/file_index.md`.
Dependencies: Ticket 1.
Drift Guard: This ticket must not create a concrete campaign-specific workflow, a persistence format, or another generic agent runtime separate from `BaseAgent`. The focus is the reusable email specialization layer only.
