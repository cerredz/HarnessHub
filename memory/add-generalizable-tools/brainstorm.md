# Brainstorm

Chosen tool set and rationale:

1. `text.normalize_whitespace`
   Clean browser text, OCR output, copied documents, and model-generated drafts into a stable form.
2. `text.regex_extract`
   Extract structured signals such as emails, URLs, IDs, dates, or tagged fragments from unstructured text.
3. `text.truncate_text`
   Enforce length budgets before prompting, logging, storing memory, or handing data to smaller models.
4. `records.select_fields`
   Project large records into the small schemas that downstream prompts or APIs actually need.
5. `records.filter_records`
   Keep only items matching simple constraints without requiring the model to hand-roll list filtering repeatedly.
6. `records.sort_records`
   Re-rank results deterministically by a chosen field.
7. `records.limit_records`
   Bound fan-out and keep candidate sets manageable.
8. `records.unique_records`
   Remove duplicate records or duplicate field values while preserving first-seen order.
9. `records.count_by_field`
   Summarize datasets into lightweight frequency views for planning and prioritization.
10. `control.pause_for_human`
   Escalate blockers or approval points to a human in a structured, agent-runtime-compatible way.

Why these 10:

- They cover three broad needs shared by many agents: text cleanup, structured record manipulation, and safe control flow.
- They are deterministic and local, so they fit the repository's current runtime model without introducing network or SDK dependencies.
- They compose well with each other and with existing context-compaction tools.
