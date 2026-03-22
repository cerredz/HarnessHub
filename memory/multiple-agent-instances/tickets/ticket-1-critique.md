Self-critique findings:
- The first implementation normalized explicit filesystem paths too aggressively with `Path.resolve()`, which changed the lexical form of caller-provided paths on Windows and regressed an existing Knowt assertion.
- I adjusted the registry to preserve explicit path strings instead of canonicalizing them eagerly, while still keeping repo-relative default paths deterministic.
- I kept the persisted record schema compact: payload snapshot, stable id/name, timestamps, and memory path. I deliberately did not add speculative fields such as agent class import paths because they were not required for retrieval and would have increased coupling.
