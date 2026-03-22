# Ticket 4: Salesforge Provider

## Title
Add `harnessiq/providers/salesforge/` — full Salesforge API client

## Intent
Implement a complete Salesforge provider package. Salesforge is an AI-powered sales engagement platform supporting campaign management, contact management, mailbox configuration, email sequence automation, and analytics.

## Scope
**Creates:**
- `harnessiq/providers/salesforge/__init__.py`
- `harnessiq/providers/salesforge/api.py`
- `harnessiq/providers/salesforge/client.py`
- `harnessiq/providers/salesforge/requests.py`
- `harnessiq/providers/salesforge/credentials.py`
- `tests/test_salesforge_provider.py`

## Relevant Files
| File | Change |
|---|---|
| `harnessiq/providers/salesforge/__init__.py` | Create: public exports |
| `harnessiq/providers/salesforge/api.py` | Create: URL, headers |
| `harnessiq/providers/salesforge/client.py` | Create: `SalesforgeClient` dataclass |
| `harnessiq/providers/salesforge/requests.py` | Create: request builders |
| `harnessiq/providers/salesforge/credentials.py` | Create: `SalesforgeCredentials` TypedDict |
| `tests/test_salesforge_provider.py` | Create: unit tests |

## API Reference

**Base URL:** `https://api.salesforge.ai`
**Authentication:** `Authorization: Bearer {api_key}` header

**Endpoints:**

| Method | Path | Description |
|---|---|---|
| GET | /public/api/v1/sequence | List all sequences/campaigns |
| POST | /public/api/v1/sequence | Create a new sequence |
| GET | /public/api/v1/sequence/{id} | Get sequence details |
| PATCH | /public/api/v1/sequence/{id} | Update sequence settings |
| DELETE | /public/api/v1/sequence/{id} | Delete a sequence |
| POST | /public/api/v1/sequence/{id}/contact | Add contacts to a sequence |
| GET | /public/api/v1/sequence/{id}/contact | List contacts in a sequence |
| DELETE | /public/api/v1/sequence/{id}/contact/{contactId} | Remove contact from sequence |
| GET | /public/api/v1/contact | List contacts |
| POST | /public/api/v1/contact | Create a contact |
| GET | /public/api/v1/contact/{id} | Get contact details |
| PATCH | /public/api/v1/contact/{id} | Update contact |
| DELETE | /public/api/v1/contact/{id} | Delete contact |
| GET | /public/api/v1/mailbox | List connected mailboxes |
| GET | /public/api/v1/mailbox/{id} | Get mailbox details |
| GET | /public/api/v1/sequence/{id}/stats | Sequence performance stats |
| GET | /public/api/v1/contact/{id}/activity | Contact activity history |
| POST | /public/api/v1/sequence/{id}/pause | Pause a sequence |
| POST | /public/api/v1/sequence/{id}/resume | Resume a sequence |
| GET | /public/api/v1/unsubscribe | List unsubscribed contacts |
| POST | /public/api/v1/unsubscribe | Add contact to unsubscribe list |
| DELETE | /public/api/v1/unsubscribe | Remove contact from unsubscribe list |

## Approach

**`credentials.py`:**
```python
class SalesforgeCredentials(ProviderCredentialConfig):
    api_key: str
```

**`api.py`:**
- `DEFAULT_BASE_URL = "https://api.salesforge.ai"`
- `build_headers(api_key)` → `{"Authorization": f"Bearer {api_key}"}`
- URL builder per endpoint group: `sequences_url()`, `sequence_url(sequence_id)`, `contacts_url()`, etc.

**`requests.py`:** Builder functions per operation. Contact and sequence creation accept keyword args. `omit_none_values()` for optional fields.

Key builders:
- `build_create_sequence_request(name, mailbox_id, *, daily_limit, timezone, ...)`
- `build_add_contacts_to_sequence_request(contacts)` where contacts is list of dicts
- `build_create_contact_request(first_name, last_name, email, *, company, title, linkedin_url, ...)`
- `build_update_contact_request(**fields)` — only non-None fields included
- Stats/list requests are GET with optional query params, returned as dicts

**`client.py`:**
```python
@dataclass(frozen=True, slots=True)
class SalesforgeClient:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0
    request_executor: RequestExecutor = request_json
```
Methods mirror each endpoint above.

## Assumptions
- Salesforge uses Bearer token (API key) auth.
- Path prefix is `/public/api/v1/`.
- Sequence is the primary campaign-equivalent object.
- Response format is JSON in all cases.

## Acceptance Criteria
- [ ] `from harnessiq.providers.salesforge import SalesforgeClient, SalesforgeCredentials` works
- [ ] `build_create_sequence_request(name="Q1 Outreach", mailbox_id="mb_1")` returns correct shape
- [ ] `build_add_contacts_to_sequence_request([{"email": "a@b.com"}])` wraps list correctly
- [ ] `build_headers(api_key)` returns `Authorization: Bearer {api_key}`
- [ ] Optional fields omitted when `None`
- [ ] All existing tests remain green

## Verification Steps
1. `python -m pytest tests/test_salesforge_provider.py -v`
2. `python -m pytest tests/ -v`
3. `python -c "from harnessiq.providers.salesforge import SalesforgeClient; print('ok')"`
4. `python -m py_compile harnessiq/providers/salesforge/*.py`

## Dependencies
- Ticket 1

## Drift Guard
Must not touch agent modules, other providers, or existing test files.
