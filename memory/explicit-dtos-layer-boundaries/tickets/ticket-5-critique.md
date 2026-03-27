Post-critique review found one meaningful regression in the first DTO pass: prepared-request clients were forwarding empty DTO `query` and `path_params` mappings as `{}` instead of preserving the prior `None` semantics for "argument not supplied". Provider families like Apollo and Paperclip interpret any non-`None` query mapping as an explicit query payload, so valid operations began failing at the boundary.

Implemented improvements:

- Normalized every prepared-request client adapter to pass `request.path_params or None` and `request.query or None` into the existing provider-specific request builders.
- Removed the dead Google Drive payload helper functions from the tool module so request validation now has a single owner in the DTO-driven client path.

Reverification after the critique changes:

- `python -m pytest tests/test_interfaces.py tests/test_apollo_provider.py tests/test_attio_provider.py tests/test_creatify_provider.py tests/test_exa_provider.py tests/test_expandi_provider.py tests/test_inboxapp_provider.py tests/test_instantly_provider.py tests/test_lemlist_provider.py tests/test_lusha_provider.py tests/test_outreach_provider.py tests/test_paperclip_provider.py tests/test_serper_provider.py tests/test_smartlead_provider.py tests/test_zerobounce_provider.py tests/test_browser_use_provider.py tests/test_google_drive_provider.py tests/test_arxiv_provider.py tests/test_apollo_agent.py tests/test_exa_agent.py tests/test_instantly_agent.py tests/test_outreach_agent.py tests/test_exa_outreach_agent.py tests/test_knowt_tools.py -q`
- `python -m pytest tests/test_google_drive_provider.py tests/test_sdk_package.py -q`
- Apollo provider-tool smoke check repeated successfully.
