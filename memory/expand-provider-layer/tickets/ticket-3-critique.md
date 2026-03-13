## Self-Critique

- The first implementation pass normalized Anthropic message-role/content errors with plain `ValueError`, which was inconsistent with the rest of the provider layer’s `ProviderFormatError` contract.
- That inconsistency would make caller-side error handling noisier and would be easy to miss because the happy-path tests were already green.

## Implemented Improvements

- Switched Anthropic message normalization failures to raise `ProviderFormatError`.
- Added a direct test covering rejection of unsupported Anthropic message roles.
