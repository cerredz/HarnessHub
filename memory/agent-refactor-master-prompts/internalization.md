### 1a: Structural Survey

**Repository shape:**
- `harnessiq/` — production Python SDK package, installed via `pyproject.toml`
- `harnessiq/agents/` — three flat Python files today: `base.py`, `email.py`, `linkedin.py` plus a thin `__init__.py` re-exporter
- `harnessiq/shared/` — domain-specific shared definitions (agents.py, linkedin.py, tools.py, etc.)
- `harnessiq/tools/` — tool registry, built-ins, and MCP-style service tool factories
- `harnessiq/providers/` — AI and external service API clients/request builders
- `harnessiq/config/` — credential loader and provider credential models
- `harnessiq/cli/` — argparse entrypoint + LinkedIn sub-commands
- `tests/` — per-module unit tests, all using `unittest.TestCase`

**Agent layer today:**
- `base.py` — abstract `BaseAgent` class; owns the run loop, context window assembly, transcript recording, context compaction, and reset logic. Imports shared types from `harnessiq.shared.agents`.
- `email.py` — abstract `BaseEmailAgent(BaseAgent)`; owns Resend tool wiring, system-prompt generation, and credential masking. Imports from `harnessiq.agents.base`.
- `linkedin.py` — concrete `LinkedInJobApplierAgent(BaseAgent)` plus `LinkedInMemoryStore` (manages durable file-based state: job preferences, user profile, action log, applied jobs, managed files, screenshots). Memory path is a required constructor arg today. Also contains `build_linkedin_browser_tool_definitions`, helper utilities, coercion functions.
- `__init__.py` — re-exports everything from all three files so `from harnessiq.agents import X` works for all public symbols.

**Persistent memory today (LinkedIn agent):**
- `LinkedInMemoryStore(memory_path)` writes runtime files to a caller-supplied `memory_path` (default in CLI is `memory/linkedin/{agent_name}/`, configured via `--memory-root`). There is no default memory path in the Python API.
- `BaseEmailAgent` and `BaseAgent` have no file-based persistent memory.

**Package surface:**
- `harnessiq/__init__.py` lazily exposes modules via `__getattr__`; `_EXPORTED_MODULES = {"agents", "cli", "config", "providers", "tools"}`. Adding a new module requires adding it to this frozenset.

**Convention patterns:**
- Each major subsystem has its own `__init__.py` that re-exports public symbols, so import paths stay stable even when internal files move.
- Tests import from public package paths (`from harnessiq.agents import ...`) — never from internal module paths.
- CLI (`commands.py`) imports both from `harnessiq.agents` (public) and `harnessiq.agents.linkedin` (internal) for symbols not re-exported at the top level.
- Tool definitions, handlers, and utilities are co-located in single files; no separate `handlers/` layer.
- Frozen dataclasses with `slots=True` are the convention for all config and record types.

---

### 1b: Task Cross-Reference

**Change 1 — Agent subfolder restructure**

Every agent gets its own subdirectory under `harnessiq/agents/`:

| Today | After |
|---|---|
| `harnessiq/agents/base.py` | `harnessiq/agents/base/agent.py` + `harnessiq/agents/base/__init__.py` |
| `harnessiq/agents/email.py` | `harnessiq/agents/email/agent.py` + `harnessiq/agents/email/__init__.py` |
| `harnessiq/agents/linkedin.py` | `harnessiq/agents/linkedin/agent.py` + `harnessiq/agents/linkedin/__init__.py` |

Memory folders per agent:
- `harnessiq/agents/base/memory/` — placeholder; `BaseAgent` is abstract, no runtime state files
- `harnessiq/agents/email/memory/` — placeholder; `BaseEmailAgent` has no file-based state today
- `harnessiq/agents/linkedin/memory/` — **default persistent memory location** for `LinkedInJobApplierAgent`; all the runtime state files (`applied_jobs.jsonl`, `action_log.jsonl`, etc.) live here when no explicit `memory_path` is supplied

Import compatibility: Python resolves `harnessiq.agents.base`, `harnessiq.agents.email`, and `harnessiq.agents.linkedin` to the `__init__.py` of the corresponding subpackage, so all existing import statements in tests and CLI remain valid without modification.

