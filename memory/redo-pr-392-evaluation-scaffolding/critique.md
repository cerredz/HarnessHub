Post-implementation critique focused on keeping the surface minimal:

- The first pass considered auto-loading the pytest plugin through a package entry point. That would have worked, but it added more hidden behavior than the review called for.
- The final version keeps plugin loading explicit through `tests/conftest.py`, which is easier to reason about and matches the request for minimal pytest boilerplate.
- The helper surface stays intentionally small: generic run introspection, efficiency scoring, and a judge helper. The category/case abstraction layer was removed completely instead of being partially renamed.
