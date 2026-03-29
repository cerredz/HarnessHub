"""Public interface contracts for runtime dependency seams."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_SYMBOL_TO_MODULE = {
    "AnthropicModelClient": "models",
    "ArtifactSpec": "formalization",
    "BaseArtifactLayer": "formalization",
    "BaseContractLayer": "formalization",
    "BaseFormalizationLayer": "formalization",
    "BaseHookLayer": "formalization",
    "BaseRoleLayer": "formalization",
    "BaseStageLayer": "formalization",
    "BaseStateLayer": "formalization",
    "BaseToolContributionLayer": "formalization",
    "BudgetSpec": "formalization",
    "ConfluenceSinkClient": "output_sinks",
    "DynamicToolSelector": "tool_selection",
    "EmbeddingBackend": "tool_selection",
    "EmbeddingModelClient": "tool_selection",
    "FactoryLoader": "cli",
    "FieldSpec": "formalization",
    "FormalizationDescription": "formalization",
    "FormalizationEnforcementType": "formalization",
    "FormalizationHookName": "formalization",
    "GeminiModelClient": "models",
    "GoogleSheetsSinkClient": "output_sinks",
    "HookBehaviorSpec": "formalization",
    "IterableFactory": "cli",
    "IterableFactoryLoader": "cli",
    "LayerRuleRecord": "formalization",
    "LinearSinkClient": "output_sinks",
    "MongoClientFactory": "output_sinks",
    "MongoCollectionSinkClient": "output_sinks",
    "NotionSinkClient": "output_sinks",
    "OpenAIStyleModelClient": "models",
    "PreparedRequest": "provider_clients",
    "PreparedStoreLoader": "cli",
    "ProviderClientBuilder": "provider_clients",
    "RequestExecutor": "provider_clients",
    "RequestPreparingClient": "provider_clients",
    "ResendRequestClient": "provider_clients",
    "RoleSpec": "formalization",
    "StageSpec": "formalization",
    "StateFieldSpec": "formalization",
    "SupabaseSinkClient": "output_sinks",
    "TimeoutConfig": "provider_clients",
    "WebhookSinkClient": "output_sinks",
    "ZeroArgumentFactory": "cli",
}

__all__ = sorted(_SYMBOL_TO_MODULE)


def __getattr__(name: str) -> Any:
    module_name = _SYMBOL_TO_MODULE.get(name)
    if module_name is None:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
    module = import_module(f"{__name__}.{module_name}")
    value = getattr(module, name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted([*globals(), *__all__])
