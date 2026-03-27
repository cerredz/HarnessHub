## Self-Critique

Initial review found one meaningful coverage gap:

- The first pass added protocol-compatible fake-client tests for Apollo, Exa, and Email, but Instantly and Outreach had also been refactored to contract-typed constructor dependencies and deserved equivalent coverage.

## Post-Critique Changes

- Added protocol-compatible fake-client injection tests to `tests/test_instantly_agent.py` and `tests/test_outreach_agent.py`.
- Re-ran the shared interface/provider-base tests, the full touched agent test slice, the Resend tool tests, and the Apollo-based smoke script after the coverage expansion; all remained green.
