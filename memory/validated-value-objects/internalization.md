### 1a: Structural Survey

The authoritative runtime package is `harnessiq/`. The repository is a Python 3.11+ SDK/package built with setuptools and exercised primarily through `unittest`-style tests under `tests/`. The architecture is layered and consistent at a high level:

- `harnessiq/shared/` carries cross-cutting runtime types, constants, manifests, provider operation catalogs, and many of the dataclasses that normalize runtime state.
- `harnessiq/providers/` wraps external systems and model APIs. Service-provider packages generally expose `api.py`, `client.py`, `operations.py`, and sometimes `credentials.py`/`requests.py`.
- `harnessiq/tools/` exposes tool definitions and handlers, including provider-backed request tools and context/reasoning tools.
- `harnessiq/config/` owns persisted configuration, model profiles, harness profiles, and provider-credential metadata.
- `harnessiq/agents/` orchestrates harness behavior on top of shared manifests, tools, and providers.
- `artifacts/file_index.md` is a generated, high-signal architecture index and confirms `harnessiq/` is the source of truth.

The main conventions relevant to this task are:

- Validation is commonly done in `__post_init__` or local coercion helpers with repeated `str.strip()` / `<= 0` checks.
- Shared types already exist for some higher-level concepts, but primitive validated values are not centralized.
- Provider request surfaces are declarative, but their description strings are still assembled ad hoc per module.
- Tests are focused and file-local. Provider credential classes and tool surfaces already have targeted coverage, which makes a scoped refactor feasible.

Key inconsistencies surfaced during survey:

- String validation is duplicated across `harnessiq/shared/credentials.py`, `harnessiq/shared/google_drive.py`, `harnessiq/shared/resend_models.py`, `harnessiq/config/credentials.py`, `harnessiq/config/provider_credentials/models.py`, and several provider/model clients.
- Numeric validation is duplicated across context and reasoning helpers using raw `int` checks after `coerce_int`.
- Some provider layers rely on validated shared credential dataclasses, while others still read/process raw strings directly (`harnessiq/providers/exa/client.py`, model-provider clients, output-sink metadata helpers).
- Tool descriptions are validated only implicitly as strings and are composed repeatedly in provider operation modules.

### 1b: Task Cross-Reference

The user’s requested pattern is “invalid primitive values cannot be constructed,” with injection points in strings, credentials, env loading, provider layers, tool-description strings, and now integer indices/counts as well.

Concrete codebase mapping:

- Shared primitive-validation foundation does not exist yet and should live under `harnessiq/shared/`, which matches the user’s request and the repo’s conventions for cross-cutting runtime types.
- Env string / credential binding seams:
  - `harnessiq/config/credentials.py`
  - `harnessiq/config/provider_credentials/models.py`
  - `harnessiq/config/provider_credentials/api.py`
  - `harnessiq/providers/exa/client.py`
  - `harnessiq/shared/credentials.py`
  - `harnessiq/shared/google_drive.py`
  - `harnessiq/shared/resend_models.py`
- Provider-layer string seams:
  - `harnessiq/providers/http.py` for URL joining and provider inference inputs
  - model-provider clients like `harnessiq/providers/anthropic/client.py` and analogous wrappers that still accept raw `str` config
  - output sink/provider metadata helpers such as `harnessiq/providers/output_sink_metadata.py`
- Tool description / schema string seams:
  - `harnessiq/shared/tools.py`
  - `harnessiq/providers/base.py`
  - provider operation modules such as `harnessiq/providers/apollo/operations.py` and peers with `_build_tool_description`
  - tool-definition helper entrypoints like `harnessiq/tools/context/__init__.py`
- Integer injection points:
  - `harnessiq/tools/context/__init__.py` currently exposes `coerce_int` with no semantic guarantee beyond “is an integer”
  - `harnessiq/tools/context/executors/structural.py` performs downstream range and positivity checks for `keep_last`, `start_index`, `end_index`, `preserve_latest_n`, `keep_latest_n`, and `max_gap`
  - `harnessiq/tools/reasoning/core.py`, `harnessiq/tools/reasoning/injectable.py`, and `harnessiq/tools/reasoning/lenses.py` enforce bounded integer semantics after accepting raw ints
  - JSON schema definitions in context/reasoning tool factories already encode some minimums, but runtime parsing still trusts raw ints and re-validates repeatedly

Behavior that must be preserved:

- Public credential dataclasses and tool-definition interfaces must remain import-compatible.
- Existing tests for provider credentials, tool schemas, and context/reasoning tools must continue to pass.
- Error messages should stay clear and actionable even if the internal validation mechanism changes.
- Generated artifacts are not the source of truth; implementation must modify live code and only touch artifacts if they are part of the accepted surface.

Blast radius:

- High leverage but manageable. The repeated validation is centralized around a small number of core files.
- The credential refactor can affect most service providers via shared credential dataclasses.
- The integer validation refactor can affect many context/reasoning handlers but is still localized to shared coercion logic and a few executor modules.

### 1c: Assumption & Risk Inventory

- Assumption: The user wants a shared value-object layer, not merely helper functions. This is supported by the example and by the instruction to place shared pieces under `harnessiq/shared/`.
- Assumption: “Different parse methods for each platform” maps cleanly onto distinct validated scalar constructors/parsers for env vars, provider family names, URLs, tool descriptions, non-negative indices, and bounded counts.
- Assumption: The request is best handled incrementally through tickets rather than a repo-wide primitive rewrite in one patch. A one-shot rewrite would create unnecessary risk and review noise.
- Risk: Replacing dataclass field annotations with custom value-object types could break public APIs if done too aggressively. Compatibility needs to be preserved by accepting plain primitives at boundaries and normalizing internally.
- Risk: Some validations are semantic rather than merely structural. For example, context indices may be zero-based and valid at `0`, while counts like `keep_last` must be strictly positive. The shared numeric layer needs more than one integer type.
- Risk: Tool-description centralization can drift into content rewrites instead of structural cleanup. Ticket scope must keep description behavior stable while introducing typed construction points.
- Risk: There are existing untracked `memory/` artifacts in the worktree; implementation must avoid disturbing unrelated user artifacts.

Phase 1 complete.
