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

Additional examples:

- `docs/tools.md`
- `docs/agent-runtime.md`
- `docs/linkedin-agent.md`
