## Self-Critique

Primary findings after the first implementation pass:
- The Paperclip tool registration itself was straightforward, but the surrounding toolset validation depends on the built-in families loading correctly. That exposed the unrelated `_builtin_reason()` regression, which had to be corrected to validate this ticket honestly.
- The `paperclip.request` description needed to communicate both what Paperclip is and what this first integration intentionally omits, otherwise callers could assume broader adapter/runtime coverage than was actually implemented.
- The registration changes had to be kept narrow because `harnessiq/shared/tools.py` and `harnessiq/toolset/catalog.py` already had in-flight local edits unrelated to this task.

Improvements implemented after critique:
- Fixed the toolset built-in reasoning import regression so the new provider family could be validated in a normal catalog load.
- Kept Paperclip registration changes additive and avoided unrelated provider/export files where no change was necessary.
- Re-ran the focused provider/tool/toolset test suites after the fix and confirmed they passed.

Residual risk:
- The Paperclip family is intentionally broad at the operation-catalog level. If callers need smaller role-specific tool subsets later, a follow-up can expose recommended `allowed_operations` presets without changing the provider contract.
