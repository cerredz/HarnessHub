- Ticket 1 (#177): Centralize remaining agent-side shared definitions and provider-adjacent constants
  Issue URL: https://github.com/cerredz/HarnessHub/issues/177
  Complete the agent-side and adjacent runtime-definition cleanup without moving harness-local path wiring.
- Ticket 2 (#178): Centralize provider endpoint constants and provider credential/config definitions under shared
  Issue URL: https://github.com/cerredz/HarnessHub/issues/178
  PR URL: https://github.com/cerredz/HarnessHub/pull/189
  Move provider endpoint defaults and standalone provider config dataclasses into `harnessiq/shared/`.
- Ticket 3 (#179): Centralize provider operation metadata and prepared-request types for provider-backed tool surfaces
  Issue URL: https://github.com/cerredz/HarnessHub/issues/179
  Move provider operation metadata catalogs and immutable request-definition types into provider-specific shared modules.
- Ticket 4 (#180): Normalize package exports, shared-module coverage, and architectural documentation after the shared-definition refactor
  Issue URL: https://github.com/cerredz/HarnessHub/issues/180
  Reconcile exports, docs, and verification after the shared-definition moves.

Dependency order:
1. Ticket 1
2. Ticket 2
3. Ticket 3
4. Ticket 4

Phase 3a complete
Phase 3 complete
