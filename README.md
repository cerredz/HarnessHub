# Harnessiq

Harnessiq is a Python SDK for shipping tool-using agents and reusable injectable tools.

## Install

```bash
pip install harnessiq
```

For local development from this repository:

```bash
pip install -e .
```

## Quick Start

```python
from harnessiq.tools import ECHO_TEXT, create_builtin_registry

registry = create_builtin_registry()
result = registry.execute(ECHO_TEXT, {"text": "hello"})

print(result.output)
```

First-class agent exports live under `harnessiq.agents`, including `LinkedInJobApplierAgent` and `BaseEmailAgent`.

CLI entrypoint:

```bash
harnessiq --help
harnessiq linkedin --help
```

LinkedIn CLI example:

```bash
harnessiq linkedin configure \
  --agent candidate-a \
  --job-preferences-text "Staff platform roles in New York" \
  --user-profile-file ./profile.md \
  --runtime-param max_tokens=4000 \
  --custom-param target_team=platform \
  --additional-prompt-text "Prioritize remote-friendly companies" \
  --import-file ./resume.pdf
```

Additional examples:

- `docs/tools.md`
- `docs/agent-runtime.md`
- `docs/linkedin-agent.md`
