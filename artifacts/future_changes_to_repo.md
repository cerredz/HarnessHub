# Future Changes To Repo

This artifact translates the generalized best-practices guidance into concrete future guardrails for Harnessiq. It is not a refactor plan for today. It is a target state for keeping the repository low-debt as the SDK grows.

## Current Strengths Worth Preserving

- The repo already has meaningful architectural boundaries: `agents/`, `shared/`, `tools/`, `toolset/`, `providers/`, `cli/`, and `utils/`.
- The runtime has a strong shared center in [`harnessiq/agents/base/agent.py`](/C:/Users/Michael%20Cerreto/HarnessHub/harnessiq/agents/base/agent.py), which prevents copy-paste agent loops.
- Shared dataclass-heavy models such as [`harnessiq/shared/leads.py`](/C:/Users/Michael%20Cerreto/HarnessHub/harnessiq/shared/leads.py) push invariants toward construction time.
- Provider integrations are usually broken into `api.py`, `client.py`, and `operations.py`, which is a healthy separation of transport, execution, and request mapping.
- The tool layer is reusable and composable rather than being trapped inside individual agents.
- The repo already treats architecture artifacts as maintained assets, which is a major advantage if kept current.

## Target Dependency Direction

Aim for this dependency graph and enforce it over time:

- `shared` -> standard library or other `shared` modules only
- `providers` -> `shared`, `providers.base`, `providers.http`
- `tools` -> `shared`, `providers`
- `toolset` -> `shared`, `tools`
- `agents` -> `shared`, `tools`, `toolset`
- `cli` -> `agents`, `shared`, `config`, `utils`
- `utils` -> low-level shared/runtime infrastructure only

Practical implication:

- upward imports should be treated as debt unless there is a very strong reason
- sideways imports should trigger scrutiny for hidden coupling
- cycles should be rejected by default

## Recommended Future Changes

### 1. Add mechanical import-boundary checks

The repo currently documents boundaries, but those rules should eventually be enforced in CI.

Recommended checks:

- `shared` must not import from `agents`, `cli`, `tools`, or most of `providers`
- `agents` should not reach into provider internals when a tool-layer seam exists
- `cli` should remain a thin adapter over SDK surfaces rather than becoming a second business layer
- cyclical imports between top-level packages should fail CI

Suggested tool:

- `import-linter`, `grimp`, or a small custom AST-based import check

### 2. Tighten `shared/` into a true foundation layer

`shared/` should be the least-coupled part of the runtime. Most of the repo already uses it that way, but there are places where higher-layer dependencies leak downward.

Example worth correcting over time:

- [`harnessiq/shared/email.py`](/C:/Users/Michael%20Cerreto/HarnessHub/harnessiq/shared/email.py) currently imports from `harnessiq.tools.resend`

Target state:

- `shared/` contains types, constants, protocols, value objects, and pure normalization
- tool construction and operation lookup stay in `tools/` or `providers/`

### 3. Formalize public internal APIs

Some modules are effectively public inside the monolith because many other packages depend on them. Those modules should expose intentional import surfaces instead of letting callers pull from deep internals.

Candidates:

- `toolset`
- `shared` model packages
- provider credential/client surfaces
- agent package exports

Concrete move:

- prefer package-level exports or dedicated `public.py` modules for broad consumers
- avoid encouraging imports from deep implementation files unless that file is the intended public entrypoint

### 4. Keep agents orchestration-only

This is already a documented norm and should become stricter as new agents are added.

Future additions should keep:

- prompt assembly in prompt files or prompt helpers
- reusable memory/config/state models in `shared/`
- executable tools in `tools/`
- provider behavior in `providers/`
- agent modules focused on workflow, runtime glue, and domain-specific orchestration

If an agent file grows because it starts owning schemas, helper registries, or provider logic, split that immediately.

### 5. Standardize the provider-to-tool adapter pattern

The repo already uses a repeatable provider structure. Preserve that pattern and document it as the required template for future providers:

- `api.py` for URL/header/request-building helpers
- `client.py` for authenticated execution
- `operations.py` for operation catalog plus tool-facing preparation
- `tools/<provider>/operations.py` for the executable tool layer

The value is not just neatness. It gives every future provider the same seam locations for testing, migration, and debugging.

### 6. Add architecture tests for canonical patterns

Unit tests already cover behavior well. Add a small architecture-test layer so the repo checks structural promises too.

Good examples:

- all provider tool families expose deterministic keys
- all tool factories return `RegisteredTool` tuples
- new providers include matching tests for credentials, client, operations, and tool factory
- prompt-driven agents load prompt assets from files, not embedded multi-hundred-line strings

### 7. Publish a "one obvious way" guide for repeated work

The codebase is large enough that repeated decisions should have a default answer.

Examples worth codifying:

- how to add a provider
- how to add a tool family
- how to add a new agent harness
- how to model durable memory
- how to add runtime parameters
- how to write artifact updates when architecture changes

This can live partly in docs and partly in small reference modules.

### 8. Treat prompts and durable memory as first-class interfaces

In this repo, prompt files and memory schemas are not incidental assets. They are part of the product surface.

Future guardrails:

- prompt placeholders must stay explicit and validated
- memory file names and shapes should be stable or migrated deliberately
- prompt/memory changes should be reviewed with the same seriousness as Python API changes

### 9. Separate generated state from maintained source more aggressively

This repository carries long-lived `memory/` artifacts intentionally, but transient runtime noise should not become part of the maintained source tree.

Future hygiene targets:

- avoid checked-in temp files
- keep browser caches and run outputs outside long-term source paths where possible
- distinguish durable design artifacts from ephemeral execution by convention

This reduces review noise and keeps architectural intent visible.

### 10. Keep `artifacts/` current whenever boundaries change

The repo already depends on `artifacts/file_index.md` as a structural guide. That only works if updates happen at the same time as the architectural change.

Rule of thumb:

- if a new top-level boundary appears, update `artifacts/file_index.md`
- if a new default pattern becomes blessed, add or update an artifact
- if a pattern is no longer blessed, remove or deprecate the old documentation

## Suggested Enforcement Order

If these changes are implemented incrementally, this is the highest-leverage order:

1. Add import-boundary checks for top-level packages.
2. Tighten `shared/` so it only contains foundational concepts.
3. Formalize public import surfaces for heavily consumed packages.
4. Add architecture tests for provider/tool/agent conventions.
5. Improve transient-state hygiene and artifact upkeep.

## Design Questions For Future PRs

Before merging a non-trivial change, ask:

- Does this preserve the intended dependency direction?
- Am I creating a new canonical pattern or a one-off?
- Could this logic live in a reusable seam instead of a concrete agent or CLI command?
- Am I widening a public surface accidentally?
- If this needed to be migrated later, what would the expand/contract path be?

If the answers are unclear, the design is probably carrying debt already.
