## Post-Critique Review

- Finding: The initial package smoke test asserted that the new provider base classes were exported from `harnessiq.agents`, but it did not explicitly verify the provider config types that the ticket also made public. That left a gap between the documented import surface and the built-wheel regression net.
- Change: Extended the wheel/sdist smoke command in `tests/test_sdk_package.py` to assert the presence of `ApolloAgentConfig`, `ExaAgentConfig`, `InstantlyAgentConfig`, and `OutreachAgentConfig` in addition to the provider base classes.
- Result: The built-package verification now covers the full provider-base public surface introduced by this ticket, while the unrelated baseline failures in `tests.test_sdk_package` and the broader suite remain unchanged.
