# Master Prompt Session Injection

`harnessiq prompts` can activate one bundled master prompt as always-on project instructions for fresh Claude Code and Codex sessions.

If you are running from this repository checkout rather than an installed package, install the editable console entrypoint first:

```bash
pip install -e .
```

## Commands

List the bundled prompt catalog:

```bash
harnessiq prompts list
```

Activate one prompt for the current repository:

```bash
harnessiq prompts activate create_master_prompts
```

Show the current active prompt selection:

```bash
harnessiq prompts current
```

Clear the generated overlays:

```bash
harnessiq prompts clear
```

## Generated Files

Activation writes these repo-local files:

- `.claude/CLAUDE.md` for Claude Code
- `AGENTS.override.md` for Codex
- `.harnessiq/master_prompt_session/active_prompt.json` for local activation metadata

`.claude/` and `.harnessiq/` are already ignored in this repository. `AGENTS.override.md` is also ignored so the active prompt choice stays local by default.

## Behavior

This mechanism does not attempt to mutate an already-open chat. Instead, it prepares project instruction files that Claude Code and Codex read when you start a fresh session from the repository. Because the selected prompt is loaded as project guidance, it remains available for every request in that session until you clear or replace it.
