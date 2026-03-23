# Context Window Manipulation Tools

Canonical reference for the `context.*` tool family.

## Overview

The `context.*` family is a standardized toolset for manipulating an agent's
context window at runtime. The tools operate on one or both of these zones:

- Parameter zone: master prompt extensions, injected sections, and durable
  memory-backed parameter sections.
- Transcript zone: assistant messages, tool calls, tool results, and other
  execution-log entries.

The family is split into five groups:

| Group | Prefix | Operation | Target |
| --- | --- | --- | --- |
| 1 | `context.summarize.*` | LLM summarization | Transcript |
| 2 | `context.struct.*` | Deterministic structural reshape | Transcript |
| 3 | `context.select.*` | Agent-directed keep, promote, checkpoint | Transcript and parameter |
| 4 | `context.param.*` | Additive parameter and memory writes | Parameter |
| 5 | `context.inject.*` | Additive transcript inserts | Transcript |

Groups 1, 2, 3, and 5 return a `context_window` payload and are intercepted by
BaseAgent's compaction flow. Group 4 writes to runtime state and refreshes the
parameter sections in place.

## Mechanical Contract

### Context window payload

Compaction-class and transcript-injection tools return this shape:

```python
{
    "context_window": [
        {"kind": "parameter", "label": str, "content": str},
        {"kind": "tool_call", "tool_key": str, "arguments": dict},
        {"kind": "tool_result", "tool_key": str, "output": dict | str},
        {"kind": "assistant", "content": str},
        {"kind": "context", "label": str, "content": str},
    ]
}
```

Rules:

- Parameter entries are preserved unless the tool explicitly writes to the
  parameter zone.
- Transcript entries may be reordered, removed, collapsed, or appended
  depending on the tool.
- Group 5 tools are additive. They do not remove existing transcript entries.

### Group 1 LLM subcalls

Group 1 handlers and the lightweight LLM-backed Group 2 handlers use the
agent's `normal` model slot for a synchronous secondary call. The transcript,
or relevant transcript slice, is serialized into one user message. The tool's
instruction text is used as the system prompt. `model_override` can be supplied
when a harness wants a cheaper or faster summarization model.

## Group 1: LLM Summarization

These tools preserve parameter entries and replace transcript history with one
synthetic summary result.

| Key | Purpose |
| --- | --- |
| `context.summarize.headline` | 3-5 sentence executive summary |
| `context.summarize.chronological` | Strict past-tense timeline |
| `context.summarize.state_snapshot` | Current world state only |
| `context.summarize.decisions` | Decision and rationale log |
| `context.summarize.errors` | Failure and retry log |
| `context.summarize.extracted_data` | Facts-only extraction |
| `context.summarize.goals_and_gaps` | Completed vs remaining objective mapping |
| `context.summarize.entities` | Entity registry with last-known status |
| `context.summarize.open_questions` | Uncertainty and unresolved assumptions |

Common behavior:

- Parameter entries are preserved verbatim.
- The transcript is replaced by one `tool_result` entry whose `tool_key` is the
  invoked summarization tool.
- The output includes the generated summary plus token counts when available.

## Group 2: Structural Manipulation

These tools are deterministic unless otherwise noted.

| Key | Purpose |
| --- | --- |
| `context.struct.truncate` | Keep the last N transcript entries and prepend a drop marker |
| `context.struct.strip_outputs` | Strip tool-result bodies while preserving the call sequence |
| `context.struct.deduplicate` | Collapse similar repeated tool results |
| `context.struct.reorder` | Move one transcript entry to the newest position |
| `context.struct.collapse_chain` | Collapse a contiguous range into one summary entry |
| `context.struct.redact` | Replace matching content with a redaction label |
| `context.struct.merge_sections` | Merge two non-contiguous ranges with a lightweight LLM call |
| `context.struct.window_slice` | Keep only a contiguous transcript slice |
| `context.struct.fold_by_tool_key` | Fold one tool's history while keeping other entries intact |

## Group 3: Selective Window Tools

These tools let the agent explicitly choose what survives, what gets promoted,
and what gets checkpointed.

| Key | Purpose |
| --- | --- |
| `context.select.extract_and_collapse` | Keep specific indices and collapse the rest |
| `context.select.filter_by_tool_key` | Keep only specified tool keys |
| `context.select.promote_and_strip` | Write one transcript entry into memory and remove it from the transcript |
| `context.select.annotate_entry` | Append an agent-authored note or tag to an entry |
| `context.select.checkpoint` | Persist the full current window as an audit checkpoint |
| `context.select.keep_by_tag` | Keep only previously tagged entries |
| `context.select.split_and_promote` | Promote the pre-split transcript into memory and keep the post-split transcript verbatim |

Notes:

- `checkpoint` is pass-through. It stores a checkpoint but returns the live
  context window unchanged.
- `promote_and_strip` and `split_and_promote` bridge transcript history into the
  parameter zone through runtime-backed memory fields.

## Group 4: Parameter Zone Injection

