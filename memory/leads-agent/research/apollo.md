## Apollo API Research Report

Research date: March 18, 2026

Scope:

- Validate Apollo’s official API surface for prospect discovery and enrichment.
- Identify the minimum operation set needed for a first-class Harnessiq integration.
- Identify authentication, credit, and rate-limit constraints that materially affect agent design.

### Executive Summary

Apollo is a strong fit for this leads-agent use case because its official API cleanly separates:

- net-new people discovery (`People API Search`)
- company discovery (`Organization Search`)
- person enrichment (`People Enrichment`, `Bulk People Enrichment`)
- company enrichment (`Organization Enrichment`, `Bulk Organization Enrichment`)
- durable CRM-style persistence inside Apollo (`Create Contact`, `Search for Contacts`, `View a Contact`, `Update a Contact`)
- downstream campaign execution (`Search for Sequences`, `Add Contacts to a Sequence`)
- operational introspection (`View API Usage Stats and Rate Limits`)

The most important design constraint is that Apollo’s API has two distinct modes:

- search endpoints that are optimized for discovery
- enrichment/contact endpoints that are optimized for revealing or persisting data and may consume credits

For the leads agent, that means the optimal v1 flow is:

1. search net-new people or organizations first
2. enrich only shortlisted results
3. optionally convert enriched people into Apollo contacts
4. optionally attach contacts to sequences

This avoids burning credits on broad exploratory queries.

### Official API Findings

Authentication and access model:

- Apollo’s official docs state that customer integrations should use an API key, while partner integrations can use OAuth 2.0 on behalf of users.
- The Create API Keys guide shows endpoint-scoped API keys and a “master key” option for all endpoints.
- Several important endpoints for this integration explicitly require a master API key, including People API Search, sequence operations, user lookup, and usage/rate-limit inspection.

Operational implication:

- The Harnessiq Apollo integration should support API-key auth first.
- The credential model should make “master key required” explicit because a partial key will fail for core leads-agent operations.

Discovery endpoints:

- `POST /api/v1/mixed_people/api_search` is Apollo’s net-new people discovery endpoint.
- Apollo documents that this endpoint is optimized for API usage, does not consume credits, and is intended for prospecting.
- The “Find People Using Filters” tutorial shows canonical filters such as `person_titles`, `person_locations`, `organization_locations`, and `per_page`, and it explicitly recommends using returned `id` values as inputs to bulk enrichment.
- `POST /api/v1/mixed_companies/search` is the organization discovery endpoint.
- Apollo documents that organization search does consume credits.

Operational implication:

- The leads agent should prefer people-first discovery when the ICP is person-centric and only fall back to company-first discovery when company filters or missing-role logic make that necessary.
- The Apollo provider should expose people and organization search as separate operations rather than trying to collapse them into one generic search call.

Enrichment endpoints:

- `POST /api/v1/people/match` enriches one person.
- `POST /api/v1/people/bulk_match` enriches up to 10 people in one call.
- Apollo states that richer inputs improve match quality.
- By default, personal emails and phone numbers are not returned; callers must explicitly request them.
- Waterfall enrichment can be triggered with `run_waterfall_email` and `run_waterfall_phone`, and webhook delivery is used for asynchronous completion of those waterfall data fields.
- `GET /api/v1/organizations/enrich` enriches one company.
- `POST /api/v1/organizations/bulk_enrich` enriches up to 10 companies.

Operational implication:

- The Apollo provider should support both single and bulk enrichment operations, but the leads agent should use bulk enrichment for shortlisted batches.
- Waterfall enrichment should not be mandatory in v1 because it introduces webhook handling, asynchronous completion state, and idempotency requirements. It is better modeled as an optional future extension unless the user explicitly wants webhook plumbing now.

Apollo-native persistence and outreach endpoints:

- `POST /api/v1/contacts` creates a contact inside Apollo.
- Apollo documents that contact creation does not deduplicate unless `run_dedupe=true` is set.
- `POST /api/v1/contacts/search` searches only contacts already added to the team account; it is not a net-new search endpoint.
- `GET /api/v1/contacts/{contact_id}` and `PATCH /api/v1/contacts/{contact_id}` support retrieval and updates for persisted contacts.
- `POST /api/v1/emailer_campaigns/search` searches sequences.
- `POST /api/v1/emailer_campaigns/{sequence_id}/add_contact_ids` adds contacts to an Apollo sequence, and only contacts can be added.

Operational implication:

- Apollo contact creation is a useful optional save destination for the leads agent.
- The save path should set `run_dedupe=true` whenever Apollo contact creation is used.
- Sequence enrollment belongs in provider operations, but not in the core leads-agent persistence contract; it should be an optional downstream workflow.

