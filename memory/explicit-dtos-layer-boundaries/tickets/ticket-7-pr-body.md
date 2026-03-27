Title: Convert model-provider SDK surfaces to DTO-first request contracts and export them publicly

Intent:
Replace the raw dict/list request shapes in the OpenAI, Anthropic, Gemini, and Grok provider SDK surfaces with explicit DTOs and wire those DTOs into the public package exports and tests.

Issue URL:
https://github.com/cerredz/HarnessHub/issues/332

Scope:
- Introduce shared/model-provider DTOs for the SDK request boundaries.
- Convert model-provider request builders and thin clients to DTO-first public APIs.
- Update package exports and packaging tests so DTOs are part of the public contract directly.
- Keep the underlying HTTP behavior and endpoint coverage stable.

Highlights:
- Added shared provider DTOs for canonical provider messages plus OpenAI, Anthropic, Gemini, and Grok request surfaces.
- Converted the four provider client families, request builders, runtime interfaces, and ProviderAgentModel adapter to pass DTO request objects instead of raw dict/list payloads.
- Exported the DTO-first provider contract from harnessiq.shared, harnessiq.providers, and the relevant provider subpackages.
- Updated provider, runtime, interface, and packaging tests to lock in the new DTO public contract.

## Quality Pipeline Results

## Stage 1: Static Analysis

- No repository linter or standalone static-analysis command is configured in pyproject.toml.
- Applied manual review to the model-provider seams to confirm the raw public dict/list request boundaries are now replaced by explicit DTO request objects and that each provider builder still owns the final JSON translation.

## Stage 2: Type Checking

- No project type-checker configuration is present in pyproject.toml.
- Added explicit DTO annotations across the shared provider contract layer, provider clients, request builders, runtime model interfaces, and the agent-model adapter.
- Verified syntax and import integrity with py_compile across all changed code and test files.

## Stage 3: Unit Tests

Command run:

`powershell
python -m pytest tests/test_openai_provider.py tests/test_anthropic_provider.py tests/test_gemini_provider.py tests/test_grok_provider.py tests/test_provider_base.py tests/test_agent_models.py tests/test_interfaces.py tests/test_sdk_package.py -q
`

Result:

- Passed (72 passed)
- Warnings were limited to the existing setuptools / wheel packaging deprecations during the package-build smoke path.

## Stage 4: Integration & Contract Tests

- The focused verification run exercised:
  - all four model-provider request-builder modules translating DTO requests into unchanged HTTP payload dictionaries
  - the thin SDK clients accepting DTO request objects directly
  - the model runtime protocols and ProviderAgentModel adapter using DTOs internally instead of raw provider message dicts
  - the packaged SDK export surface, including wheel import smoke tests for the new DTO public contract

## Stage 5: Smoke & Manual Verification

Command run:

`powershell
@'
from harnessiq.providers.openai import OpenAIClient, OpenAIChatCompletionRequestDTO
from harnessiq.providers.anthropic import AnthropicClient, AnthropicMessageDTO, AnthropicMessageRequestDTO
from harnessiq.providers.gemini import GeminiClient, GeminiContentDTO, GeminiGenerateContentRequestDTO, build_system_instruction
from harnessiq.providers.grok import GrokClient, GrokChatCompletionRequestDTO, build_search_parameters
from harnessiq.shared.dtos import ProviderMessageDTO

captures = []

def fake_request(method, url, **kwargs):
    captures.append({"method": method, "url": url, "json_body": kwargs.get("json_body")})
    return {"ok": True}

openai = OpenAIClient(api_key="test", request_executor=fake_request)
openai.create_chat_completion(OpenAIChatCompletionRequestDTO(
    model_name="gpt-4.1",
    system_prompt="Be precise.",
    messages=(ProviderMessageDTO(role="user", content="ping"),),
))

anthropic = AnthropicClient(api_key="test", request_executor=fake_request)
anthropic.create_message(AnthropicMessageRequestDTO(
    model_name="claude-3-7-sonnet",
    messages=(AnthropicMessageDTO(role="user", content="ping"),),
    max_tokens=256,
    system_prompt="Be precise.",
))

gemini = GeminiClient(api_key="test", request_executor=fake_request)
gemini.generate_content(GeminiGenerateContentRequestDTO(
    model_name="models/gemini-2.5-flash",
    contents=(GeminiContentDTO(role="user", parts=({"text": "ping"},)),),
    system_instruction=build_system_instruction("Be precise."),
))

grok = GrokClient(api_key="test", request_executor=fake_request)
grok.create_chat_completion(GrokChatCompletionRequestDTO(
    model_name="grok-3",
    system_prompt="Be precise.",
    messages=(ProviderMessageDTO(role="user", content="ping"),),
    search_parameters=build_search_parameters(mode="on", return_citations=True),
))

assert captures[0]["json_body"]["messages"][0]["role"] == "system"
assert captures[1]["json_body"]["messages"][0]["role"] == "user"
assert captures[2]["json_body"]["contents"][0]["role"] == "user"
assert captures[3]["json_body"]["search_parameters"]["return_citations"] is True
print("dto-smoke-ok")
'@ | python -
`

