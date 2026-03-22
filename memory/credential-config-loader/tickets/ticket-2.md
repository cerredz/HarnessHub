Title: Wire agent constructors to accept direct or stored credentials

Issue URL: https://github.com/cerredz/HarnessHub/issues/29

Intent:
Allow SDK users to pass either direct credential objects or the new config-layer class into agent constructors, while preserving current direct-credential behavior and adding a consistent credentials parameter to agents that currently do not expose one.

Scope:
Update the agent layer so credential-bearing agents can resolve from the config loader and non-credential-bearing agents can accept a credentials parameter for future-compatible agent APIs. Preserve existing direct credential support and add tests around both direct and config-backed usage. This ticket does not add CLI commands yet.

Relevant Files:
- `harnessiq/agents/base.py`: shared credential parameter plumbing if needed
- `harnessiq/agents/email.py`: accept config-layer input and resolve Resend credentials
- `harnessiq/agents/linkedin.py`: add a credentials parameter surface and include safe credential summary sections when present
- `harnessiq/agents/__init__.py`: export any new public credential-facing agent types/helpers
- `tests/test_email_agent.py`: expand coverage for config-backed credentials
- `tests/test_linkedin_agent.py`: add coverage for the new credentials parameter on LinkedIn agents

Approach:
Keep the runtime contract explicit. Add a generic agent-facing credential config object from `harnessiq.config` and resolve it at construction time for agents that need concrete third-party credentials now. For `BaseEmailAgent`, accept either `ResendCredentials` or a credential config/binding that can produce the required `api_key`. For `LinkedInJobApplierAgent`, add an optional credentials parameter and expose only safe, redacted parameter sections so the API is consistent without inventing unsupported tool behavior. Avoid retrofitting provider clients in this ticket.

Assumptions:
- The first concrete third-party integration to resolve from the new config layer is Resend.
- Adding a credentials parameter to LinkedIn agents is acceptable even if current browser tools do not consume those credentials directly.
- Agent prompts must continue to avoid raw secret leakage.

Acceptance Criteria:
- [ ] Existing direct `ResendCredentials(...)` usage continues to work unchanged.
- [ ] Email agents can be constructed from the new config-layer credential binding and resolve required env vars from `.env`.
- [ ] LinkedIn agents expose a `credentials` parameter without breaking current construction paths.
- [ ] Any credential content injected into parameter sections is safely redacted or summarized.
- [ ] Updated unit tests cover direct and config-backed agent construction paths.

Verification Steps:
- Run email-agent and LinkedIn-agent unit tests.
- Manually instantiate agents using both direct credentials and config-backed credentials against a temporary `.env`.
- Inspect rendered parameter sections to confirm no raw secret values are exposed.

Dependencies:
- Ticket 1

Drift Guard:
This ticket must not add CLI commands or broaden the config layer into provider-client refactors. The goal is agent-surface integration only.
