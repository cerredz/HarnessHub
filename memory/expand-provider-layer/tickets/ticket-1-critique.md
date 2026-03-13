## Self-Critique

- The first implementation pass exposed a wider public OpenAI surface than the tests initially covered. In particular, `OpenAIClient.create_chat_completion()`, `build_response_input_file()`, and the shared transport path for `URLError` were public behaviors without direct assertions.
- I tightened those gaps with targeted tests so the branch now verifies:
- transport-level wrapping for both HTTP and connection failures
- the chat-completions client path in addition to responses/models/embeddings
- the file-input builder for Responses API payloads

## Implemented Improvements

- Added a shared transport test covering `URLError` -> `ProviderHTTPError`.
- Added OpenAI tests covering `build_response_input_file()`.
- Added an OpenAI client test covering `create_chat_completion()`.
