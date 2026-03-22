# SDK Agent Runtime Extensibility Ticket Index

1. Ticket 1: Add first-class custom sink registration to the ledger subsystem
   - Extend sink construction so user-defined sink types can be registered and resolved through the same SDK helpers as built-ins.

2. Ticket 2: Standardize agent tool injection and shared runtime helpers
   - Add public tool-composition and parameter-section helpers, then wire consistent `tools=` injection across concrete agents.

3. Ticket 3: Update SDK docs and verification for the new customization surface
   - Document and test the end-to-end story for custom tools, sinks, and runtime configuration.

Phase 3a complete.
