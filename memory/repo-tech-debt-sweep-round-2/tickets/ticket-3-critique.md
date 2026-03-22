## Self-Critique

- The first draft of the facade exported a new public `BuiltinFactory` alias even though the original module did not expose that symbol.
- That was unnecessary API expansion for a structure-only refactor and would have widened the compatibility surface instead of preserving it.

## Post-Critique Improvements

- Kept the builtin factory type alias private in `catalog_builtin.py` and removed the new `BuiltinFactory` export from `harnessiq.toolset.catalog`.
- Re-ran the full ticket verification set after tightening the facade surface.
