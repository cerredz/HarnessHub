# Ticket Index

1. `ticket-1.md` — Add the Attio provider family and register `attio.request`. Issue #171: https://github.com/cerredz/HarnessHub/issues/171
2. `ticket-2.md` — Add the InboxApp provider family and register `inboxapp.request`. Issue #172: https://github.com/cerredz/HarnessHub/issues/172
3. `ticket-3.md` — Add the Serper provider family and register `serper.request`. Issue #173: https://github.com/cerredz/HarnessHub/issues/173
4. `ticket-4.md` — Update shared documentation for the new provider families after implementation. Issue #174: https://github.com/cerredz/HarnessHub/issues/174

Phase 3a complete.
Phase 3 complete.

## Implementation Status

- Ticket 1: implemented locally, quality documented, PR blocked.
- Ticket 2: implemented locally, quality documented, PR blocked.
- Ticket 3: implemented locally, quality documented, PR blocked.
- Ticket 4: implemented locally, quality documented, PR blocked.

## PR Blocker

- The current repository has unrelated user-side uncommitted changes in shared files that this task also needed to modify, including `README.md`, `harnessiq/shared/tools.py`, and `harnessiq/toolset/catalog.py`.
- Creating granular commits or a PR from this workspace would necessarily bundle unrelated existing diffs, which would violate the requirement to avoid committing user changes that I did not make.
