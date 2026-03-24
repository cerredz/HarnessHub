## Post-Critique Changes

### Review Pass

- The first refactor draft moved the internals correctly, but I still needed to make the result easier to review and safer for existing imports.
- I kept the root `harnessiq/tools/context/*.py` modules as thin compatibility wrappers so the new `definitions/` and `executors/` split does not silently break callers that may import those module paths directly.
- I added explicit regression coverage for the opt-in activation contract and for the richer injection descriptions so the review feedback is enforced by tests instead of depending on code review memory.
- While rerunning the suite, I found a stale assertion tail inside `tests/test_agents_base.py` that conflicted with the actual normalized `assistant` entry semantics. I removed that dead block so the file reflects the current runtime model and the suite stays stable.
