Title: Add historical run selection to platform-first resume flows

Issue URL: https://github.com/cerredz/HarnessHub/issues/258

PR URL: https://github.com/cerredz/HarnessHub/pull/259

Intent:
Extend platform-first resume so a user can resume a specific prior run for a configured harness profile instead of only the latest run.

Scope:
- Persist numbered historical run snapshots for platform-first harness profiles.
- Add `--run <number>` to the global `resume` command and to `run <harness> --resume`.
- Preserve latest-run fallback when `--run` is omitted.
- Keep legacy profiles with only `last_run` resumable.
- Refresh generated docs and the file index artifact.

Relevant Files:
- `harnessiq/config/harness_profiles.py`: persist numbered run history and normalize legacy `last_run` payloads.
- `harnessiq/cli/platform_commands.py`: resolve specific run numbers and seed resumed contexts from historical snapshots.
- `tests/test_harness_profiles.py`: cover history persistence and backward compatibility.
- `tests/test_platform_cli.py`: cover specific-run replay and failure paths.
- `artifacts/file_index.md`: regenerated file index output.
- `artifacts/live_inventory.json`: regenerated repo inventory output.

Approach:
Store a chronological `run_history` on each generic harness profile while retaining `last_run` as the latest compatibility view. Each snapshot records the run number, timestamp, runtime/custom parameters, model factory, sink specs, max cycles, and harness-specific run arguments. Resume flows resolve the requested historical snapshot first, rebuild the effective profile context from that snapshot, and then append a new run-history entry for the resumed execution.

Assumptions:
- Run numbers are monotonic and scoped to one manifest/profile pair.
- Legacy `last_run` payloads represent the same runtime/custom state stored at the profile level when they were written.

Acceptance Criteria:
- [ ] Platform-first profiles persist a numbered run history alongside the latest compatibility snapshot.
- [ ] `python -m harnessiq.cli resume <agent> --run 2` replays the second stored run for that profile.
- [ ] `python -m harnessiq.cli run <harness> --resume --agent <agent> --run 2` replays the second stored run for that harness/profile.
- [ ] Omitting `--run` still resumes the latest run.
- [ ] Legacy profiles with only `last_run` still resume without losing their runtime/custom configuration.
- [ ] Generated docs and `artifacts/file_index.md` are refreshed.

Verification Steps:
- Run `python -m pytest -q tests/test_harness_profiles.py tests/test_platform_cli.py`.
- Run `python scripts/sync_repo_docs.py`.
- Run `python -m pytest -q tests/test_platform_cli.py tests/test_harness_profiles.py tests/test_harness_manifests.py tests/test_docs_sync.py tests/test_sdk_package.py`.
- Smoke the CLI help output for `python -m harnessiq.cli resume --help` and `python -m harnessiq.cli run instagram --help`.

Dependencies:
- None.

Drift Guard:
Keep this change focused on replaying historical platform-first run payloads. Do not expand it into a separate run browser, harness-native log redesign, or unrelated CLI restructuring.
