Title: Add a system-prompt builder and non-destructive filesystem built-ins
Intent: Expand HarnessHub's built-in tool layer with a prompt-generation tool that derives a system prompt from explicit inputs plus context, and a machine-path filesystem tool set made of explicit non-destructive commands.
Scope:
- Add one provider-agnostic system-prompt generation tool.
- Add explicit filesystem tools for current directory lookup, path existence checks, directory listing, text-file reads, text-file creation, text append, directory creation, and copy operations.
- Allow arbitrary machine paths, but keep the surface non-destructive by forbidding delete, overwrite, and move/rename behavior.
- Export the new tool family through the shared/tool package surfaces, update built-ins, tests, and repository artifacts.
- Do not add a generic shell-execution tool.
- Do not modify the base agent runtime to support live prompt mutation.
Relevant Files:
- `memory/add-system-prompt-terminal-tools/internalization.md`: Phase 1 internalization for this task.
- `memory/add-system-prompt-terminal-tools/clarifications.md`: resolved design choices from Phase 2.
- `src/shared/tools.py`: canonical keys for the prompt and filesystem tools.
- `src/tools/prompting.py`: system-prompt generation helpers and tool definitions.
- `src/tools/filesystem.py`: explicit non-destructive filesystem helpers and tool definitions.
- `src/tools/builtin.py`: include the new tool families in the default registry.
- `src/tools/__init__.py`: export the public helper surface.
- `tests/test_prompt_filesystem_tools.py`: direct behavior coverage for the new tool families.
- `tests/test_tools.py`: update built-in ordering and registry execution coverage.
- `artifacts/file_index.md`: reflect the broader tool-layer responsibilities and new tests.
Approach: Follow the existing tool-family pattern already used by `context_compaction` and `general_purpose`: implement small pure helpers with explicit runtime validation, wrap them in `RegisteredTool` definitions, and append them into `BUILTIN_TOOLS` in stable order. The prompt tool will render a structured prompt string from role/objective/instructions/constraints/tool metadata and a normalized slice of the context window. The filesystem tools will use `pathlib` and `shutil` to expose explicit non-destructive commands over arbitrary machine paths while refusing overwrites or destination collisions.
Assumptions:
- The prompt builder should return a single generated prompt string rather than storing or applying it automatically.
- Text-file operations are sufficient for the initial filesystem surface; binary-file support is out of scope.
- Appending to a file is acceptable in the initial non-destructive model because it preserves prior content.
Acceptance Criteria:
- [ ] A built-in prompt tool exists and returns a system prompt string derived from explicit inputs and context-window state.
- [ ] Built-in filesystem tools exist for current directory lookup, path existence checks, directory listing, text-file reads, text-file creation, text append, directory creation, and copying.
- [ ] The filesystem tools accept arbitrary machine paths but reject destructive operations such as delete, move, and overwrite.
- [ ] Built-in registry ordering remains deterministic and is covered by tests.
- [ ] Unit tests cover prompt rendering, path normalization/validation behavior, non-destructive write semantics, and registry execution.
- [ ] The file index reflects the expanded prompt/filesystem tool surface.
Verification Steps:
- Run `python -m unittest tests.test_prompt_filesystem_tools tests.test_tools`.
- Run `python -m unittest`.
- Manually inspect generated prompt content and temporary-directory file operations through the unit results.
Dependencies: None.
Drift Guard: This ticket must not add a shell-command execution tool, must not mutate live agent system prompts, and must not introduce destructive file operations. The goal is an explicit, understandable, non-destructive filesystem surface plus a reusable prompt builder.
