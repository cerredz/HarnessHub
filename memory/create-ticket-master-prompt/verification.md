Verification completed for the bundled `create_tickets` master prompt.

Checks run:

- `python -c "import json, pathlib; json.loads(pathlib.Path('harnessiq/master_prompts/prompts/create_tickets.json').read_text(encoding='utf-8')); print('create_tickets.json OK')"`
  - Result: passed. The new prompt file is valid JSON and loads cleanly.
- `python -m unittest tests.test_master_prompts`
  - Result: passed. `Ran 27 tests in 0.024s` and `OK`.

Environment note:

- `pytest` is not installed in this workspace, so prompt verification used the repository's existing `unittest`-based test module directly.
