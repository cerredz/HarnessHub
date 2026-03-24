# Ticket 1 Post-Critique

## Findings

1. The initial implementation correctly exposed the new harness in the SDK and CLI, but the built wheel still omitted harness-local `master_prompt.md` files. That meant an installed package could import the agent classes yet fail later when prompt-backed harnesses tried to load their prompt assets at runtime.
2. The first pass of platform CLI coverage exercised the new manifest and direct CLI, but it did not yet lock down the generic platform alias and bound-Serper-credential path that real users will hit through `prepare/show/run/inspect/credentials`.

## Improvements Applied

- Updated `pyproject.toml` package-data rules so all harness-local `prompts/master_prompt.md` assets, including the new research sweep prompt, are shipped in the wheel.
- Strengthened `tests/test_sdk_package.py` to assert those prompt assets are present in the built wheel alongside the existing import smoke checks.
- Expanded `tests/test_platform_cli.py` to cover:
  - generic `prepare/show/inspect` for `research_sweep` and the `research-sweep` alias
  - generic `run` using bound `serper` credentials resolved from the persisted credential store

## Re-Verification

- Re-ran the full test suite after the critique fixes:

```powershell
pytest
```

- Result: passed (`1417 passed`).
