Post-Critique Review for issue-153

Findings addressed in this ticket:
- The initial leads CLI run path accepted `search_summary_every`, `search_tail_size`, and `max_leads_per_icp` as run-time overrides but never applied them because those values were still read from persisted `run_config`. I fixed this by deriving an effective `LeadRunConfig` for the current invocation before constructing `LeadsAgent`.
- The initial CLI surface did not expose the already-supported pluggable `LeadsStorageBackend`. I added `--storage-backend-factory` so the public CLI can reach the same backend injection point that the SDK supports.
- `leads configure` wrote `run_config.json` but did not initialize per-ICP state files, which left `leads show` with no `icp_states` until a run had already started. I now initialize ICP state immediately after writing a valid run config.
- The repo docs understated the public surface: README still described four concrete agents, omitted the Apollo provider from the provider table, and had no leads-agent CLI flow. I added README coverage, a focused `docs/leads-agent.md`, Apollo tool examples, and runtime-pruning documentation.

Residual review notes:
- The leads CLI still expects the durable run config fields (`company_background`, `icps`, `platforms`) to be present before it can persist `run_config.json`. That is acceptable for v1 because the CLI examples configure all required inputs together, and adding an explicit draft-config layer would be a separate UX expansion rather than a bug fix.
- `artifacts/file_index.md` still contains some older encoding artifacts in pre-existing lines outside this ticket's scope. I updated the relevant leads/Apollo entries without broad cleanup to avoid unrelated churn.
