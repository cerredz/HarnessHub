## Stage 1: Static Analysis

- No dedicated linter or static-analysis tool is configured in `pyproject.toml`.
- Applied the existing repository style and verified the changed CLI modules through targeted pytest runs.

## Stage 2: Type Checking

- No dedicated type-checker configuration (`mypy`, `pyright`, etc.) is present in `pyproject.toml`.
- The added code follows the repo's existing typed dataclass/argparse patterns and passed the focused runtime-oriented CLI tests.

## Stage 3: Unit Tests

- Ran:
```bash
pytest tests/test_model_profiles.py tests/test_master_prompts_cli.py
```
- Result: `24 passed`.

## Stage 4: Integration & Contract Tests

- Ran:
```bash
pytest tests/test_platform_cli.py
```
- Result: `18 passed`.
- Purpose: confirm the expanded command groups did not regress the broader platform CLI surface.

## Stage 5: Smoke & Manual Verification

- Ran:
```bash
python -m harnessiq.cli models add --name smoke --model openai:gpt-5.4
python -m harnessiq.cli models show smoke
python -m harnessiq.cli models export
python -m harnessiq.cli prompts search master
```
- Observed:
  - `models add` and `models show` round-tripped the persisted profile correctly under a temporary `HARNESSIQ_HOME`.
  - `models export` emitted the expected JSON array to stdout.
  - `prompts search master` returned a filtered prompt catalog while preserving the `prompts list` payload shape.
