# Provider API Expansion — Ticket Index

## Summary of Research Findings

All missing operations identified by researching official API documentation.

| # | Provider | Style | Missing Operations | Priority |
|---|---|---|---|---|
| 1 | Lemlist | new-style | ~30 ops: pause/start campaign, schedules, sequence steps, tasks, lead state, contacts, email accounts, lemwarm, DB search | HIGH |
| 2 | Outreach | new-style | ~40 ops: email addresses, phone numbers, snippets, personas, teams, roles, mailings, events, notes, opportunity stages | HIGH |
| 3 | PhantomBuster | old-style | ~6 ops: save_agent, launch_sync, launch_soon, unschedule_all, get_deleted, container_result_object | MEDIUM |
| 4 | ZoomInfo | old-style | ~5 ops: enrich_technology, enrich_org_chart, enrich_corporate_hierarchy, lookup_enrich_fields, lookup_search_fields | MEDIUM |
| 5 | People Data Labs | old-style | ~3 ops: enrich_ip, get_person_changelog, enrich_person_preview | MEDIUM |
| 6 | Coresignal | old-style | ~10 ops: multi_source_employee, employee_posts, real_time_employee, multi_source_company, enrich_company_by_website, historical_headcount, multi_source_jobs | HIGH |
| 7 | LeadIQ | old-style | ~4 ops: get_account, flat_advanced_search, grouped_advanced_search, submit_person_feedback | LOW |
| 8 | Snov.io | old-style | TBD | MEDIUM |
| 9 | Arcads | new-style | None — public API is fully covered | N/A |
| 10 | Creatify | new-style | Already comprehensive (50+ ops) | N/A |
| 11 | Instantly | new-style | Already comprehensive (70+ ops) | N/A |
| 12 | Exa | new-style | Already comprehensive | N/A |
| 13 | Proxycurl | deprecated | Shut down Jan 2025 — skip | N/A |

## Tickets

- [ticket-1.md](ticket-1.md) — Lemlist API expansion
- [ticket-2.md](ticket-2.md) — Outreach API expansion
- [ticket-3.md](ticket-3.md) — PhantomBuster API expansion
- [ticket-4.md](ticket-4.md) — ZoomInfo API expansion
- [ticket-5.md](ticket-5.md) — People Data Labs API expansion
- [ticket-6.md](ticket-6.md) — Coresignal API expansion
- [ticket-7.md](ticket-7.md) — LeadIQ API expansion
