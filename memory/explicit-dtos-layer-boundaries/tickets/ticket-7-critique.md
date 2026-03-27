Post-critique review found one concrete gap in the first DTO pass: the new public request DTOs were wired into the main provider-client seams, but a few optional nested config fields in the OpenAI and Anthropic request builders still assumed raw mappings and would have deep-copied DTO objects directly into the outgoing JSON body if callers passed DTO-backed config fragments.

Implemented improvements:

- Updated [harnessiq/providers/openai/requests.py](C:/Users/422mi/HarnessHub/.worktrees/issue-332/harnessiq/providers/openai/requests.py) so esponse_format and 	ext serialize DTO values through 	o_dict() before transport payload emission.
- Updated [harnessiq/providers/anthropic/messages.py](C:/Users/422mi/HarnessHub/.worktrees/issue-332/harnessiq/providers/anthropic/messages.py) so 	hinking also serializes DTO values through 	o_dict() before transport payload emission.
- Added regression coverage in [tests/test_openai_provider.py](C:/Users/422mi/HarnessHub/.worktrees/issue-332/tests/test_openai_provider.py) and [tests/test_anthropic_provider.py](C:/Users/422mi/HarnessHub/.worktrees/issue-332/tests/test_anthropic_provider.py) to prove DTO-backed optional config fragments now translate into plain JSON mappings at the wire boundary.

Reverification after the critique change:

- python -m py_compile harnessiq\providers\openai\requests.py harnessiq\providers\anthropic\messages.py tests\test_openai_provider.py tests\test_anthropic_provider.py
- python -m pytest tests/test_openai_provider.py tests/test_anthropic_provider.py tests/test_gemini_provider.py tests/test_grok_provider.py tests/test_provider_base.py tests/test_agent_models.py tests/test_interfaces.py tests/test_sdk_package.py -q
- The DTO smoke check for OpenAI, Anthropic, Gemini, and Grok repeated successfully.
