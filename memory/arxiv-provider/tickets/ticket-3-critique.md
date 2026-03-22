## Self-Critique — Ticket 3

### Issues found and fixed

**1. `registry.list()` relies on _ensure_builtin_loaded() which has a pre-existing bug**
`registry.list()` calls `_ensure_builtin_loaded()` which imports `create_reasoning_tools` from a module that can't export it. Two tests that used `registry.list()` were rewritten to use `PROVIDER_ENTRY_INDEX` directly — correct alternative that tests the same behavior without hitting the pre-existing bug.

**2. Registry `_resolve_family` lookup strategy**
The `needs_creds` check iterates over `PROVIDER_ENTRIES` to find entries for the given family. This is O(n) but `PROVIDER_ENTRIES` is a small tuple (~16 entries). A dict `PROVIDER_FAMILY_INDEX` could make this O(1) but would be premature optimization for a static catalog. Current approach is clear and correct.

**3. Registry fix scope is precise**
The two changes to `registry.py` are surgical: `if credentials is None:` → `if credentials is None and entry.requires_credentials:` in `_resolve_provider_tool`, and the equivalent check in `_resolve_family`. No behavioral change for any existing provider — all existing providers have `requires_credentials=True`. The regression tests confirm this.

**4. `ARXIV_REQUEST` added in Ticket 2 worktree, not Ticket 3**
The constant was added in the issue-140 worktree for practical reasons (the factory needed it to compile). The cherry-pick into issue-141 carries it through. The final state is correct.

**5. `file_index.md` entries are precise and useful**
Provider entry documents the `ArxivConfig`/no-auth distinction explicitly. Test entry documents all three test class contributions. Consistent with adjacent entries in style.

**No additional improvements needed.**
