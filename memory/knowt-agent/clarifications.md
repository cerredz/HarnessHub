## Phase 2 — Clarifying Questions

---

**Q1 — Reasoning tools: local scaffolds vs. LLM-powered generation**

*Ambiguity*: "Output reasoning tokens based on their description" could mean two fundamentally different things:

- **Option A (local)**: The tools are pure Python — they take structured inputs (topic, context, count) and return a structured text scaffold. For example, `reason.brainstorm(topic="TikTok hooks", count=10)` returns a formatted template that the agent reads from its context window and then uses to drive its own reasoning in the next turn. No API calls.
- **Option B (LLM-powered)**: The tools invoke a language model themselves (would require an `AgentModel` parameter passed at construction time) to actually generate ideas or chain-of-thought text before returning. This breaks the current pattern where LLM generation is the agent loop's responsibility.

**Why it matters**: Option B requires a substantially different implementation — the tools would need an `AgentModel` injected into them, which is unusual in this SDK. Option A is fully consistent with the existing tool pattern.

*My recommendation is Option A*, but please confirm.

---

**Q2 — `create_video`: actual API call or stub?**

*Ambiguity*: The repository has two video-creation providers already integrated — **Creatify** (`harnessiq/tools/creatify/`) and **Arcads** (`harnessiq/tools/arcads/`). The `create_video` Knowt tool needs to either:

- **Option A**: Delegate to one of these providers under the hood (which one?).
- **Option B**: Be a standalone tool that assembles a video creation job description / structured payload from the script + avatar description (no external API call — acts as a "prepare and return" step the agent could then feed into Creatify/Arcads manually).
- **Option C**: Be a stub that signals to the agent that video creation is ready (i.e., all prerequisites are met), and the agent calls the Creatify or Arcads tool directly in its next turn.

**Why it matters**: Option A requires knowing which provider and building an API call. Options B/C are self-contained but may not actually create the video.

---

**Q3 — `create_script`: single-tool with embedded brainstorm, or multi-step using reasoning tools?**

*Ambiguity*: The spec says `create_script` should "output brainstorm tool for 10-15 ideas, then create script, then store in agent memory." This could mean:

- **Option A**: `create_script` is a single tool that returns a multi-section output: a brainstorm list (10-15 ideas) + the selected/generated script + confirmation that it stored the script in memory. The agent calls one tool and gets all three in one result.
- **Option B**: The agent flow is: first call `reason.brainstorm(...)` → agent sees 10-15 ideas in context → then calls `create_script(topic, selected_idea)` → script is generated and stored. Two separate tool calls.

**Why it matters**: Option A keeps logic in one tool; Option B makes reasoning tools genuinely reusable in the Knowt workflow. The answer changes how many tools exist and how the agent's tool call sequence is designed.

---

**Q4 — Agent memory: in-memory (session-scoped) or file-backed (persistent across runs)?**

*Ambiguity*: "Deterministic memory of the agent we can validate in code" could mean:

- **Option A (in-memory)**: `KnowtAgentMemory` is a simple dataclass held on the agent instance. `script_created` and `avatar_description_created` are boolean flags reset when the agent is re-instantiated. Sufficient if the entire script → avatar → video pipeline completes in one `run()` call.
- **Option B (file-backed)**: Like `LinkedInMemoryStore`, state persists to disk. The current script and avatar description are written to files so a resumed run knows they were already created.

**Why it matters**: File persistence adds the full `prepare()` + file I/O pattern (like the LinkedIn harness). In-memory is simpler but loses state if the run is interrupted.

---

**Q5 — Vidbyte/Knowt master prompt content: provide actual content or accept placeholders?**

*Ambiguity*: The master prompt must contain Vidbyte background, common pain points, ICP, example TikTok scripts, and recent scripts. None of this content was provided in the task.

- **Option A (placeholders)**: The prompt file is scaffolded with clearly labeled `[TODO: ...]` sections that the user fills in. The structure, format, and all static agent guidance is complete; only domain data is missing.
- **Option B (you provide content now)**: You supply the actual Vidbyte company background, ICP details, pain points, and 2-3 example scripts directly in this conversation, and I incorporate them into the prompt file.

**Why it matters**: Option A lets me ship a fully functional prompt skeleton immediately. Option B requires you to provide the actual Knowt/Vidbyte business context now.

---

## Responses

**Q1** → B. The tool returns a structured dict containing a `reasoning_instruction` field. That instruction text tells the model to output reasoning tokens about the given topic/task. The tool result appears in the transcript (context window) and the agent produces its reasoning in the next assistant turn.

**Q2** → Creatify. `create_video` calls `create_lipsync_v2` (AI Avatar v2). The tool parameters map directly to the Creatify API payload. Creatify `CreatifyClient` is injected at construction time.

**Q3** → B (multi-step). Agent flow: `reason.brainstorm(...)` → agent reasons through ideas → `knowt.create_script(topic, angle, script_text)` to finalize and store. The reasoning tool and the script tool are separate tool calls.

**Q4** → B (file-backed). `KnowtMemoryStore` persists `current_script.md`, `current_avatar_description.md`, `creation_log.jsonl` to disk — same pattern as `LinkedInMemoryStore`.

**Q5** → Placeholders. Master prompt scaffolded with clearly labeled `[TODO: ...]` sections.

**Implementation notes from responses**:
- Reasoning tools: inject `reasoning_instruction` string into context window via standard tool_result path — no special BaseAgent handling needed
- `create_video` → `create_lipsync_v2`; tool input schema = lipsync_v2 API payload fields
- Memory guard on `create_video`: if `current_script.md` or `current_avatar_description.md` are absent/empty, return semantic error dict
- `create_file` / `edit_file` → write to memory directory, mirror LinkedIn's `write_managed_text_file` pattern
