Title: Add the shared email campaign domain model and concrete durable-memory agent
Intent: Create a first-class email harness that can read Instagram leads from MongoDB, prepare batch payloads, and persist sent-history instead of relying on ad hoc scripts.
Scope: Add shared email-campaign config/store models, recipient extraction, template rendering, Mongo read support, and the concrete `EmailCampaignAgent`. Do not add CLI parsers in this ticket.
Relevant Files:
- `harnessiq/shared/email_campaign.py` — durable memory store, manifest, recipient extraction, payload helpers.
- `harnessiq/agents/email/agent.py` — allow durable email subclasses to pass memory/instance context through the base harness.
- `harnessiq/agents/email/campaign.py` — concrete durable-memory email campaign agent.
- `harnessiq/shared/dtos/agents.py` — add the explicit email-campaign instance payload DTO.
- `harnessiq/shared/dtos/__init__.py` — export the new DTO.
- `harnessiq/providers/output_sink_clients.py` — add backward-compatible Mongo document reads.
- `harnessiq/agents/email/__init__.py` — export the new concrete agent.
- `harnessiq/agents/__init__.py` — export the new concrete agent from the package root.
Approach: Model the email harness the same way Instagram models durable state: a shared memory store plus a concrete agent class. Extend the existing Mongo client with a simple read surface so recipient discovery stays outside CLI modules. Restrict the email agent to `send_batch_emails`, preload the selected recipient batch, and persist successful deliveries into sent-history.
Assumptions:
- The first supported source is MongoDB and the target source shape matches the Instagram lead-export workflow.
- Durable sent-history is required to avoid resending the same batch on subsequent runs.
- Template substitution only needs lightweight `{{field}}` replacement.
Acceptance Criteria:
- [x] A shared email-campaign memory store exists and persists source config, campaign config, runtime/custom params, identity/prompt text, and sent-history.
- [x] A concrete `EmailCampaignAgent` exists and can build a prepared recipient batch from durable memory.
- [x] Successful Resend batch sends are recorded into sent-history.
- [x] Mongo document reads are supported through reusable provider code rather than CLI business logic.
Verification Steps:
- Run focused shared and agent tests covering recipient extraction, payload rendering, and send-history recording.
- Run manifest/output-sink tests covering the Mongo read helper change.
Dependencies: None.
Drift Guard: Do not add CLI parsing logic here and do not expand the source surface beyond the Mongo-backed Instagram-leads workflow needed for this task.
