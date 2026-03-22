No blocking clarifications were required after Phase 1.

Implementation assumptions carried forward:
- Instance identity will be derived from a normalized, JSON-serializable payload assembled from agent parameters/configuration.
- The SDK will persist agent-instance records under the repo `memory/` tree so retrieval works without external services.
- Re-running the same logical agent with the same normalized payload will resolve the same instance; a different payload will create a new one automatically.
- Existing explicit memory-path workflows will remain compatible by registering those paths as the instance memory location instead of breaking current callers.
