## Self-Critique Findings

1. `models import` originally allowed duplicate profile names inside the import file and would have let later entries silently overwrite earlier ones.
- Improvement made: import files now fail fast on duplicate profile names, and the behavior is covered by a focused test.
