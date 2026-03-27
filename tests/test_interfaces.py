"""Tests for the public interface-contract package."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import unittest

from harnessiq import interfaces
from harnessiq.interfaces import (
    AnthropicModelClient,
    FactoryLoader,
    GoogleSheetsSinkClient,
    OpenAIStyleModelClient,
    PreparedRequest,
    PreparedStoreLoader,
    RequestExecutor,
    RequestPreparingClient,
    TimeoutConfig,
    WebhookSinkClient,
    ZeroArgumentFactory,
)


@dataclass
class _FakeTimeoutConfig:
    timeout_seconds: float = 12.5


@dataclass
class _FakePreparedRequest:
    method: str = "POST"
    path: str = "/v1/things"
    url: str = "https://example.test/v1/things"
    headers: dict[str, str] = None  # type: ignore[assignment]
    json_body: dict[str, object] | None = None

    def __post_init__(self) -> None:
        if self.headers is None:
            self.headers = {"Authorization": "Bearer test"}
        if self.json_body is None:
            self.json_body = {"ok": True}


class _FakeRequestPreparingClient:
    def __init__(self) -> None:
        self.credentials = _FakeTimeoutConfig()
        self.request_executor = _fake_request_executor

    def prepare_request(
        self,
        operation_name: str,
        *,
        path_params=None,
        query=None,
        payload=None,
    ) -> _FakePreparedRequest:
        del operation_name, path_params, query, payload
        return _FakePreparedRequest()


class _FakeWebhookClient:
    def post_json(self, *, url: str, payload, headers=None, timeout_seconds: float = 30.0):
        return {"url": url, "payload": dict(payload), "headers": headers, "timeout_seconds": timeout_seconds}


class _FakeGoogleSheetsClient:
    def get_values(self, *, spreadsheet_id: str, range_name: str) -> list[list[object]]:
        return [[spreadsheet_id, range_name]]

    def update_values(self, *, spreadsheet_id: str, range_name: str, values, value_input_option: str = "RAW"):
        return {"spreadsheet_id": spreadsheet_id, "range_name": range_name, "values": values, "value_input_option": value_input_option}

    def append_values(
        self,
        *,
        spreadsheet_id: str,
        range_name: str,
        values,
        value_input_option: str = "RAW",
        insert_data_option: str = "INSERT_ROWS",
    ):
        return {
            "spreadsheet_id": spreadsheet_id,
            "range_name": range_name,
            "values": values,
            "value_input_option": value_input_option,
            "insert_data_option": insert_data_option,
        }


class _FakeFactoryLoader:
    def __call__(self, spec: str):
        def factory():
            return {"spec": spec}

        return factory


class _FakeOpenAIStyleClient:
    def create_chat_completion(
        self,
        *,
        model_name: str,
        system_prompt: str,
        messages,
        tools=None,
        max_tokens=None,
        temperature=None,
        parallel_tool_calls=None,
        reasoning_effort=None,
    ):
        return {
            "model_name": model_name,
            "system_prompt": system_prompt,
            "messages": messages,
            "tools": tools,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "parallel_tool_calls": parallel_tool_calls,
            "reasoning_effort": reasoning_effort,
        }


class _FakeAnthropicClient:
    def create_message(
        self,
        *,
        model_name: str,
        messages,
        max_tokens: int,
        system_prompt: str | None = None,
        tools=None,
        tool_choice=None,
        temperature=None,
    ):
        return {
            "model_name": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "system_prompt": system_prompt,
            "tools": tools,
            "tool_choice": tool_choice,
            "temperature": temperature,
        }


def _fake_request_executor(
    method: str,
    url: str,
    *,
    headers=None,
    json_body=None,
    timeout_seconds: float = 60.0,
):
    return {
        "method": method,
        "url": url,
        "headers": headers,
        "json_body": json_body,
        "timeout_seconds": timeout_seconds,
    }


class InterfacesPackageTests(unittest.TestCase):
    def test_top_level_harnessiq_exports_interfaces_module(self) -> None:
        self.assertIs(interfaces, __import__("harnessiq.interfaces", fromlist=["interfaces"]))

    def test_package_exports_expected_contracts(self) -> None:
        exported = set(interfaces.__all__)
        self.assertIn("RequestPreparingClient", exported)
        self.assertIn("WebhookSinkClient", exported)
        self.assertIn("PreparedStoreLoader", exported)
        self.assertIn("OpenAIStyleModelClient", exported)

    def test_interfaces_package_contains_flat_contract_files(self) -> None:
        package_dir = Path(interfaces.__file__).resolve().parent
        self.assertTrue((package_dir / "provider_clients.py").exists())
        self.assertTrue((package_dir / "output_sinks.py").exists())
        self.assertTrue((package_dir / "cli.py").exists())
        self.assertTrue((package_dir / "models.py").exists())


class ProviderContractTests(unittest.TestCase):
    def test_timeout_config_protocol_matches_fake(self) -> None:
        self.assertIsInstance(_FakeTimeoutConfig(), TimeoutConfig)

    def test_request_executor_protocol_matches_fake(self) -> None:
        self.assertIsInstance(_fake_request_executor, RequestExecutor)

    def test_prepared_request_protocol_matches_fake(self) -> None:
        self.assertIsInstance(_FakePreparedRequest(), PreparedRequest)

    def test_request_preparing_client_protocol_matches_fake(self) -> None:
        self.assertIsInstance(_FakeRequestPreparingClient(), RequestPreparingClient)


class OutputSinkContractTests(unittest.TestCase):
    def test_webhook_sink_client_protocol_matches_fake(self) -> None:
        self.assertIsInstance(_FakeWebhookClient(), WebhookSinkClient)

    def test_google_sheets_sink_client_protocol_matches_fake(self) -> None:
        self.assertIsInstance(_FakeGoogleSheetsClient(), GoogleSheetsSinkClient)


class CliContractTests(unittest.TestCase):
    def test_prepared_store_loader_protocol_matches_callable(self) -> None:
        loader: PreparedStoreLoader[dict[str, Path]] = lambda memory_path: {"memory_path": memory_path}
        expected = Path("memory/example")
        self.assertIsInstance(loader, PreparedStoreLoader)
        self.assertEqual(loader(expected)["memory_path"], expected)

    def test_factory_loader_and_zero_argument_factory_protocols_match_fake(self) -> None:
        loader = _FakeFactoryLoader()
        self.assertIsInstance(loader, FactoryLoader)
        factory = loader("module:factory")
        self.assertIsInstance(factory, ZeroArgumentFactory)
        self.assertEqual(factory()["spec"], "module:factory")


class ModelContractTests(unittest.TestCase):
    def test_openai_style_model_client_protocol_matches_fake(self) -> None:
        self.assertIsInstance(_FakeOpenAIStyleClient(), OpenAIStyleModelClient)

    def test_anthropic_model_client_protocol_matches_fake(self) -> None:
        self.assertIsInstance(_FakeAnthropicClient(), AnthropicModelClient)


if __name__ == "__main__":
    unittest.main()
