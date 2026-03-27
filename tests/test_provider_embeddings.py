from __future__ import annotations

from unittest.mock import patch

import pytest

from harnessiq.providers import create_provider_embedding_client
from harnessiq.providers.openai import OpenAIClient


def test_create_provider_embedding_client_constructs_openai_client() -> None:
    with patch.dict(
        "os.environ",
        {
            "OPENAI_API_KEY": "test-key",
            "OPENAI_ORGANIZATION": "test-org",
            "OPENAI_PROJECT": "test-project",
        },
        clear=False,
    ):
        client = create_provider_embedding_client("openai", timeout_seconds=12.5)

    assert isinstance(client, OpenAIClient)
    assert client.api_key == "test-key"
    assert client.organization == "test-org"
    assert client.project == "test-project"
    assert client.timeout_seconds == 12.5


def test_create_provider_embedding_client_rejects_unsupported_providers() -> None:
    with pytest.raises(ValueError, match="support only 'openai'"):
        create_provider_embedding_client("grok")
