1. Google Drive authentication contract

Ambiguity:
“Via the user’s credentials” is not specific enough for implementation because Google Drive writes require OAuth-scoped credentials, and this repo currently has no interactive OAuth flow.

Why it materially affects implementation:
This determines whether I build a lightweight env-backed credential integration, a refreshable OAuth client, or a much larger browser/callback flow.

Options:
- Preferred: you provide Google OAuth fields via the existing repo-local secret pattern (`client_id`, `client_secret`, `refresh_token`, and optionally `access_token`), and I implement refresh/write support around those.
- Alternative: you want a full interactive sign-in flow in the product/CLI that obtains tokens for the user.
- Alternative: you want a service-account-based integration instead of true user credentials.

2. What exact Drive artifact should be created per successful application?

Ambiguity:
“Store ... via a folder name” could mean folder-only naming, a folder plus a metadata file, or a folder hierarchy.

Why it materially affects implementation:
The Drive data model, duplicate handling, and deterministic save logic all depend on the exact artifact contract.

Options:
- Preferred: create one folder per successful application and write a deterministic `job.json` file inside it containing the structured job/application data.
- Alternative: create one company folder and one job-specific file inside it.
- Alternative: create only folders and encode limited metadata in folder names.

3. What should the canonical local-memory payload become?

Ambiguity:
The current local record only stores `job_id`, `title`, `company`, `url`, timestamps, status, and notes, but your request adds `job description`, `salary`, `location`, and similar fields.

Why it materially affects implementation:
I need to decide whether to extend `applied_jobs.jsonl`, add a second richer artifact, or keep Drive-only extended metadata.

Options:
- Preferred: extend the local persisted job record so both local memory and Drive contain the same richer structured fields.
- Alternative: keep `applied_jobs.jsonl` lean and add a parallel rich-details artifact locally.
- Alternative: keep extended fields only in Drive, leaving local memory mostly unchanged.

4. Where do you want the optional “save to Google Drive” control exposed?

Ambiguity:
The repo already supports persisted LinkedIn runtime parameters and CLI configuration, but the request does not specify whether this is SDK-only, CLI-visible, or both.

Why it materially affects implementation:
This changes the public API surface, persistence path, docs, and test coverage.

Options:
- Preferred: support it as a LinkedIn runtime parameter persisted by CLI/SDK, defaulting to `false`.
- Alternative: SDK constructor parameter only.
- Alternative: CLI flag only for runs, without persistence in memory.

5. Deterministic naming and duplicate behavior

Ambiguity:
If the same company appears multiple times or the same job is retried, it is unclear whether Drive writes should reuse an existing folder, create a new unique one, or become a no-op.

Why it materially affects implementation:
This is the core of the deterministic storage contract.

Options:
- Preferred: derive a stable folder name from `company + title + job_id`, reuse it if it already exists, and overwrite/update a canonical metadata file inside it.
- Alternative: one stable company folder plus one stable per-job child folder.
- Alternative: append a timestamp for every successful application, even for repeats.

## Responses

1. Google Drive authentication contract

- Decision: use env-backed OAuth credentials.
- Additional requirement: the SDK must also provide a way for the user to load credentials into the SDK and save them.
- Implication: implement a persisted credential-binding path using the existing repo-local credentials-config layer, plus a concrete Google Drive credential model/client that can be constructed from resolved values.

2. Drive artifact shape

- Decision: create one deterministic folder per successful application and write a canonical `job.json` file inside it.
- Implication: implement stable folder naming from job identity and overwrite/update semantics for the metadata file.

3. Canonical local-memory payload

- Decision: local memory and Google Drive should stay aligned.
- Implication: the local persisted LinkedIn job record must be expanded or paired with a richer deterministic artifact so the same structured fields are represented locally and remotely.

4. `save_to_google_drive` control surface

- Decision: the parameter should live in the agent class parameters and be settable from both SDK and CLI.
- Implication: add a first-class LinkedIn agent/runtime parameter with a default of `false`, plumb it through constructor, persisted runtime parameters, CLI configure/run flows, and docs/tests.

5. Duplicate behavior and already-applied guard

- Decision: duplicates must deterministically not be applied to.
- Additional requirement: add an `already_applied` tool that deterministically checks the agent memory and injects the necessary message into the context window if the job has already been applied to.
- Implication: add an internal LinkedIn tool for explicit duplicate detection, and update the system prompt to require this check before submission. The tool should derive its answer from local durable memory, not from model reasoning.
