## Self-Critique

- The initial refactor introduced a model-client union alias without marking it as internal, which made an implementation detail look more public than intended.
- I renamed the alias to `_ProviderModelClient` so the type surface communicates that only the constructor parameter uses it internally; the public contract remains the exported protocols in `harnessiq.interfaces.models`.
- This keeps the runtime seam explicit without accidentally creating a new public integration type that the rest of the codebase might start depending on.
