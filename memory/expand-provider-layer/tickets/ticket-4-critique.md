## Self-Critique

- The initial Gemini URL builders assumed callers would always pass bare model IDs like `gemini-2.5-flash`.
- In practice, Gemini and Google examples often use full resource names like `models/gemini-2.5-flash`; without normalization the client would have produced malformed URLs with a duplicated `models/` segment.

## Implemented Improvements

- Normalized Gemini model names inside the URL builders so both bare IDs and `models/...` resource names work.
- Expanded the Gemini client test to assert the normalized URL shape explicitly.
