## Self-Critique

- The first pass risked losing caller-specified operation order in the `resend_request` tool schema because the allowed-operation set was rebuilt as an unordered collection.
- The initial design also needed an explicit provider-name inference update so transport failures would report `resend` instead of the generic `provider`.

## Implemented Improvements

- Preserved the configured operation order when building the tool-definition enum.
- Added shared transport coverage that verifies Resend failures are labeled with the `resend` provider name.
