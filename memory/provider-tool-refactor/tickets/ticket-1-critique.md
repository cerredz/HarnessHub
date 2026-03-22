## Self-Critique — Ticket 1 (issue-63)

**Finding 1: Config merge artifacts fixed as side effect** — The `harnessiq/config/__init__.py`, `loader.py`, and `models.py` all had merge artifacts from multiple PRs being applied without conflict resolution. These were blocking imports of `ProviderCredentialConfig`. Fixed as a prerequisite. This was not in the ticket scope but was unavoidable.

**Finding 2: Re-export pattern is correct** — Using `from x import Y as Y` is the right pattern for explicit re-exports. It satisfies both mypy and the intent of making the original location the canonical one.

**Finding 3: `provider: str` field on base class** — The `ProviderCredentialConfig` base TypedDict has an optional `provider: str` field. None of the 8 TypedDicts include this field, and no code reads it. This is harmless since `total=False` makes it optional. Left in place to avoid breaking any downstream consumer that relies on it.

**No regressions found.** The change is purely additive (new shared file + thin re-export shims). Existing imports continue to work transparently.
