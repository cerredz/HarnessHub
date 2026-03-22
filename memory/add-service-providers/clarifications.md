## Clarifications

### Q1: What is "arcards"?
Response: User confirmed it is **arcads** (arcads.ai) — an AI video/image ad creator.
- Base URL: `https://external-api.arcads.ai`
- Auth: Basic Auth with `clientId:clientSecret` (Base64 encoded)
- Resources: Products, Folders, Situations, Scripts, Videos

### Q2: Where should these providers live?
Response: `harnessiq/providers/` — as explicitly stated in the task.

### Q3: Config layer scope?
Response: Create `harnessiq/config/` fresh with minimal CredentialLoader (`.env`-backed, per credential-config-loader clarifications Q1) plus credential models for all 6 providers. CLI commands (ticket #30 of prior work) are out of scope.

### Q4: Depth of "full functionality"?
Response (inferred from "build out the full functionality of the api/documentation"): Cover all documented resource categories with primary CRUD operations per resource. Skip internal admin/billing/audit-log endpoints for large providers.

---

## API Research Summary

| Provider | Base URL | Auth Method | Resource Count |
|---|---|---|---|
| creatify | `https://api.creatify.ai` | `X-API-ID` + `X-API-KEY` headers | 20 resource types |
| arcads | `https://external-api.arcads.ai` | Basic Auth (`clientId:clientSecret`) | 5 resource types |
| instantly | `https://api.instantly.ai/api/v2` | `Authorization: Bearer <key>` | 29 resource types |
| outreach | `https://api.outreach.io/api/v2` | OAuth 2.0 Bearer token | 40+ resource types (core: 12) |
| lemlist | `https://api.lemlist.com/api` | Basic Auth (empty user, API key as password) | 19 resource types |
| exa | `https://api.exa.ai` | `x-api-key` header | 6 endpoint groups |

Phase 2 complete — no remaining blockers.
