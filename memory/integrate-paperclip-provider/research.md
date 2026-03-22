## Paperclip Research Notes

Primary sources used:
- Project site: https://paperclip.ing/
- GitHub repository: https://github.com/paperclipai/paperclip
- API docs:
  - https://github.com/paperclipai/paperclip/blob/master/docs/api/overview.md
  - https://github.com/paperclipai/paperclip/blob/master/docs/api/authentication.md
  - https://github.com/paperclipai/paperclip/blob/master/docs/api/companies.md
  - https://github.com/paperclipai/paperclip/blob/master/docs/api/agents.md
  - https://github.com/paperclipai/paperclip/blob/master/docs/api/issues.md
  - https://github.com/paperclipai/paperclip/blob/master/docs/api/approvals.md
  - https://github.com/paperclipai/paperclip/blob/master/docs/api/activity.md
  - https://github.com/paperclipai/paperclip/blob/master/docs/api/costs.md
- Agent developer guides:
  - https://github.com/paperclipai/paperclip/blob/master/docs/guides/agent-developer/heartbeat-protocol.md
  - https://github.com/paperclipai/paperclip/blob/master/docs/guides/agent-developer/task-workflow.md
  - https://github.com/paperclipai/paperclip/blob/master/docs/guides/agent-developer/comments-and-communication.md
  - https://github.com/paperclipai/paperclip/blob/master/docs/adapters/http.md

High-confidence product/capability findings:
- Paperclip is a self-hosted control plane for coordinating external AI agents rather than an LLM runtime itself.
- It organizes agents into companies with org charts, budgets, goals, projects, issues, approvals, and heartbeats.
- It is explicitly "bring your own agent"; supported adapter styles include local runtimes and HTTP webhooks.
- The integration point relevant to Harnessiq is the REST API, not Paperclip’s internal server/runtime code.

API characteristics:
- Base URL: `http://localhost:3100/api` by default.
- Auth: bearer token for agent API keys and run JWTs; session cookies for board operators.
- Response shape: JSON entity bodies on success, `{\"error\": \"...\"}` on failure.
- Mutation convention during heartbeats: include `X-Paperclip-Run-Id`.
- Conflict semantics: `409` is meaningful, especially for issue checkout; docs explicitly say not to blindly retry.

Most integration-worthy endpoint groups:
- Companies: list/get/create/update/archive.
- Agents: list/get/me/create/update/pause/resume/terminate/create key/invoke heartbeat/org chart/list adapter models/config revisions/rollback.
- Issues: list/get/create/update/checkout/release/comments/documents/document revisions.
- Approvals: list/get/create/request hire/approve/reject/request revision/resubmit/issues/comments.
- Activity: list immutable activity feed.
- Costs: report cost events and fetch summaries.

Important workflow semantics from upstream docs:
- Agents should start a heartbeat by calling `GET /api/agents/me`.
- Assignment inbox is driven by `GET /api/companies/{companyId}/issues?assigneeAgentId=...&status=todo,in_progress,blocked`.
- Work should start with `POST /api/issues/{issueId}/checkout`; a `409` means another agent owns the task and should not be retried.
- Status changes and progress comments should be captured via `PATCH /api/issues/{issueId}` and/or issue comments, with run-id tracing.
- Delegation is modeled as creating child issues with `parentId` and usually `goalId`.
- Comments with `@AgentName` can wake mentioned agents.

Integration design conclusion:
- A single `paperclip.request` MCP-style tool cleanly matches both the upstream API style and Harnessiq’s existing provider-backed tool architecture.
- The first implementation should stay JSON-first and exclude attachment/logo upload endpoints because they require multipart transport and would complicate the current generic provider abstraction.
