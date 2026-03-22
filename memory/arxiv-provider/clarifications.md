## Phase 2 Clarifications

### Q1 — "Embedding search" scope
**Ambiguity:** The tweet mentions "embedding search tools" but the native arXiv API only supports keyword search (title/abstract/author/category field prefixes). Semantic/embedding search would require a third-party service (e.g. Semantic Scholar, a vector DB pipeline).

**Why it matters:** If we need embedding search, this becomes a multi-service integration ticket. If it's out of scope for this provider (just keyword search), we can ship immediately and cleanly.

**Options:**
- (a) Keyword-only — implement the native arXiv API faithfully; embedding search is a separate future provider
- (b) Two-operation tool — add `semantic_search` via Semantic Scholar's free passage-search API alongside `search`
- (c) Treat "embedding search" as agent-level reasoning over keyword results — not a distinct API operation

---

### Q2 — Response normalization (XML → dict)
**Ambiguity:** The arXiv API returns Atom 1.0 XML. All other providers in this codebase return raw JSON which flows straight through to the agent. Should we normalize the XML response into clean Python dicts (paper records with id, title, authors, abstract, published, categories, pdf_url fields), or return the raw XML string?

**Why it matters:** Normalized dicts are far more useful for agents. But parsing XML in the provider deviates from how every other provider handles its response (pass-through). It's the right call architecturally but I want to confirm.

**Options:**
- (a) Parse XML → return `list[dict]` of normalized paper records (strongly recommended for agent usability)
- (b) Return raw Atom XML string (consistent with pass-through pattern, but difficult for agents to consume)

---

### Q3 — Paper download operation
**Ambiguity:** The reference MCP (`blazickjp/arxiv-mcp-server`) includes `download_paper` and `read_paper` tools that fetch a paper's content from arXiv and store it locally. The HarnessHub filesystem tools already handle file I/O separately.

**Why it matters:** Including PDF/source download in the arXiv provider would introduce local file coupling (writing to disk). Excluding it keeps the provider purely as a data retrieval layer (metadata + abstracts).

**Options:**
- (a) Metadata-only — `search` + `get_paper` operations only; agents use filesystem tools for any file storage
- (b) Include `download_paper` — fetches the PDF URL and returns binary or writes to a path (couples to filesystem)

---

### Q4 — Rate-limit enforcement
**Ambiguity:** arXiv ToS requires ≤1 request/3 seconds. The `arxiv.py` library bakes in a `delay_seconds=3.0` default. No other HarnessHub provider enforces delays internally.

**Why it matters:** Building in a sleep delays every single tool call by 3 seconds even in tests. Documenting it as the caller's responsibility is consistent with the rest of the codebase.

**Options:**
- (a) Document-only — note the rate limit in the tool description; no sleep
- (b) Optional `delay_seconds` param on the client (default 0.0, caller sets 3.0 if needed)
- (c) Hard-coded 3-second delay in the client (matches arXiv ToS strictly)

---

## Responses

**Q1 → (a) Keyword-only.** Implement native arXiv API search only; embedding search is future scope.

**Q2 → Two separate operations within the tool:** `search` returns normalized `list[dict]` (parsed Atom XML); `search_raw` returns raw Atom XML string.

**Q3 → Both, two separate operations:** `get_paper` returns normalized paper dict; `download_paper` downloads PDF to a local path.

**Q4 → (b) Optional `delay_seconds` param on `ArxivConfig`, default `0.0`.** Caller sets `delay_seconds=3.0` to comply with arXiv ToS.

### Follow-on implication
`ToolsetRegistry._resolve_provider_tool` and `_resolve_family` both hard-fail when `credentials is None` regardless of `requires_credentials`. The registry must be patched to respect `entry.requires_credentials=False` before arXiv can be called without credentials.
