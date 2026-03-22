No blocking clarification questions were required after Phase 1.

Rationale:
- The requested surface area is intentionally flexible ("register some functionalities"), so a curated subset of the Paperclip REST API is a reasonable product decision rather than a guess at an omitted requirement.
- The codebase already has a strong provider-backed tool pattern, which makes the implementation boundary unambiguous.
- Upstream Paperclip documentation is explicit enough to support a first-pass integration around agents, issues, approvals, activity, and costs.

Implementation implication:
- Proceed with a JSON-first Paperclip provider integration that exposes the control-plane API via a single `paperclip.request` tool and excludes multipart upload endpoints for this iteration.
