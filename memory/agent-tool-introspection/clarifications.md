No blocking clarifications were required after Phase 1.

Implementation assumptions carried forward:

- The new helper will live on `BaseAgent` and therefore be inherited by all concrete agents.
- The helper will expose a structured, serialization-safe tool inspection payload that includes descriptions, parameter schemas, required arguments, and handler identity.
- Existing `available_tools()` behavior will remain unchanged for backward compatibility.
