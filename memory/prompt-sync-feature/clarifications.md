# Prompt Sync Feature Clarifications

## Questions For User

1. Surface decision: should the new Prompt Sync commands replace the current bundled-prompt workflow, or coexist with it?
   - Ambiguity being resolved: the repo already ships `harnessiq prompts list/show/text/activate/current/clear` backed by packaged JSON prompts and repo-local overlays, while the design doc introduces a different top-level model (`install`, `update`, `session`, `list`) backed by GitHub-hosted Markdown.
   - Why this matters: replacement implies migrating or deprecating public APIs/tests/package data; coexistence implies preserving the current `harnessiq.master_prompts` API and adding a second prompt system beside it.
   - Concrete options:
     - Option A: Keep the existing `harnessiq prompts` and `harnessiq.master_prompts` API intact, and add the new sync commands as a separate system.
     - Option B: Replace the existing bundled prompt system with the new GitHub-backed system and update the public API accordingly.
     - Option C: Keep legacy read-only compatibility temporarily, but route new behavior and docs to Prompt Sync.

2. Platform support decision: for Codex, Gemini, and OpenCode, should implementation follow the draft spec or the actual installed CLIs?
   - Ambiguity being resolved: locally, `claude --append-system-prompt` is confirmed, but `codex --instructions` is not present, and `gemini`/`opencode` do not expose the draft's `--system-prompt` flags in their installed help output.
   - Why this matters: hard-coding the draft flags will produce a broken feature on this machine; switching to installed-tool behavior changes the design materially.
   - Concrete options:
     - Option A: Implement against the actual installed tool contracts now. That likely means confirmed first-class support for Claude, partial or adjusted support for Codex, and best-effort or deferred support for Gemini/OpenCode until their real injection surfaces are specified.
     - Option B: Implement the draft spec literally, even though it does not match the currently installed binaries.
     - Option C: Ship Claude and Codex first, and explicitly defer Gemini/OpenCode to a later ticket once you provide the exact supported invocation contracts.

3. Registry ownership decision: do you want me to implement the runtime feature only, or also add the repo-side prompt registry generation workflow now?
   - Ambiguity being resolved: the design doc requires `artifacts/prompts/registry.json` and states it should be CI-generated, but the current repo has no `artifacts/prompts/` directory, no registry generator, and no CI workflow for it.
   - Why this matters: the `harnessiq list`, fetch validation, and unknown-harness behavior all depend on the registry existing and staying current.
   - Concrete options:
     - Option A: Implement the feature plus a local generator script and commit the generated `registry.json`, leaving CI for later.
     - Option B: Implement the feature plus the generator script and a CI workflow in this same task.
     - Option C: Treat `registry.json` as manually committed for now and only implement runtime consumption.

4. Sticky-mode contract decision: what level of support do you want for tools whose per-turn instruction mechanism is not verified?
   - Ambiguity being resolved: the draft only gives a concrete sticky strategy for Claude (`CLAUDE.md`) and Codex (`AGENTS.md`), while Gemini/OpenCode lack a verified per-turn mechanism in the current environment.
   - Why this matters: a "sticky" flag that silently degrades can be acceptable if documented, but not if you expect strict behavioral parity across all targets.
   - Concrete options:
     - Option A: Fully support sticky mode only for Claude and Codex, and emit explicit warnings/fallbacks for Gemini/OpenCode.
     - Option B: Make `--sticky` available only on targets with verified support.
     - Option C: Attempt speculative implementations for all four targets despite the missing confirmation.

5. Workflow decision: should I follow the skill's GitHub-issue decomposition workflow in this repo, or skip directly to local implementation after clarifications?
   - Ambiguity being resolved: the `github-software-engineer` skill prescribes Phase 3 ticket drafting plus GitHub issue creation before implementation, but your task wording asks me to implement the design directly.
   - Why this matters: creating issues and working ticket-by-ticket will add process overhead but follows the invoked skill exactly; skipping that step is faster but deviates from the skill contract.
   - Concrete options:
     - Option A: Follow the full skill workflow, including ticket docs and GitHub issue creation.
     - Option B: Write the task artifacts locally in `memory/prompt-sync-feature/`, but skip GitHub issue creation and proceed straight to implementation.
     - Option C: Ignore the skill workflow and implement directly.

## User Responses

1. Surface decision
   - Response: Replace the current bundled prompt workflow entirely. Do not make the new Prompt Sync system coexist with the old one.
   - Implementation implication: the existing `harnessiq prompts` command family and the bundled `harnessiq.master_prompts.prompts/*.json` workflow should be treated as legacy to be removed or rewritten around the new source of truth.

