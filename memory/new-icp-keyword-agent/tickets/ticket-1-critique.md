Self-critique findings:

- The most likely long-term risk was schema drift between persisted leads and the retrieval surface. I kept a single canonical `lead_database.json` contract and derived `get_emails()` from it to avoid dual-write drift.
- Search history and canonical lead state are separated so recent-search context can stay compact without losing the all-time email list.
- The memory-store API is intentionally narrow; adding downstream outreach or verification state later should happen in separate files rather than overloading the current lead schema.

Post-critique changes made:

- Kept the persisted lead/email contract centralized in `InstagramLeadDatabase`.
- Ensured runtime parameter normalization is explicit and rejects unknown keys.
