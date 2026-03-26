# Ticket 3: Implement multi-tool session launch, prompt injection, and sticky mode

## Title
Implement `harnessiq session` for Claude, Codex, Gemini, and OpenCode

## Intent
Deliver the daily-use command that fetches a named harness prompt and either launches a target CLI with that prompt active, copies the prompt to the clipboard, or prints it for piping and manual use. This ticket also implements verified sticky-mode behavior and the documented explicit fallbacks for partially supported targets.

## Scope
Changes:
- Implement `harnessiq session <harness-name>` with target selection, cache usage, dry-run rendering, copy mode, print mode, and passthrough args
- Use `os.execvp` or equivalent true process replacement for interactive launches
- Implement current verified startup-injection strategies for each tool
- Implement sticky mode for verified targets and explicit warning fallback behavior where only partial support is possible
- Add tool-specific temp-file or managed-file lifecycle helpers under `harnessiq/master_prompts/injections/`
- Add prompt-size warnings and target-binary validation

Does not touch:
- Prompt artifact generation
- Install/update/list registration beyond reusing the shared runtime
- Final removal of legacy prompt commands and docs synchronization

## Relevant Files
- CREATE `harnessiq/cli/sync/session.py` - `harnessiq session` parser registration and command handling
- MODIFY `harnessiq/cli/sync/__init__.py` - export session command registration
- CREATE `harnessiq/master_prompts/injections/session_runtime.py` - per-tool launch-plan construction and `execvp` argument building
- CREATE `harnessiq/master_prompts/injections/sticky.py` - sticky-mode file strategies for Claude, Codex, Gemini, and OpenCode
- CREATE `harnessiq/master_prompts/injections/warnings.py` - prompt-size and fallback warnings
- MODIFY `harnessiq/cli/main.py` - wire in session registration if not already done in Ticket 2
- CREATE `tests/test_prompt_sync_session.py` - parser, launch-plan, copy/print, sticky fallback, and `execvp`-argument coverage
- CREATE `tests/test_prompt_sync_clipboard.py` - clipboard success and fallback-to-stdout coverage

## Approach
Separate "resolve prompt and launch plan" from "perform the launch." The command handler should build a structured launch plan that includes the fetched prompt path/text, environment overrides, temp or managed files to materialize, warning messages, and the final argv. This makes the behavior testable without actually replacing the test process. For interactive runs, hand the final argv and environment to an `execvp` path after all validation passes. For sticky mode, use the verified file-based mechanisms:
- Claude: managed `CLAUDE.md` plus startup prompt append where appropriate
- Codex: managed `AGENTS.md`
- Gemini: managed system prompt file via `GEMINI_SYSTEM_MD` and documented context-file behavior
- OpenCode: managed `AGENTS.md` or documented instruction-file path
Where the mechanism is weaker than the draft spec, emit explicit warnings rather than silently pretending feature parity exists.

## Assumptions
- `os.execvp` remains the required execution strategy for interactive targets.
- It is acceptable to materialize temporary or managed instruction files in or adjacent to the active workspace when that is the only viable way to achieve sticky behavior.
- Cleanup for file-based sticky mode may need to favor deterministic managed-file locations and explicit overwrite semantics rather than post-exit deletion when `execvp` takes over the process.
- `--copy` and `--print` are valid no-target modes, while interactive launch requires `--target`.

## Acceptance Criteria
- [ ] `harnessiq session` is registered and validates `harness-name`, `--target`, and passthrough args correctly
- [ ] `--copy` copies prompt text when a clipboard tool is available and falls back to stdout with a warning when it is not
- [ ] `--print` prints the raw prompt text without launching a target binary
- [ ] Interactive launch builds the correct argv and environment for Claude, Codex, Gemini, and OpenCode using the researched current contracts
- [ ] Interactive launch uses a true exec handoff rather than child-process piping for the final session start
- [ ] Sticky mode works on the verified targets and produces explicit warnings or documented fallback behavior where full parity is not possible
- [ ] Tests cover launch-plan construction, copy/print mode, binary-not-found errors, prompt-size warnings, and sticky fallback behavior

## Verification Steps
1. Run the session and clipboard tests.
2. Run representative dry-runs for each target and confirm the rendered launch plan matches the researched tool contract.
3. Manually smoke-test at least one session launch per target in this environment with a small prompt and confirm the target starts correctly.
4. Manually smoke-test sticky mode on the verified targets and confirm the generated instruction files land in the expected locations.

## Dependencies
- Ticket 2 must land first because session depends on the shared fetch, cache, clipboard, and tool-contract runtime.

## Drift Guard
This ticket is about session behavior only. It must not reintroduce the old bundled prompt API, re-scope install/update/list semantics, or hand-edit generated docs as part of the core implementation. If sticky-mode cleanup semantics require a compromise because of `execvp`, that compromise should be explicit and documented rather than hidden behind ad hoc process wrappers.

## Issue URL

https://github.com/cerredz/HarnessHub/issues/284

