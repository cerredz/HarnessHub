No blocking ambiguities remained after Phase 1.

Implementation will proceed on these resolved assumptions:
- `harnessiq prospecting init-browser` should open a usable Google Maps page rather than a blank tab.
- The fix belongs in the Google Maps Playwright session startup path so both CLI bootstrap and runtime session creation stay consistent.
- Regression coverage should be added around session startup behavior and any CLI-visible bootstrap contract that changes.
