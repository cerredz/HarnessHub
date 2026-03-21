Title: Split the provider output-sink utility module into focused metadata and client layers

## Summary

- Split `harnessiq.providers.output_sinks` into dedicated metadata and delivery-client modules.
- Kept `harnessiq.providers.output_sinks` as the stable public facade and preserved provider-package exports.
- Added compatibility coverage for the facade and cleaned up duplicated provider-name heuristics during self-critique.

## Testing

- `python -m compileall harnessiq tests`
- `.venv\Scripts\pytest.exe -q tests/test_output_sinks.py`
- `.venv\Scripts\pytest.exe -q tests/test_agents_base.py` (known `origin/main` baseline failure in prune-progress reset test)
- `.venv\Scripts\pytest.exe -q tests/test_providers.py`
- Manual smoke snippet importing `LinearClient`, `WebhookDeliveryClient`, and `extract_model_metadata` from `harnessiq.providers`

## Post-Critique Changes

- Replaced duplicated provider-name heuristic lists with named private tuples in the extracted metadata module.
