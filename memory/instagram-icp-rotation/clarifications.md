Phase 2 review: no blocking ambiguities remain after Phase 1.

Implementation assumptions carried forward:
- The Instagram harness should rotate through ICPs in the exact configured order.
- Each ICP should have its own durable recent-search history and duplicate-check scope.
- Legacy flat search history should remain readable so existing memory folders do not hard-fail.
