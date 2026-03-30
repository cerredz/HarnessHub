Post-implementation critique:

- The first version of the investigation focused on session reuse, but live CLI logging showed that reuse was already correct. The real bug was browser fingerprinting in headless mode. Keeping the provider-layer change generic while scoping the actual hardening policy to Instagram is the simpler and more defensible fix.
- The Playwright helper change stays additive: it now accepts `context_options`, but existing callers do not need to change and retain their current behavior.
- The Instagram hardening defaults are intentionally modest. They fix the concrete `HeadlessChrome`/locale/timezone/header gap without turning the shared provider layer into a broad stealth browser abstraction.
- The live CLI probe should remain in `memory/` only. It is useful for this ticket’s verification, but it is not product code.

Applied refinements after critique:

- Kept the new browser-context configuration in the generic session helper instead of hardcoding Instagram-only logic in the provider layer.
- Centralized all Instagram-specific browser hardening constants in `harnessiq/shared/instagram.py` so future tuning stays in one place.
- Verified the fix with the actual CLI path and a deterministic two-search probe rather than relying only on unit tests.
