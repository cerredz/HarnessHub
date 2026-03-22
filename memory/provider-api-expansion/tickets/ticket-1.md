# Ticket 1: Lemlist API Expansion

**Title:** Expand Lemlist provider operation catalog with 30 missing API endpoints

**Intent:** The current Lemlist catalog covers basic campaign/lead CRUD but is missing campaign control (pause/resume), scheduling, sequence step management, task management, lead state operations, contact list, email account management, lemwarm (warmup), and people database search. This ticket adds all of them.

**Scope:**
- Modify: `harnessiq/providers/lemlist/operations.py` — add ~30 new `_op()` entries
- Modify: `tests/test_lemlist_provider.py` — update operation count assertion, add new op tests
- No changes to `harnessiq/tools/lemlist/operations.py` (imports dynamically from provider layer)

**New Operations:**
Campaign control: pause_campaign (POST /campaigns/{id}/pause), resume_campaign (POST /campaigns/{id}/start)
Campaign reporting: get_campaign_reports (GET /campaigns/reports)
Campaign export: start_campaign_export (GET /campaigns/{id}/export/start), get_campaign_export_status (GET /campaigns/{id}/export/{exportId}/status)
Lead state: set_lead_interested (POST /leads/interested/{leadId}), set_lead_not_interested (POST /leads/notinterested/{leadId}), pause_lead (POST /leads/pause/{leadId}), resume_lead (POST /leads/start/{leadId})
Lead variables: update_lead_variables (PATCH /leads/{id}/variables), delete_lead_variable (DELETE /leads/{id}/variables)
Lead import: import_leads_to_campaign (POST /campaigns/{id}/leads/import)
Schedules: list_schedules, create_schedule, get_schedule, update_schedule, delete_schedule; list_campaign_schedules, assign_schedule_to_campaign
Sequence steps: list_campaign_sequences (GET /campaigns/{id}/sequences), create_sequence_step, update_sequence_step, delete_sequence_step
Tasks: list_tasks, create_task, update_task, ignore_task
Team: get_team_credits (GET /team/credits), list_team_senders (GET /team/senders)
Contacts: list_contacts (GET /contacts), get_contact (GET /contacts/{idOrEmail})
Email accounts: add_email_account, delete_email_account, test_email_account
Lemwarm: start_lemwarm, pause_lemwarm, get_lemwarm_settings, update_lemwarm_settings
People DB: search_people_database (POST /database/people), search_companies_database (POST /database/companies)

**Acceptance Criteria:**
- [ ] All new operations appear in `build_lemlist_operation_catalog()`
- [ ] Each operation has correct HTTP method and path
- [ ] Test operation count updated
- [ ] New operations are accessible via `get_lemlist_operation(name)`
- [ ] Tool definition enum includes all new operations

**Dependencies:** None
