## Phase 2 Clarifications

The repo mapping is clear, but the product list contains several API-surface ambiguities. These questions determine whether implementation should stay limited to the confirmed public APIs or expand into products whose public API status is unclear.

1. `Trellus` product identity
   Ambiguity: the official API docs found during Phase 1 appear to belong to a logistics/delivery product, not an outbound dialer.
   Why it matters: the wrong product match would produce an entirely incorrect provider implementation.
   Options:
   - Use only the sales-dialer Trellus product you intended
   - Ignore Trellus for this task unless its exact API/docs URL is provided
   - Include the currently surfaced official API anyway

2. Scope for weakly documented products
   Ambiguity: `Bitscale`, `Floqer`, `Kondo`, and `LeadDelta` did not surface clearly indexed public API docs in Phase 1.
   Why it matters: implementing them without reliable official docs would mean guessing on auth, endpoints, and supported operations.
   Options:
   - Only implement providers with clearly confirmed public docs
   - Include products with private/partner APIs if I can infer enough from official marketing/help content
   - Hold those products out entirely unless you provide exact API references

3. `Serper` inclusion threshold
   Ambiguity: Serper clearly offers a public API from the official site, but its endpoint reference is less directly exposed than Attio/Inbox in indexed docs.
   Why it matters: I can implement a conservative Serper provider, but I should confirm you want that even if the operation set is narrower than the richer providers.
   Options:
   - Include Serper with a conservative official-surface operation set
   - Skip Serper unless a fuller official endpoint reference is provided

4. Naming preference for `InboxApp`
   Ambiguity: the product domain is `inboxapp.com`, while the docs brand the surface as `Inbox API`.
   Why it matters: this affects package names, tool keys, and public imports.
   Options:
   - Use `inboxapp` everywhere in code (`inboxapp.request`)
   - Use `inbox` everywhere in code (`inbox.request`)
   - Use `inboxapp` package names with `inbox.request` tool key

## User Responses

1. `Trellus`: skip.
2. Scope: documented public APIs only.
3. `Serper`: yes, include a conservative implementation.
4. `InboxApp`: use `inboxapp`.

## Follow-on Implications

- Confirmed implementation scope:
  - `attio`
  - `inboxapp`
  - `serper`
- Explicitly excluded from this task:
  - `trellus`
  - `bitscale`
  - `floqer`
  - `kondo`
  - `leaddelta`
  - `replit`
- `exa` remains unchanged because it is already implemented.
- No further clarification is required before ticket drafting or implementation.
