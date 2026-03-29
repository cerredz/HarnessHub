"""Tests for the public interface-contract package."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import unittest

from harnessiq import interfaces
from harnessiq.interfaces import (
    AnthropicModelClient,
    BaseContractLayer,
    BaseStageLayer,
    BaseStateLayer,
    BudgetSpec,
    DynamicToolSelector,
    EmbeddingBackend,
    EmbeddingModelClient,
    FactoryLoader,
    FieldSpec,
    GeminiModelClient,
    GoogleSheetsSinkClient,
    IterableFactoryLoader,
    LayerRuleRecord,
    OpenAIStyleModelClient,
    PreparedRequest,
    PreparedStoreLoader,
    RequestExecutor,
    RequestPreparingClient,
    StageSpec,
    StateFieldSpec,
    TimeoutConfig,
    WebhookSinkClient,
    ZeroArgumentFactory,
)
from harnessiq.shared import (
    ArtifactSpec,
    FormalizationDescription,
    StateUpdateRule,
)
from harnessiq.shared.tool_selection import ToolSelectionConfig, ToolSelectionResult
from harnessiq.shared.dtos import PreparedProviderOperationResultDTO, ProviderOperationRequestDTO
from harnessiq.shared.tool_selection import ToolSelectionConfig, ToolSelectionResult


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
        request: ProviderOperationRequestDTO,
    ) -> _FakePreparedRequest:
        del request
        return _FakePreparedRequest()

    def execute_operation(
        self,
        request: ProviderOperationRequestDTO,
    ) -> PreparedProviderOperationResultDTO:
        prepared = self.prepare_request(request)
        return PreparedProviderOperationResultDTO.from_prepared_request(
            prepared=prepared,
            response={"ok": True},
        )


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


class _FakeIterableFactoryLoader:
    def __call__(self, spec: str):
        def factory():
            return [{"spec": spec}]

        return factory


class _FakeOpenAIStyleClient:
    def create_chat_completion(
        self,
        request: OpenAIChatCompletionRequestDTO,
    ):
        return {
            "model_name": request.model_name,
            "system_prompt": request.system_prompt,
            "messages": [message.to_dict() for message in request.messages],
            "tools": request.tools,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "parallel_tool_calls": request.parallel_tool_calls,
        }


class _FakeAnthropicClient:
    def create_message(
        self,
        request: AnthropicMessageRequestDTO,
    ):
        return {
            "model_name": request.model_name,
            "messages": [message.to_dict() for message in request.messages],
            "max_tokens": request.max_tokens,
            "system_prompt": request.system_prompt,
            "tools": request.tools,
            "tool_choice": request.tool_choice,
            "temperature": request.temperature,
        }


class _FakeGeminiClient:
    def generate_content(self, request: GeminiGenerateContentRequestDTO):
        return {
            "model_name": request.model_name,
            "contents": [content.to_dict() for content in request.contents],
            "system_instruction": request.system_instruction.to_dict() if request.system_instruction else None,
        }


class _FakeEmbeddingClient:
    def create_embedding(
        self,
        *,
        model_name: str,
        input_value,
        dimensions: int | None = None,
        encoding_format: str | None = None,
        user: str | None = None,
    ):
        return {
            "model_name": model_name,
            "input_value": input_value,
            "dimensions": dimensions,
            "encoding_format": encoding_format,
            "user": user,
        }


class _FakeEmbeddingBackend:
    def embed_texts(self, texts):
        return tuple((float(index),) for index, _ in enumerate(texts))


class _FakeDynamicToolSelector:
    @property
    def config(self) -> ToolSelectionConfig:
        return ToolSelectionConfig(enabled=True, top_k=2)

    def index(self, profiles) -> None:
        self._profiles = tuple(profiles)

    def select(self, *, context_window, candidate_profiles, metadata=None) -> ToolSelectionResult:
        del context_window, metadata
        selected = tuple(profile.key for profile in candidate_profiles[:2])
        return ToolSelectionResult(selected_keys=selected, retrieval_query="demo")


class _FakeContractLayer(BaseContractLayer):
    def get_input_spec(self):
        return (
            FieldSpec(
                name="mission_goal",
                field_type="string",
                description="The user-provided objective for the harness.",
                required=True,
            ),
        )

    def get_output_spec(self):
        return (
            FieldSpec(
                name="final_report",
                field_type="markdown",
                description="The final structured deliverable.",
                required=True,
            ),
        )

    def get_budget_spec(self):
        return BudgetSpec(max_tokens=120000, max_resets=6, max_wall_seconds=900.0)


class _FakeStageLayer(BaseStageLayer):
    def get_stages(self):
        return (
            StageSpec(
                name="discover",
                description="Collect the core facts.",
                system_prompt_fragment="You are in the discovery stage.",
                allowed_tool_patterns=("search.*", "artifact.append_run_log"),
                required_output_keys=("facts",),
                completion_hint="Facts have been collected.",
            ),
            StageSpec(
                name="report",
                description="Write the structured report.",
                system_prompt_fragment="You are in the reporting stage.",
                allowed_tool_patterns=("artifact.*",),
                required_output_keys=("final_report",),
            ),
        )

    def get_current_stage_index(self) -> int:
        return 0


class _FakeStateLayer(BaseStateLayer):
    def get_state_fields(self):
        return (
            StateFieldSpec(
                name="continuation_pointer",
                field_type="string",
                description="The next step to resume from.",
                update_rule="overwrite",
                is_continuation_pointer=True,
            ),
            StateFieldSpec(
                name="mission_goal",
                field_type="string",
                description="Original user objective.",
                update_rule="write_once",
            ),
        )

    def get_state_snapshot(self):
        return {
            "continuation_pointer": "report",
            "mission_goal": "Add formalization layer interfaces",
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
        self.assertIn("DynamicToolSelector", exported)
        self.assertIn("EmbeddingBackend", exported)
        self.assertIn("BaseFormalizationLayer", exported)
        self.assertIn("BaseStageLayer", exported)
        self.assertIn("BaseStateLayer", exported)
        self.assertIn("LayerRuleRecord", exported)

    def test_interfaces_package_contains_formalization_package(self) -> None:
        package_dir = Path(interfaces.__file__).resolve().parent
        self.assertTrue((package_dir / "formalization.py").exists())
        self.assertTrue((package_dir / "provider_clients.py").exists())
        self.assertTrue((package_dir / "output_sinks.py").exists())
        self.assertTrue((package_dir / "cli.py").exists())
        self.assertTrue((package_dir / "models.py").exists())
        self.assertTrue((package_dir / "tool_selection.py").exists())

    def test_top_level_harnessiq_exports_formalization_module(self) -> None:
        from harnessiq import formalization

        self.assertTrue((Path(formalization.__file__).resolve().parent / "base.py").exists())
        self.assertEqual(formalization.BaseFormalizationLayer.__name__, "BaseFormalizationLayer")

    def test_lazy_exports_resolve_and_cache_symbols(self) -> None:
        first = interfaces.RequestPreparingClient
        second = interfaces.RequestPreparingClient

        self.assertIs(first, second)
        self.assertIn("RequestPreparingClient", dir(interfaces))


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

    def test_iterable_factory_loader_protocol_matches_fake(self) -> None:
        loader = _FakeIterableFactoryLoader()
        self.assertIsInstance(loader, IterableFactoryLoader)
        self.assertEqual(loader("module:factory")()[0]["spec"], "module:factory")


class ModelContractTests(unittest.TestCase):
    def test_openai_style_model_client_protocol_matches_fake(self) -> None:
        self.assertIsInstance(_FakeOpenAIStyleClient(), OpenAIStyleModelClient)

    def test_anthropic_model_client_protocol_matches_fake(self) -> None:
        self.assertIsInstance(_FakeAnthropicClient(), AnthropicModelClient)

    def test_embedding_model_client_protocol_matches_fake(self) -> None:
        self.assertIsInstance(_FakeEmbeddingClient(), EmbeddingModelClient)

    def test_embedding_backend_protocol_matches_fake(self) -> None:
        self.assertIsInstance(_FakeEmbeddingBackend(), EmbeddingBackend)

    def test_dynamic_tool_selector_protocol_matches_fake(self) -> None:
        self.assertIsInstance(_FakeDynamicToolSelector(), DynamicToolSelector)


class FormalizationContractTests(unittest.TestCase):
    def test_contract_layer_produces_default_self_documentation(self) -> None:
        layer = _FakeContractLayer()

        description = layer.describe()
        sections = layer.get_parameter_sections()

        self.assertIn("execution contract", description.identity)
        self.assertEqual(description.rules[0], LayerRuleRecord(
            rule_id="CONTRACT-INPUTS",
            description="Required inputs must exist before substantive work begins: mission_goal.",
            enforced_at="on_agent_prepare",
            enforcement_type="raise",
        ))
        self.assertEqual(sections[0].title, "Formalization: _FakeContractLayer")
        self.assertIn("mission_goal", sections[0].content)
        self.assertIn("final_report", sections[0].content)

    def test_stage_layer_filters_visible_tools_and_augments_prompt(self) -> None:
        layer = _FakeStageLayer()

        filtered = layer.filter_tool_keys(
            ("search.web", "artifact.write_markdown", "artifact.append_run_log", "reason.step")
        )
        prompt = layer.augment_system_prompt("Base system prompt")
        sections = layer.get_parameter_sections()

        self.assertEqual(filtered, ("search.web", "artifact.append_run_log"))
        self.assertIn("You are in the discovery stage.", prompt)
        self.assertEqual(sections[1].title, "Current Stage")
        self.assertIn('"stage_name": "discover"', sections[1].content)

    def test_state_layer_injects_state_snapshot_parameter_section(self) -> None:
        layer = _FakeStateLayer()

        sections = layer.get_parameter_sections()
        description = layer.describe()

        self.assertEqual(sections[1].title, "Formalization State")
        self.assertIn('"continuation_pointer": "report"', sections[1].content)
        self.assertIn("Continuation pointer: continuation_pointer.", description.identity)
        self.assertIn("STATE-WRITE-ONCE-MISSION_GOAL", [rule.rule_id for rule in description.rules])


if __name__ == "__main__":
    unittest.main()
