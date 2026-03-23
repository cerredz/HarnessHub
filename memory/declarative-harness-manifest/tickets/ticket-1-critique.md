## Ticket 1 Critique

- The manifest layer now centralizes the metadata contract, but it does not yet drive agent instance payload construction directly. That would be a larger follow-up once the team decides how much payload generation should become declarative.
- Output schemas are intentionally coarse JSON-schema-style contracts. Tightening them further would add maintenance burden without changing current runtime behavior.
- The registry is shared-first and additive. That keeps imports clean without forcing a constructor or package-structure redesign.
