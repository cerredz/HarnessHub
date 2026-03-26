### 1a: Structural Survey

- `harnessiq/cli/main.py` is the argparse entrypoint and registers both platform-first and harness-specific command trees.
- `harnessiq/cli/platform_commands.py` owns the generic `prepare`, `show`, `run`, `resume`, and credential flows for declarative harness manifests.
- `harnessiq/config/harness_profiles.py` persists generic harness profile state under each memory folder plus a repo-scoped discovery index under `memory/harness_profiles.json`.
- The current platform-first resume implementation on this branch stores one `last_run` snapshot per profile and resolves candidates by agent name plus optional harness narrowing.
- Generated repo docs and the artifact index are refreshed through `scripts/sync_repo_docs.py`, with regressions enforced by `tests/test_docs_sync.py`.
- The primary regression surface for this feature lives in `tests/test_harness_profiles.py` and `tests/test_platform_cli.py`, with wider CLI/doc packaging checks in `tests/test_harness_manifests.py`, `tests/test_docs_sync.py`, and `tests/test_sdk_package.py`.

### 1b: Task Cross-Reference

- The request maps directly onto `harnessiq/config/harness_profiles.py`: the persisted run metadata must evolve from a single latest snapshot to a numbered history that can replay specific historical runs.
- `harnessiq/cli/platform_commands.py` must accept a specific historical selector in both `resume` and `run <harness> --resume`, resolve the requested snapshot, and seed the resumed context from that run's stored payload.
- The previous resume work on this branch already added global resume by agent name, persisted run-only arguments, and ambiguity selection. This change must extend that behavior rather than replace it.
- The exact replay requirement means historical snapshots must capture runtime/custom profile parameters in addition to model factory, sink specs, max cycles, and harness-specific adapter arguments.
- The file index artifact named in the task is generated, so the implementation has to flow through `scripts/sync_repo_docs.py` rather than a hand edit.

### 1c: Assumption & Risk Inventory

- Assumption: "run 2 / run 3 / run 4" means chronological per-profile numbering starting at `1`.
- Assumption: omitting `--run` should preserve the existing "resume latest" behavior for both global and harness-scoped resume flows.
- Risk: storing only run-only arguments would make `--run 2` replay the wrong configuration after later profile edits; per-run runtime/custom parameters must be captured too.
- Risk: legacy profiles that only contain `last_run` metadata must keep working and must not lose their current runtime/custom state when resumed.
- Risk: generated docs and file-index artifacts will drift as soon as the CLI help surface or test inventory changes, so doc sync must be rerun after both code and test updates.

Phase 1 complete
