# Ticket 4: Update Shared Documentation for New GTM Providers

## Title
Document the new Attio, InboxApp, and Serper provider/tool families

## Issue URL
https://github.com/cerredz/HarnessHub/issues/174

## Intent
Once the provider families are implemented, the public SDK documentation should reflect the expanded tool surface so users can discover the new providers and their credential expectations.

## Scope
In scope:
- Update public-facing documentation for the new provider families.
- Ensure any provider counts or category descriptions remain accurate.

Out of scope:
- New CLI commands.
- Long-form guides or tutorials for each provider.

## Relevant Files
- `README.md`: update provider/tool listings, examples, and credential snippets if needed.
- `tests/test_sdk_package.py`: update only if package/documentation-visible exports require smoke coverage.

## Approach
Make the minimum documentation changes needed to keep the public surface truthful after tickets 1-3 land.

- Add Attio, InboxApp, and Serper to the relevant external provider sections.
- Update any credential examples or environment variable examples if those are documented centrally.
- Keep the documentation aligned with the actual provider names and namespaces used in code.

## Assumptions
- Tickets 1-3 have landed and established the final exported names.
- README remains the primary public provider catalog for the package.

## Acceptance Criteria
- [ ] The README mentions Attio, InboxApp, and Serper in the correct provider categories.
- [ ] Any provider counts or examples remain accurate after the additions.
- [ ] Documentation uses the final code-level family names and tool keys.

## Verification Steps
1. `python -m pytest tests/test_sdk_package.py -v`
2. Manually inspect the updated README provider sections for accuracy.

## Dependencies
- Ticket 1
- Ticket 2
- Ticket 3

## Drift Guard
Do not expand this into tutorials, CLI work, or agent changes. Keep it to accuracy updates for the public SDK surface created by the new provider families.
