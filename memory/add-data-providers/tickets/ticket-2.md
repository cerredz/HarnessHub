# Ticket 2: Snov.io Provider

## Title
Add `harnessiq/providers/snovio/` — full Snov.io API client

## Intent
Implement a complete Snov.io provider package covering OAuth2 token exchange, email discovery, email verification, prospect list management, and campaign operations. Snov.io is an email finding and outreach platform whose API is central to LinkedIn prospecting workflows.

## Scope
**Creates:**
- `harnessiq/providers/snovio/__init__.py`
- `harnessiq/providers/snovio/api.py`
- `harnessiq/providers/snovio/client.py`
- `harnessiq/providers/snovio/requests.py`
- `harnessiq/providers/snovio/credentials.py`
- `tests/test_snovio_provider.py`

**Does not touch:** any other provider, any agent, config layer internals.

## Relevant Files
| File | Change |
|---|---|
| `harnessiq/providers/snovio/__init__.py` | Create: public exports |
| `harnessiq/providers/snovio/api.py` | Create: URLs, headers |
| `harnessiq/providers/snovio/client.py` | Create: `SnovioClient` dataclass |
| `harnessiq/providers/snovio/requests.py` | Create: request builders |
| `harnessiq/providers/snovio/credentials.py` | Create: `SnovioCredentials` TypedDict |
| `tests/test_snovio_provider.py` | Create: unit tests |

## API Reference

**Base URL:** `https://api.snov.io`
**Authentication:** OAuth 2.0 — POST `/v1/oauth/access_token` with `client_id`, `client_secret`, `grant_type=client_credentials` → returns `{access_token, token_type, expires_in}`. Access token passed as `access_token` query/body parameter in subsequent calls.

**Endpoints:**

| Method | Path | Description |
|---|---|---|
| POST | /v1/oauth/access_token | Get OAuth2 access token |
| GET | /v1/get-domain-search | Search emails by domain (`domain`, `type`, `limit`, `lastId`) |
| GET | /v1/get-emails-count | Count emails available for domain (`domain`, `type`) |
| POST | /v1/get-emails-from-names | Find emails by name + domain (`firstName`, `lastName`, `domain`) |
| POST | /v1/get-email-info | Get info for a known email (`email`) |
| POST | /v1/email-verifier | Verify email deliverability (`email`) |
| POST | /v1/get-profile-emails | Get emails from social URL (`url`) |
| POST | /v1/url-search | Find prospect from social profile URL (`url`) |
| GET | /v1/get-prospect | Get prospect by ID (`id`) |
| POST | /v1/add-prospect | Add a prospect to a list (`email`, `fullName`, `listId`, optional fields) |
| POST | /v1/update-prospect | Update prospect fields (`id`, field map) |
| DELETE | /v1/delete-prospect | Delete prospect (`id`) |
| GET | /v1/prospect-list | Get all prospect lists |
| GET | /v1/get-list | Get specific prospect list (`listId`) |
| POST | /v1/add-to-list | Add email to list (`email`, `listId`) |
| DELETE | /v1/delete-from-list | Remove email from list (`listId`, `email`) |
| GET | /v1/get-all-campaigns | List all campaigns |
| GET | /v1/get-campaign-data | Get campaign details (`id`) |
| GET | /v1/get-campaign-recipients | Get campaign recipients (`id`, `status`) |
| GET | /v1/get-campaign-recipient-status | Get recipient status (`email`, `campaignId`) |
| POST | /v1/add-to-campaign | Add recipients to campaign (`id`, `emails`) |
| POST | /v1/start-campaign | Start a campaign (`id`) |
| POST | /v1/pause-campaign | Pause a campaign (`id`) |
| GET | /v2/me | Get current user info |

## Approach

**`credentials.py`:**
```python
from harnessiq.config.models import ProviderCredentialConfig

class SnovioCredentials(ProviderCredentialConfig):
    client_id: str
    client_secret: str
```

**`api.py`:**
- `DEFAULT_BASE_URL = "https://api.snov.io"`
- `build_auth_headers()` — no auth header (token in body/query param for v1)
- URL builder per endpoint: `access_token_url()`, `domain_search_url()`, etc.
- `build_token_request(client_id, client_secret)` — returns form-encoded body for token exchange

**`requests.py`:** One builder function per endpoint accepting typed keyword args, returning `dict[str, object]` via `omit_none_values()`. Token exchange uses form data (not JSON).

**`client.py`:**
```python
@dataclass(frozen=True, slots=True)
class SnovioClient:
    client_id: str
    client_secret: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0
    request_executor: RequestExecutor = request_json
```
Methods: `get_access_token()`, `domain_search(access_token, domain, ...)`, `get_emails_count(...)`, `get_emails_from_names(...)`, `get_email_info(...)`, `verify_email(...)`, `get_profile_emails(...)`, `url_search(...)`, `get_prospect(...)`, `add_prospect(...)`, `update_prospect(...)`, `delete_prospect(...)`, `get_prospect_lists(...)`, `get_list(...)`, `add_to_list(...)`, `delete_from_list(...)`, `get_all_campaigns(...)`, `get_campaign(...)`, `get_campaign_recipients(...)`, `get_campaign_recipient_status(...)`, `add_to_campaign(...)`, `start_campaign(...)`, `pause_campaign(...)`, `get_user_info(access_token)`

## Assumptions
- Token exchange is a form POST (application/x-www-form-urlencoded), not JSON.
- All other endpoints accept the `access_token` as a URL query parameter (`?access_token=...`).
- The `SnovioClient` stores `client_id` and `client_secret` for token acquisition; callers are responsible for managing token lifecycle.

## Acceptance Criteria
- [ ] `from harnessiq.providers.snovio import SnovioClient, SnovioCredentials` works
- [ ] `build_access_token_request(client_id, client_secret)` returns correct form body
- [ ] `build_domain_search_request(access_token, domain)` includes required params
- [ ] `build_verify_email_request(access_token, email)` includes correct fields
- [ ] All optional fields omitted when `None` via `omit_none_values()`
- [ ] All request builders return `dict[str, object]`
- [ ] `SnovioClient` is a frozen dataclass with slots
- [ ] Tests cover all endpoint request builders with assertions on payload shape
- [ ] All existing tests remain green

## Verification Steps
1. `python -m pytest tests/test_snovio_provider.py -v`
2. `python -m pytest tests/ -v`
3. `python -c "from harnessiq.providers.snovio import SnovioClient; print('ok')"`
4. `python -m py_compile harnessiq/providers/snovio/*.py`

## Dependencies
- Ticket 1 (config layer — `ProviderCredentialConfig` base type)

## Drift Guard
This ticket must not modify any other provider package, any agent module, or any existing test file.
