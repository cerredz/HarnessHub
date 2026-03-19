Title: Add fail-open default LangSmith tracing across BaseAgent, SDK runtime config, and CLI run paths

Issue URL: https://github.com/cerredz/HarnessHub/issues/164

Intent: Ensure every Harnessiq agent run is traced by default when LangSmith credentials are available, while preserving normal execution when they are not. This satisfies the user-facing requirement that LinkedIn, Instagram, Knowt, and all other agents appear automatically in the user’s LangChain/LangSmith account without making tracing a hard dependency at runtime.

Scope:

- Add tracing configuration fields to the shared runtime config.
- Make the LangSmith provider helpers fail open when credentials are absent or tracing transport/setup fails.
- Add default root-run and tool tracing in `BaseAgent`.
- Preserve or expose runtime-config injection across all concrete agents.
- Seed CLI LangSmith environment variables from repo-local `.env` before model factories are created.
- Add regression tests for the new behavior.

Out of scope:

- Adding a new Knowt CLI surface.
- Reworking provider-specific model adapters beyond the shared LangSmith fail-open boundary.
- Broad documentation rewrites unless a test or behavior change requires a small update.

Relevant Files:

- `harnessiq/shared/agents.py`: add tracing-related runtime config fields and helpers.
- `harnessiq/agents/base/agent.py`: wrap agent runs and tool execution in default tracing.
- `harnessiq/providers/langsmith.py`: implement credential-aware, fail-open tracing behavior.
- `harnessiq/agents/linkedin/agent.py`: preserve/inject tracing-aware runtime config.
- `harnessiq/agents/instagram/agent.py`: add/preserve tracing-aware runtime config.
- `harnessiq/agents/knowt/agent.py`: add/preserve tracing-aware runtime config.
- `harnessiq/agents/leads/agent.py`: add/preserve tracing-aware runtime config.
- `harnessiq/agents/exa_outreach/agent.py`: preserve tracing-aware runtime config.
- `harnessiq/agents/email/agent.py`: preserve tracing-aware runtime config.
- `harnessiq/cli/linkedin/commands.py`: seed env and pass tracing-aware runtime config.
- `harnessiq/cli/instagram/commands.py`: seed env for model-factory tracing and pass runtime config if supported.
- `harnessiq/cli/leads/commands.py`: seed env and pass tracing-aware runtime config.
- `harnessiq/cli/exa_outreach/commands.py`: seed env and pass tracing-aware runtime config.
- `tests/test_agents_base.py`: validate default base-agent tracing and fail-open behavior.
- `tests/test_providers.py`: validate fail-open tracing helpers.
- `tests/test_linkedin_cli.py`: validate CLI LangSmith env seeding/runtime behavior.
- `tests/test_instagram_cli.py`: validate CLI LangSmith env seeding/runtime behavior.
- `tests/test_linkedin_agent.py`: validate runtime-config propagation for LinkedIn.
- `tests/test_instagram_agent.py`: validate runtime-config propagation for Instagram.
- `tests/test_knowt_agent.py`: validate runtime-config propagation for Knowt.

Approach:

- Keep tracing behavior centralized. The provider helper decides whether tracing is actually possible; the base agent and CLI always wire it by default.
- Treat missing credentials as “tracing unavailable,” not as an error.
- Preserve explicit shell environment values over repo-local `.env` values, and only backfill missing LangSmith/LangChain keys from `.env`.
- Avoid per-agent ad hoc tracing code. Agent constructors should only preserve the shared runtime config rather than each re-implementing tracing logic.

Assumptions:

- LangSmith is the correct implementation target for the user’s “LangChain account” request.
- Repo-local `.env` is a valid CLI credential source.
- Adding optional runtime-config fields is backward compatible for existing SDK users.

Acceptance Criteria:

- [ ] `BaseAgent.run()` emits a default LangSmith root trace when credentials are available.
- [ ] `BaseAgent` tool execution emits child tool traces when credentials are available.
- [ ] Agent execution succeeds unchanged when LangSmith credentials are absent.
- [ ] Shared LangSmith tracing helpers do not raise solely because tracing credentials or tracing setup are missing/unavailable.
- [ ] LinkedIn, Instagram, Knowt, Leads, ExaOutreach, and BaseEmailAgent preserve tracing-aware runtime config instead of dropping it.
- [ ] CLI run commands seed LangSmith/LangChain env vars from repo-local `.env` without overriding already-exported values.
- [ ] Regression tests cover both traced and fail-open paths.

Verification Steps:

- Run the targeted unit tests for provider tracing, base agent runtime, and agent/CLI surfaces.
- Run the full test suite if the targeted set passes cleanly in reasonable time.
- Manually inspect the effective env/runtime behavior in CLI tests to confirm `.env` backfill and non-overwrite semantics.

Dependencies: None.

Drift Guard:

This ticket must not expand into a general observability framework rewrite or a broad provider abstraction redesign. The goal is narrowly to make the existing LangSmith integration universal by default, safe when credentials are absent, and properly propagated through the current SDK and CLI surfaces.
