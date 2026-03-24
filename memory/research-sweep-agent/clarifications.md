No blocking ambiguities remain after Phase 1.

Implementation decisions to keep aligned with repository conventions:

- Use the shared manifest + platform CLI adapter architecture for the authoritative SDK/CLI integration.
- Keep Serper credentials in the existing provider-credential path for the platform CLI instead of introducing raw API-key custom params.
- Add a direct `research-sweep` top-level CLI family for parity with the design doc and existing repo ergonomics.
- Realize the design doc’s restricted context-tool surface by filtering the live context tool registry instead of changing the public `create_context_tools()` signature.
