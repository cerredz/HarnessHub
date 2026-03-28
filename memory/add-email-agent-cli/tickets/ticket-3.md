Title: Add verification coverage, sync docs, and update the Obsidian operator note
Intent: Ensure the new email harness is discoverable, verified, and documented consistently across the repo and the operator-facing Obsidian workflow note.
Scope: Add or update tests, regenerate synced docs, and revise the Obsidian note so it references the new CLI flow. Do not expand runtime behavior beyond what tickets 1 and 2 already implemented.
Relevant Files:
- `tests/test_harness_manifests.py` — include the built-in email manifest.
- `tests/test_output_sinks.py` — cover Mongo document reads.
- `tests/test_email_campaign_shared.py` — new shared-domain tests.
- `tests/test_email_campaign_agent.py` — new concrete-agent tests.
- `tests/test_email_cli.py` — new dedicated CLI tests.
- `tests/test_platform_cli.py` — add email manifest/platform-flow coverage.
- `artifacts/file_index.md` — synced repo artifact.
- `artifacts/commands.md` — synced repo artifact.
- `README.md` — synced repo artifact if the generator updates it.
- Obsidian note under the existing `harnessiq/` folder — replace helper-script instructions with first-class CLI commands.
Approach: Extend the current test suites instead of creating parallel custom harnesses, then rerun the repo’s doc-sync generator so the manifests and commands stay authoritative. Update the operator note only after the final CLI shape is stable.
Assumptions:
- The Obsidian note already exists and should be updated in place.
- The docs sync generator is the authoritative way to refresh repo command/file-index artifacts.
Acceptance Criteria:
- [x] The new email harness is covered by dedicated and platform CLI tests plus shared/agent tests.
- [x] The repo docs are regenerated from live code after the new manifest and command family land.
- [x] The Obsidian note instructs users to use the built-in email CLI rather than a helper script.
Verification Steps:
- Run the targeted pytest suites for manifests, output sinks, email shared/agent/CLI, and platform CLI.
- Run doc sync and the docs-sync test.
- Read back the updated Obsidian note after writing it.
Dependencies: `ticket-1.md`, `ticket-2.md`
Drift Guard: Do not let the documentation describe commands or scripts that no longer match the implemented CLI surface.
