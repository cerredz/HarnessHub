## Post-Critique Review

### Findings
1. `src/providers/base.py` still contained a local `role_map` constant inside `build_gemini_contents()`.
   - Why it mattered: the user explicitly asked for constants to live in the new shared package wherever practical.
   - Improvement: moved the Gemini role mapping into `src/shared/providers.py` as `GEMINI_ROLE_MAP`.

2. The new shared modules did not declare an explicit public surface.
   - Why it mattered: once `src/shared/` becomes the source of truth, explicit exports make the intended contract clearer for future consumers.
   - Improvement: added `__all__` declarations to `src/shared/providers.py` and `src/shared/tools.py`.

### Result
- The refactor remains structural only; no request-shape or registry behavior changed.
- Shared definitions now better match the intended “single source of truth” design for constants and typed runtime primitives.
- Post-critique verification rerun:
  - `rg -n "src\.tools\.(base|constants|schemas)|src\.providers\.base import ProviderMessage|src\.tools\.schemas import ToolDefinition" src tests` returned no matches.
  - `python -m compileall src tests` passed.
  - `python -m unittest` passed.
  - The manual smoke script still produced the expected built-in registry keys and OpenAI-style request payload shape.
