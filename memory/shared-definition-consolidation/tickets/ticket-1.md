Title: Centralize remaining agent configs and durable type definitions under `harnessiq/shared`

Intent:
Complete the shared-definition pattern for the agent layer so concrete harness modules stop owning reusable configs, constants, and durable helper types that belong in `harnessiq/shared/`.

Scope:
- Add `harnessiq/shared/email.py` for reusable email-agent definitions.
- Move `EmailAgentConfig` and `DEFAULT_EMAIL_AGENT_IDENTITY` out of `harnessiq/agents/email/agent.py`.
- Move remaining LinkedIn definition-only runtime helpers (`LinkedInMemoryStore`, supported runtime parameter metadata, normalization helpers) into `harnessiq/shared/linkedin.py`.
- Move `ExaOutreachAgentConfig` into `harnessiq/shared/exa_outreach.py`.
- Update agent modules, package exports, and tests to consume shared definitions.

Relevant Files:
- `harnessiq/shared/email.py`: new shared email-agent constants/config dataclass.
- `harnessiq/shared/linkedin.py`: extend shared LinkedIn module with durable memory store and runtime parameter helpers.
- `harnessiq/shared/exa_outreach.py`: add `ExaOutreachAgentConfig`.
- `harnessiq/agents/email/agent.py`: import shared email definitions and keep only runtime behavior.
- `harnessiq/agents/linkedin/agent.py`: import shared LinkedIn definitions and remove in-module duplicates.
- `harnessiq/agents/exa_outreach/agent.py`: import shared ExaOutreach config.
- `harnessiq/agents/email/__init__.py`: preserve public exports.
- `harnessiq/agents/linkedin/__init__.py`: preserve public exports.
- `harnessiq/agents/__init__.py`: keep agent package surface aligned.
- `tests/test_email_agent.py`: verify email config import/behavior still works.
- `tests/test_linkedin_agent.py`: verify LinkedIn shared definitions and runtime helpers still work.
- `tests/test_exa_outreach_agent.py`: verify ExaOutreach config import/behavior still works.

Approach:
- Reuse existing shared modules when they already own the domain (`linkedin`, `exa_outreach`).
- Keep behavior-heavy helper functions in the harness module unless they are part of the definition-only runtime/config layer.
- Preserve current public imports by re-exporting from package `__init__` modules after shifting implementation imports.

Assumptions:
- The current `shared/*` module pattern is the correct target structure.
- `LinkedInMemoryStore` is part of the durable type/config layer because it is used by CLI and tests as a reusable contract, not only by the agent runtime.
- Existing Google Drive-related LinkedIn changes in the working tree are authoritative and must remain intact while the shared move happens.

Acceptance Criteria:
- [ ] `EmailAgentConfig` and `DEFAULT_EMAIL_AGENT_IDENTITY` are defined in `harnessiq/shared/email.py`.
- [ ] `LinkedInMemoryStore`, `SUPPORTED_LINKEDIN_RUNTIME_PARAMETERS`, and `normalize_linkedin_runtime_parameters()` are defined in `harnessiq/shared/linkedin.py`.
- [ ] `ExaOutreachAgentConfig` is defined in `harnessiq/shared/exa_outreach.py`.
- [ ] Agent harness modules import those definitions from `harnessiq/shared/*` and no longer define duplicates inline.
- [ ] Public imports from `harnessiq.agents`, `harnessiq.agents.email`, and `harnessiq.agents.linkedin` continue to work.
- [ ] Existing agent behavior and tests remain unchanged except for import paths.

Verification Steps:
1. Run syntax/import validation against touched agent and shared modules.
2. Run `pytest tests/test_email_agent.py tests/test_linkedin_agent.py tests/test_exa_outreach_agent.py`.
3. Smoke-import `harnessiq.agents` and verify key agent exports resolve.

Dependencies:
- None.

Drift Guard:
- Do not redesign agent behavior, prompt structure, or tool wiring.
- Do not rename public agent classes or constants.
- Do not move generic agent runtime definitions out of `harnessiq/shared/agents.py`.
