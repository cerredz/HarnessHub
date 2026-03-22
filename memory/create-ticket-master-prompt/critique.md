Self-critique:

- The prompt is intentionally platform-agnostic so it can be pasted into Linear, GitHub issues, or PR planning threads without rewriting. This is the correct choice for the user's portability requirement.
- The strongest failure mode for this kind of prompt is producing vague or oversized tickets. The final draft addresses that directly by making one-context-window scoping, explicit non-goals, relevant files, and observable success criteria first-class requirements.
- The prompt could have been written as a sequential workflow prompt, but the repository's `create_master_prompts.json` establishes a seven-section master prompt structure as the local standard. Matching that structure is the better fit for a bundled prompt asset in this package.
- No further code changes were necessary because the registry auto-discovers bundled JSON prompt files by filename and the existing test module already covered this integration surface.
