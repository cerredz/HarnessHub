## Self-Critique

- The main risk in this change is overfitting Grok capability detection to one naming convention. I reviewed whether the helper should introduce a full model catalog, but that would add maintenance overhead and global state for a repo that currently only distinguishes reasoning support by model naming. The current helper is intentionally narrow and centralized so future expansion happens in one place.
- I checked whether `with_model_override()` would accidentally drop a previously configured `reasoning_effort` after starting from a non-reasoning Grok model. That was a real risk in the original implementation, so the change now preserves the requested effort separately from the effective emitted effort.
- I checked whether the fix leaked into agent-specific code. It does not; the behavior remains in shared Grok model plumbing, which is the correct boundary for "support all agents".
- I checked whether the tests prove the user-visible path, not just internals. They now cover shared adapter behavior, request serialization omission, and the Instagram platform CLI command surface.

## Post-Critique Changes

- No additional code changes were required after the critique. The main improvement identified during review, preserving requested reasoning effort across model overrides, was already included in the implementation commit.
