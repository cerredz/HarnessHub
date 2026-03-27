# Explicit DTOs at Layer Boundaries Tickets

1. Ticket 1: Establish shared DTO package and typed agent instance boundaries
   Issue: #326 - https://github.com/cerredz/HarnessHub/issues/326
   PR: #340 - https://github.com/cerredz/HarnessHub/pull/340
   Foundational shared DTO package plus the first common agent-instance persistence boundary.

2. Ticket 2: Convert reusable provider-backed agent classes to DTO-first public contracts
   Issue: #327 - https://github.com/cerredz/HarnessHub/issues/327
   PR: #346 - https://github.com/cerredz/HarnessHub/pull/346
   Moves the reusable provider-backed agent families onto explicit DTO boundaries.

3. Ticket 3: Convert concrete durable-memory agents to explicit DTO contracts
   Issue: #328 - https://github.com/cerredz/HarnessHub/issues/328
   Replaces raw payload helpers and public agent boundaries across the bespoke harness agents.

4. Ticket 4: Convert platform CLI and profile storage surfaces to DTO-based contracts
   Issue: #329 - https://github.com/cerredz/HarnessHub/issues/329
   Introduces DTOs for the CLI adapter/context/result and persisted run-profile transport layers.

5. Ticket 5: Introduce explicit DTOs for request-style service provider tool and client layers
   Issue: #330 - https://github.com/cerredz/HarnessHub/issues/330
   PR: #383 - https://github.com/cerredz/HarnessHub/pull/383
   Converts the prepared-request style service provider families to shared provider DTO envelopes.

6. Ticket 6: Convert legacy service provider families to explicit DTO request and result contracts
   Issue: #331 - https://github.com/cerredz/HarnessHub/issues/331
   PR: #386 - https://github.com/cerredz/HarnessHub/pull/386
   Applies the provider DTO pattern to the older reflective client families.

7. Ticket 7: Convert model-provider SDK surfaces to DTO-first request contracts and export them publicly
   Issue: #332 - https://github.com/cerredz/HarnessHub/issues/332
   Finishes the rollout by making model-provider SDK APIs and exports DTO-first.

Phase 3 complete