Observed output:

- dto-smoke-ok

What this confirmed:

- Each provider family accepts a DTO request object at the public client boundary.
- The providers still emit the expected JSON wire shapes after DTO translation.
- The DTO contract covers the provider-specific nested request seams that used to rely on raw dict/list inputs.

## Stage 6: Syntax Verification

Command run:

`powershell
python -m py_compile harnessiq\shared\dtos\providers.py harnessiq\shared\dtos\__init__.py harnessiq\shared\providers.py harnessiq\shared\__init__.py harnessiq\providers\base.py harnessiq\providers\__init__.py harnessiq\providers\langsmith.py harnessiq\providers\openai\client.py harnessiq\providers\openai\requests.py harnessiq\providers\openai\helpers.py harnessiq\providers\openai\__init__.py harnessiq\providers\anthropic\client.py harnessiq\providers\anthropic\messages.py harnessiq\providers\anthropic\helpers.py harnessiq\providers\anthropic\__init__.py harnessiq\providers\gemini\client.py harnessiq\providers\gemini\content.py harnessiq\providers\gemini\helpers.py harnessiq\providers\gemini\__init__.py harnessiq\providers\grok\client.py harnessiq\providers\grok\requests.py harnessiq\providers\grok\helpers.py harnessiq\providers\grok\__init__.py harnessiq\interfaces\models.py harnessiq\integrations\agent_models.py tests\test_openai_provider.py tests\test_anthropic_provider.py tests\test_gemini_provider.py tests\test_grok_provider.py tests\test_provider_base.py tests\test_agent_models.py tests\test_interfaces.py tests\test_sdk_package.py
`

Result:

- py_compile completed successfully for all changed code and test files.


## Post-Critique Changes

Post-critique review found one concrete gap in the first DTO pass: the new public request DTOs were wired into the main provider-client seams, but a few optional nested config fields in the OpenAI and Anthropic request builders still assumed raw mappings and would have deep-copied DTO objects directly into the outgoing JSON body if callers passed DTO-backed config fragments.

Implemented improvements:

- Updated [harnessiq/providers/openai/requests.py](C:/Users/422mi/HarnessHub/.worktrees/issue-332/harnessiq/providers/openai/requests.py) so esponse_format and 	ext serialize DTO values through 	o_dict() before transport payload emission.
- Updated [harnessiq/providers/anthropic/messages.py](C:/Users/422mi/HarnessHub/.worktrees/issue-332/harnessiq/providers/anthropic/messages.py) so 	hinking also serializes DTO values through 	o_dict() before transport payload emission.
- Added regression coverage in [tests/test_openai_provider.py](C:/Users/422mi/HarnessHub/.worktrees/issue-332/tests/test_openai_provider.py) and [tests/test_anthropic_provider.py](C:/Users/422mi/HarnessHub/.worktrees/issue-332/tests/test_anthropic_provider.py) to prove DTO-backed optional config fragments now translate into plain JSON mappings at the wire boundary.

Reverification after the critique change:

- python -m py_compile harnessiq\providers\openai\requests.py harnessiq\providers\anthropic\messages.py tests\test_openai_provider.py tests\test_anthropic_provider.py
- python -m pytest tests/test_openai_provider.py tests/test_anthropic_provider.py tests/test_gemini_provider.py tests/test_grok_provider.py tests/test_provider_base.py tests/test_agent_models.py tests/test_interfaces.py tests/test_sdk_package.py -q
- The DTO smoke check for OpenAI, Anthropic, Gemini, and Grok repeated successfully.

