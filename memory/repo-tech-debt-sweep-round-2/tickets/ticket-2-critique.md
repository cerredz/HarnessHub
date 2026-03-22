## Self-Critique

- The first extracted metadata module still duplicated the provider-name heuristic lists across the model-module and client-module detection paths.
- That duplication was inherited from the original monolith, but keeping it in the split module would make future heuristic updates easier to miss in one path.

## Post-Critique Improvements

- Introduced named private tuples for the known provider-name heuristics in `output_sink_metadata.py`.
- Re-ran the full ticket verification set after the readability cleanup and confirmed the same passing and baseline-failure profile.
