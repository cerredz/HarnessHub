## Self-Critique

- Reviewed whether the examples should be normalized into Markdown bullets or reformatted into cleaner prose. I did not do that because the user asked for this examples corpus to be added, and preserving the exact numbered-tag structure is the safest interpretation of that request.
- Reviewed whether other TODO sections should be removed for consistency. I left them untouched because they were outside scope and current tests still expect TODO markers in the prompt.
- Reviewed whether source-code or test updates were necessary. They were not: the change is content-only, and the existing Knowt prompt-loading tests already validate the relevant contract.

## Post-Critique Outcome

- No further source changes were warranted after critique.
- The implemented prompt edit remains the narrowest correct change.