These tools write to the runtime context state, persist it, and then call
`refresh_parameters()` so the change appears immediately in the active window.

| Key | Purpose |
| --- | --- |
| `context.param.inject_section` | Create a new named parameter section |
| `context.param.update_section` | Replace an existing section's content |
| `context.param.append_memory_field` | Append to a memory field governed by the append rule |
| `context.param.overwrite_memory_field` | Replace a memory field governed by the overwrite rule |
| `context.param.write_once_memory_field` | Write a field exactly once |
| `context.param.inject_directive` | Add a dynamic directive to the effective system prompt |
| `context.param.clear_memory_field` | Clear a field with an explicit sentinel |
| `context.param.bulk_write_memory` | Apply multiple memory writes atomically |

Memory-field update rules:

- `append`
- `overwrite`
- `write_once`

Default field rules are defined in the shared agent types so harnesses can use
standard names like `continuation_pointer`, `verified_outputs`, and
`open_questions`.

## Group 5: Transcript Injection

These tools return a `context_window` payload that contains the current window
plus one or more additive entries.

| Key | Purpose |
| --- | --- |
| `context.inject.synthetic_tool_result` | Insert a synthetic tool result |
| `context.inject.assistant_note` | Insert a labeled synthetic assistant message |
| `context.inject.tool_call_pair` | Insert a synthetic call/result pair |
| `context.inject.context_block` | Insert a labeled free-form context block |
| `context.inject.task_reminder` | Re-state the task objective and current progress signals |
| `context.inject.replay_memory` | Pull memory-field values into the transcript as a synthetic result |
| `context.inject.handoff_brief` | Inject a structured post-reset orientation brief |
| `context.inject.progress_marker` | Insert a lightweight milestone marker |

Synthetic entries are marked so they can be distinguished from live tool
results during inspection and testing.

## Runtime Integration

The implementation lives in:

```text
harnessiq/tools/context/
    __init__.py
    summarization.py
    structural.py
    selective.py
    parameter.py
    injection.py
```

Shared runtime pieces:

- Tool keys are defined in `harnessiq/shared/tools.py`.
- BaseAgent context-window support lives in `harnessiq/agents/base/agent.py`.
- The normalized context and runtime-state dataclasses live in
  `harnessiq/shared/agents.py`.

BaseAgent behavior:

- Groups 1, 2, 3, and 5 are included in `_COMPACTION_TOOL_KEYS`.
- Group 4 is not a compaction class and records its tool result in the
  transcript.
- Runtime-backed context state persists across cycles and resets.
- Dynamic directives are appended to the effective system prompt rather than
  mutating the base system prompt text.

## Recommended Lifecycle Usage

| Phase | Recommended tools |
| --- | --- |
| Context pressure building | `struct.truncate`, `struct.strip_outputs`, `struct.deduplicate`, `summarize.headline`, `param.append_memory_field`, `param.bulk_write_memory` |
| Focused sub-task entry | `struct.window_slice`, `select.filter_by_tool_key`, `inject.task_reminder`, `inject.progress_marker` |
| Phase boundary | `select.split_and_promote`, `struct.fold_by_tool_key`, `param.inject_section` |
| Pre-reset consolidation | `summarize.state_snapshot`, `summarize.goals_and_gaps`, `summarize.open_questions`, `select.checkpoint`, `param.bulk_write_memory` |
| Post-reset orientation | `inject.handoff_brief`, `inject.replay_memory`, `inject.task_reminder` |
| Error recovery | `summarize.errors`, `struct.redact`, `inject.assistant_note` |

## Allowed Tools Guidance

Harness authors should grant only the subset needed by the agent's workflow.

Minimal reset-safe set:

```text
context.summarize.headline
context.param.overwrite_memory_field
context.param.append_memory_field
context.param.bulk_write_memory
context.inject.handoff_brief
```

Research-oriented set:

```text
context.summarize.extracted_data
context.summarize.entities
context.summarize.goals_and_gaps
context.struct.deduplicate
context.struct.truncate
context.param.append_memory_field
context.param.overwrite_memory_field
context.param.bulk_write_memory
context.inject.handoff_brief
context.inject.task_reminder
```

Filesystem and data-processing set:

```text
context.summarize.state_snapshot
context.struct.strip_outputs
context.struct.fold_by_tool_key
context.struct.redact
context.select.split_and_promote
context.param.overwrite_memory_field
context.param.bulk_write_memory
context.inject.handoff_brief
context.inject.progress_marker
```

Debugging-oriented set:

```text
context.summarize.errors
context.summarize.chronological
context.struct.deduplicate
context.struct.collapse_chain
context.struct.redact
context.inject.assistant_note
context.param.inject_directive
```

## Notes

- The context-tool family is opt-in at the BaseAgent level through
  `enable_context_tools()`.
- The runtime state stores injected sections, memory fields, directives, and
  checkpoints separately from the rolling transcript.
- The implementation preserves compatibility with the existing context
  compaction and prompting helpers by extending them to understand `assistant`
  and `context` entry kinds.
