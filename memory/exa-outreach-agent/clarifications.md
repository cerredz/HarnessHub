# Clarifications — ExaOutreach Agent

## Questions & Answers

**Q1 — Email address source**
**A:** Option A — Exa-only. `search_and_contents` returns full page text; the agent extracts contact info from profile content. No Hunter.io provider.

**Q2 — Email composition / email_data parameter**
**A:** `email_data` is a constructor parameter — a list of email template objects, each with: `title`, `subject`, `description`, `links`, `actual_email`, and optional metadata (`pain_points`, `icp`, etc.). The agent has a `get_email_template(template_id)` / `list_email_templates()` tool surface to pick which template to use per lead. Context window order: master prompt → tools → email data → rest. Results (leads found, emails sent) are saved **deterministically in Python** (inside tool handlers) via a configurable storage backend parameter. Default backend is filesystem (`run_{N}.json` per run).

**Q3 — Memory/log format**
**A:** One `run_{N}.json` file per run, where N is the next integer after counting existing run files. Each run file contains: `run_id`, `started_at`, `completed_at`, `query`, `leads_found: []`, `emails_sent: []`.

**Q4 — CLI + SDK**
**A:** Yes — both `harnessiq outreach` CLI sub-command and programmatic `harnessiq.agents.ExaOutreachAgent` export.

## Implementation Implications

- `EmailTemplate` dataclass: `id, title, subject, description, actual_email, links, pain_points, icp, extra`
- `StorageBackend` Protocol with `FileSystemStorageBackend` default
- `ExaOutreachMemoryStore` handles: run numbering, run file CRUD, `is_contacted(url)` dedup
- Tool constants: `EXA_OUTREACH_LIST_TEMPLATES`, `EXA_OUTREACH_GET_TEMPLATE`, `EXA_OUTREACH_CHECK_CONTACTED`, `EXA_OUTREACH_LOG_LEAD`, `EXA_OUTREACH_LOG_EMAIL_SENT`
- When Exa search runs (inside agent) → handler wraps call → logs leads to current run file
- When Resend send_email runs → handler wraps call → logs sent email to current run file
- `harnessiq/shared/tools.py` needs 5 new constants
- `harnessiq/agents/__init__.py` needs ExaOutreachAgent export
- `harnessiq/cli/main.py` needs `register_exa_outreach_commands` call
