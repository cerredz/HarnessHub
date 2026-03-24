No clarification round required.

The request is implementable without a user round-trip if the Instagram agent:
- keeps `Recent Searches` as the only run-progress signal in context,
- drops Instagram search tool calls/results from the rolling transcript,
- tracks failed attempted keywords in agent state for the current run so it does not retry them after transcript compaction, and
- updates the prompt to stop relying on tool-result feedback.
