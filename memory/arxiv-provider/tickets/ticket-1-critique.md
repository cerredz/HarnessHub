## Self-Critique — Ticket 1

### Issues found and fixed

**1. `_fetch_xml` called twice in `search_raw`**
`search_raw` and `search` both call `_fetch_xml` which applies the delay. No duplication — both call their own URL variant. `search_raw` returns the string directly; `search` parses it. Clean.

**2. `download_paper` bypasses delay**
Originally missed: `download_paper` applies `time.sleep` before `urllib.request.urlopen` directly. Confirmed the delay IS applied in `download_paper`. The rate-limit sleep happens before every network call. Correct.

**3. Non-string response guard in `_fetch_xml`**
The guard `if not isinstance(result, str)` correctly handles the case where a test executor accidentally returns a dict instead of XML text. Covered by `test_non_string_executor_response_raises`. Good.

**4. `parse_arxiv_entry` exposes as public API**
`parse_arxiv_entry` is exposed in `__init__.py`? No — it's NOT re-exported from `__init__.py`. It's importable directly from `api.py` for tests. The `__init__.py` exports only the top-level user-facing names. This is correct. Tests import from `harnessiq.providers.arxiv.api` directly.

**5. Atom namespace prefix in `<feed>` root**
`ET.fromstring` on a namespaced root like `<feed xmlns="...">` correctly handles namespace expansion. The `_ENTRY = f"{{{_ATOM_NS}}}entry"` Clark notation is the right approach. Verified with the sample XML fixture.

**6. `_extract_arxiv_id` exposed in module for testing**
`_extract_arxiv_id` is a private helper (underscore prefix) but imported directly in tests. Acceptable — it's complex enough to warrant direct unit testing. Not re-exported from `__init__.py`. This is standard Python convention for "private but testable".

**7. Error message clarity in `ArxivConfig` validation**
All three validation error messages include the field name (`ArxivConfig.base_url`, `ArxivConfig.timeout_seconds`, `ArxivConfig.delay_seconds`). Clean.

**No improvements needed.** Code is clean, tested, and follows codebase conventions throughout.