Usage and rate-limit introspection:

- `POST /api/v1/usage_stats/api_usage_stats` returns usage plus rate limits.
- Apollo documents rate limits per minute, hour, and day, and notes that plan tier affects those limits.
- Bulk enrichment endpoints are documented as throttled to half of the single-enrichment per-minute limit while matching the same hourly and daily limits.

Operational implication:

- The leads agent should expose a budget-aware mode and use the usage endpoint when Apollo is configured.
- The runtime should not hard-code Apollo limits because limits are plan-dependent.

### Recommended Apollo v1 Operation Set

Recommended provider operations to implement in the repo:

- `search_people`
- `search_organizations`
- `enrich_person`
- `bulk_enrich_people`
- `enrich_organization`
- `bulk_enrich_organizations`
- `create_contact`
- `search_contacts`
- `view_contact`
- `update_contact`
- `search_sequences`
- `add_contacts_to_sequence`
- `view_usage_stats`

Why this set:

- It fully covers discovery, enrichment, Apollo-native save, and optional sequence handoff.
- It is large enough to make Apollo a first-class provider in the repo.
- It avoids webhook-heavy waterfall handling in the initial pass while still leaving room for future support.

### Integration Recommendations For Harnessiq

Credential model:

- Add `ApolloCredentials` with `api_key`, `base_url` defaulting to `https://api.apollo.io`, and `timeout_seconds`.
- In docs and validation, call out that many leads-agent operations require a master API key.

Provider structure:

- Follow the established repo pattern:
  - `harnessiq/providers/apollo/api.py`
  - `harnessiq/providers/apollo/credentials.py`
  - `harnessiq/providers/apollo/requests.py`
  - `harnessiq/providers/apollo/client.py`
  - `harnessiq/providers/apollo/operations.py`
  - `harnessiq/tools/apollo/operations.py`
  - `harnessiq/tools/apollo/__init__.py`

Tool surface:

- Expose one MCP-style request tool at `apollo.request`.
- Use operation names and payload/query/path separation consistent with other providers in this repo.

Leads-agent behavior when Apollo is present:

- Use Apollo people search as a primary discovery path for title-driven ICPs.
- Use Apollo organization search or organization enrichment when company filtering is central.
- Batch enrich shortlisted Apollo people IDs before save.
- If saving into Apollo, create contacts with dedupe enabled.
- Inspect usage stats before large enrichment bursts if Apollo is configured.

### Known Risks / Caveats

- Official docs show the tutorial examples using `X-Api-Key` while the reference UI labels credentials as Bearer. I infer Apollo accepts API-key-based authentication at the HTTP layer and that implementation should match the reference examples carefully during coding.
- People search does not directly return full contact channels; enrichment is required for complete contact data.
- Waterfall enrichment is asynchronous and webhook-based, which adds implementation complexity not justified for the first pass unless explicitly required.
- Organization search consumes credits, so a company-first strategy should be budget-aware.
- Rate limits are plan-dependent, so the integration should expose usage/rate introspection rather than assume fixed quotas.

### Sources

- Apollo Developer Hub: https://docs.apollo.io/
- APIs Overview: https://docs.apollo.io/docs/api-overview
- Create API Keys: https://docs.apollo.io/docs/create-api-key
- Authentication: https://docs.apollo.io/reference/authentication
- Apollo API FAQs: https://docs.apollo.io/docs/apollo-api-faqs
- People API Search: https://docs.apollo.io/reference/people-api-search
- Find People Using Filters: https://docs.apollo.io/docs/find-people-using-filters
- People Enrichment: https://docs.apollo.io/reference/people-enrichment
- Bulk People Enrichment: https://docs.apollo.io/reference/bulk-people-enrichment
- Organization Search: https://docs.apollo.io/reference/organization-search
- Organization Enrichment: https://docs.apollo.io/reference/organization-enrichment
- Bulk Organization Enrichment: https://docs.apollo.io/reference/bulk-organization-enrichment
- Create a Contact: https://docs.apollo.io/reference/create-a-contact
- Search for Contacts: https://docs.apollo.io/reference/search-for-contacts
- Convert Enriched People to Contacts: https://docs.apollo.io/docs/convert-enriched-people-to-contacts
- Search for Sequences: https://docs.apollo.io/reference/search-for-sequences
- Add Contacts to a Sequence: https://docs.apollo.io/reference/add-contacts-to-sequence
- View API Usage Stats and Rate Limits: https://docs.apollo.io/reference/view-api-usage-stats
