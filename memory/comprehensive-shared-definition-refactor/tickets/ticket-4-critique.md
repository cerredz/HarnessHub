Post-Critique Review for issue-180

Findings
- The first integration pass still left several provider-local constant/type bundles outside `harnessiq/shared/`, specifically provider HTTP error/protocol types, LangSmith env/config constants, and provider-specific request/endpoint constants in `arxiv`, `leadiq`, and `salesforge`.
- The initial regression test only spot-checked a few exported definitions and would not have caught future drift back into `agents/` or `providers/`.
- The first implementation of the audit test assumed UTF-8 source without BOM and failed on existing BOM-encoded agent modules, which would have made the enforcement noisy rather than useful.

Changes Made
- Moved the remaining shared-definition surfaces into `harnessiq/shared/http.py`, `harnessiq/shared/langsmith.py`, and the existing shared provider modules for arXiv, LeadIQ, Salesforge, and generic provider errors.
- Updated provider and CLI modules to import those moved definitions through the shared layer while preserving compatibility re-exports from the existing package surfaces.
- Added an AST-based regression test that audits `harnessiq/agents/` and `harnessiq/providers/` for top-level shared-definition classes/constants, with explicit allowances only for local path wiring in agents and ParamSpec/TypeVar aliases in the LangSmith helper.
- Hardened that audit to read source with `utf-8-sig` so BOM-encoded files are handled correctly.