Files affected:
- CREATE: `harnessiq/agents/base/__init__.py`, `harnessiq/agents/base/agent.py`, `harnessiq/agents/base/memory/.gitkeep`
- CREATE: `harnessiq/agents/email/__init__.py`, `harnessiq/agents/email/agent.py`, `harnessiq/agents/email/memory/.gitkeep`
- CREATE: `harnessiq/agents/linkedin/__init__.py`, `harnessiq/agents/linkedin/agent.py`, `harnessiq/agents/linkedin/memory/.gitkeep`
- MODIFY: `harnessiq/agents/__init__.py` — update relative imports from `.base`, `.email`, `.linkedin` to the same names (no change needed; Python resolves the package automatically)
- MODIFY: `harnessiq/agents/linkedin/agent.py` — make `memory_path` optional, default to `Path(__file__).parent / "memory"`
- DELETE: `harnessiq/agents/base.py`, `harnessiq/agents/email.py`, `harnessiq/agents/linkedin.py`

**Change 2 — Master prompts module**

New module `harnessiq/master_prompts/`:
- `harnessiq/master_prompts/__init__.py` — public API: `MasterPrompt` dataclass, `MasterPromptRegistry`, module-level `get_prompt()` / `list_prompts()` / `get_prompt_text()` convenience functions
- `harnessiq/master_prompts/registry.py` — `MasterPrompt` frozen dataclass and `MasterPromptRegistry` class that locates JSON files inside the `prompts/` sibling directory
- `harnessiq/master_prompts/prompts/create_master_prompts.json` — first prompt (key: `create_master_prompts`)

SDK access pattern the user described:
```python
from harnessiq.master_prompts import get_prompt, list_prompts
prompt = get_prompt("create_master_prompts")
system_prompt_text = prompt.prompt  # inject into any agent or API call
```

Also via lazy module access:
```python
import harnessiq
prompt = harnessiq.master_prompts.get_prompt("create_master_prompts")
```

Files affected:
- CREATE: `harnessiq/master_prompts/__init__.py`, `harnessiq/master_prompts/registry.py`, `harnessiq/master_prompts/prompts/create_master_prompts.json`
- MODIFY: `harnessiq/__init__.py` — add `"master_prompts"` to `_EXPORTED_MODULES`
- CREATE: `tests/test_master_prompts.py` — unit tests
- MODIFY: `artifacts/file_index.md` — document new layout

---

### 1c: Assumption & Risk Inventory

1. **Default memory path for LinkedIn agent**: Making `memory_path` optional with default `Path(__file__).parent / "memory"` inside the installed package is the right interpretation. The CLI already has its own `--memory-root` mechanism and passes explicit paths, so the CLI flow is unaffected. The Python API default will point to the in-repo `harnessiq/agents/linkedin/memory/` directory, which is the user's explicit intention.

2. **`from_memory` classmethod**: This also takes `memory_path` as required; it should receive the same `None` default resolving to the same default path. The logic that creates a temporary `LinkedInMemoryStore` before the main constructor must apply the same resolution.

3. **Email and base agent memory folders**: No persistent state currently — the `memory/` folders are structural placeholders. `.gitkeep` files will make them visible in the repository without adding non-code content.

4. **Import backward compatibility**: Converting `base.py` → `base/` (a package) preserves `from harnessiq.agents.base import X` semantics because Python maps `harnessiq.agents.base` to the package `__init__.py`. No test or CLI file needs modification for ticket 1.

5. **`SUPPORTED_LINKEDIN_RUNTIME_PARAMETERS` re-export**: This symbol is imported directly from `harnessiq.agents.linkedin` in `cli/commands.py`. It must be present in `harnessiq/agents/linkedin/__init__.py`.

6. **Master prompt JSON schema**: The user specified `title`, `description`, and `prompt`. The `key` is derived from the filename (without extension) at load time — not stored in the JSON — so renaming a file changes its key. This is the cleanest convention and avoids redundancy.

7. **Master prompts bundled with package**: JSON files under `harnessiq/master_prompts/prompts/` must be included in the installed package. The `pyproject.toml` uses `setuptools` with `include-package-data = true` and finds all `harnessiq*` packages. A `MANIFEST.in` or `package-data` config may be needed to ensure `.json` files are included. Using `importlib.resources` (stdlib) for loading ensures compatibility.

**Phase 1 complete.**