2. Platform support decision
   - Response: Research the current CLIs and implement the real current contracts, not the draft-spec placeholders.
   - Implementation implication: the draft spec is no longer authoritative for per-tool startup and injection behavior. Verified vendor docs and current CLI behavior are authoritative instead.

3. Registry ownership decision
   - Response: Everything in the design doc.
   - Implementation implication: this task includes the runtime feature plus repository-side prompt storage under `artifacts/prompts/`, registry handling, and the supporting generator/workflow needed to keep the registry aligned.

4. Sticky-mode contract decision
   - Response: Option A.
   - Implementation implication: sticky mode should be fully supported on verified targets, with explicit warning/fallback behavior where only partial support is possible.

5. Workflow decision
   - Response: Follow the GitHub software engineer skill.
   - Implementation implication: proceed with ticket drafting and GitHub issue creation before coding.

## Research-Driven Contract Updates

The following findings supersede draft-spec assumptions where they conflict.

### Claude Code

- Verified via installed CLI help:
  - `claude --append-system-prompt <prompt>` exists.
  - `claude --system-prompt <prompt>` also exists.
- Verified via Anthropic docs:
  - `--append-system-prompt` appends to the system prompt.
  - `CLAUDE.md` is added as a user message after the default system prompt rather than editing the system prompt directly.
  - Skills are a supported concept and are distinct from output styles and agents.
- Implementation implication:
  - Session-start injection can use `--append-system-prompt`.
  - Sticky mode can rely on a temporary `CLAUDE.md` strategy, but this is a per-turn context-file mechanism rather than a true system-prompt flag.

### OpenAI Codex

- Verified via installed CLI help:
  - Interactive `codex [PROMPT]` accepts an initial prompt as a positional argument.
  - Non-interactive `codex exec [PROMPT]` also accepts initial instructions as a positional prompt.
  - The installed CLI does not expose a top-level `--instructions` flag.
- Verified via official OpenAI docs:
  - Codex uses `AGENTS.md` as an instruction file convention.
  - Codex configuration lives in `~/.codex/config.toml`.
- Verified via local install state:
  - `~/.codex/AGENTS.md` exists.
  - `~/.codex/skills/` exists in this environment.
- Implementation implication:
  - Session-start injection for Codex should use the initial positional prompt, not the draft's `--instructions` flag.
  - Sticky mode can use temporary `AGENTS.md` handling in the working tree.
  - Skill installation can target `~/.codex/skills/<name>/SKILL.md` based on the live environment; this is an inference from the installed client state rather than a currently cited OpenAI web doc.

### Gemini CLI

- Verified via installed CLI help:
  - No `--system-prompt` flag is exposed.
  - `gemini skills` is a supported command family.
- Verified via official Gemini CLI docs:
  - Full system prompt override is controlled by `GEMINI_SYSTEM_MD`.
  - Setting `GEMINI_SYSTEM_MD=1` causes the CLI to read `./.gemini/system.md`.
  - Skills are discovered from `.gemini/skills/`, `~/.gemini/skills/`, and `.agents/skills/` / `~/.agents/skills/`.
  - `GEMINI.md` is the persistent context-file mechanism and is loaded hierarchically.
- Implementation implication:
  - Session-start injection should use `GEMINI_SYSTEM_MD` pointing at a generated Markdown file rather than a nonexistent `--system-prompt` flag.
  - Sticky mode can be implemented through the same system-prompt-file override or via context-file strategy as appropriate.
  - Install/update should target `~/.gemini/skills/<name>/SKILL.md` or a documented compatible path.

### OpenCode

- Verified via installed CLI help:
  - No `--system-prompt` flag is exposed.
  - `opencode agent create` exists.
  - `--prompt` is a user-prompt argument, not a documented system-prompt override.
- Verified via official OpenCode docs:
  - OpenCode reads `AGENTS.md` rules files from project and global locations.
  - Global rules path is `~/.config/opencode/AGENTS.md`.
  - OpenCode supports explicit instruction files via `opencode.json` `instructions`.
  - OpenCode supports skills from `.opencode/skills/<name>/SKILL.md`, `~/.config/opencode/skills/<name>/SKILL.md`, plus Claude-compatible and `.agents`-compatible fallback locations.
  - Custom agents can point at a system prompt file via `prompt` config.
- Implementation implication:
  - Session-start injection should be based on a generated `AGENTS.md`, generated instruction config, or generated temporary agent config rather than the draft's `--system-prompt` flag.
  - Sticky mode can rely on an ephemeral `AGENTS.md` or related rule/config file.
  - Install/update should prefer OpenCode-native locations under `~/.config/opencode/skills/`, with Claude-compatible fallback only if needed.
