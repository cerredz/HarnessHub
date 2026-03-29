"""Shared constants, configs, and reusable data-model definitions for Harnessiq."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTED_MODULES = frozenset({"dtos"})
_ATTRIBUTE_EXPORTS = {
    "AppError": ("harnessiq.shared.exceptions", "AppError"),
    "ConfigurationError": ("harnessiq.shared.exceptions", "ConfigurationError"),
    "ExternalServiceError": ("harnessiq.shared.exceptions", "ExternalServiceError"),
    "NotFoundError": ("harnessiq.shared.exceptions", "NotFoundError"),
    "ResourceNotFoundError": ("harnessiq.shared.exceptions", "ResourceNotFoundError"),
    "StateError": ("harnessiq.shared.exceptions", "StateError"),
    "ValidationError": ("harnessiq.shared.exceptions", "ValidationError"),
    "HarnessManifest": ("harnessiq.shared.harness_manifest", "HarnessManifest"),
    "HarnessMemoryEntryFormat": ("harnessiq.shared.harness_manifest", "HarnessMemoryEntryFormat"),
    "HarnessMemoryEntryKind": ("harnessiq.shared.harness_manifest", "HarnessMemoryEntryKind"),
    "HarnessMemoryFileSpec": ("harnessiq.shared.harness_manifest", "HarnessMemoryFileSpec"),
    "HarnessParameterSpec": ("harnessiq.shared.harness_manifest", "HarnessParameterSpec"),
    "HarnessParameterType": ("harnessiq.shared.harness_manifest", "HarnessParameterType"),
    "EMAIL_HARNESS_MANIFEST": ("harnessiq.shared.harness_manifests", "EMAIL_HARNESS_MANIFEST"),
    "EXA_OUTREACH_HARNESS_MANIFEST": ("harnessiq.shared.harness_manifests", "EXA_OUTREACH_HARNESS_MANIFEST"),
    "HARNESS_MANIFESTS": ("harnessiq.shared.harness_manifests", "HARNESS_MANIFESTS"),
    "HARNESS_MANIFESTS_BY_AGENT_NAME": ("harnessiq.shared.harness_manifests", "HARNESS_MANIFESTS_BY_AGENT_NAME"),
    "HARNESS_MANIFESTS_BY_CLI_COMMAND": ("harnessiq.shared.harness_manifests", "HARNESS_MANIFESTS_BY_CLI_COMMAND"),
    "INSTAGRAM_HARNESS_MANIFEST": ("harnessiq.shared.harness_manifests", "INSTAGRAM_HARNESS_MANIFEST"),
    "KNOWT_HARNESS_MANIFEST": ("harnessiq.shared.harness_manifests", "KNOWT_HARNESS_MANIFEST"),
    "LEADS_HARNESS_MANIFEST": ("harnessiq.shared.harness_manifests", "LEADS_HARNESS_MANIFEST"),
    "LINKEDIN_HARNESS_MANIFEST": ("harnessiq.shared.harness_manifests", "LINKEDIN_HARNESS_MANIFEST"),
    "MISSION_DRIVEN_HARNESS_MANIFEST": ("harnessiq.shared.harness_manifests", "MISSION_DRIVEN_HARNESS_MANIFEST"),
    "PROSPECTING_HARNESS_MANIFEST": ("harnessiq.shared.harness_manifests", "PROSPECTING_HARNESS_MANIFEST"),
    "RESEARCH_SWEEP_HARNESS_MANIFEST": ("harnessiq.shared.harness_manifests", "RESEARCH_SWEEP_HARNESS_MANIFEST"),
    "SPAWN_SPECIALIZED_SUBAGENTS_HARNESS_MANIFEST": ("harnessiq.shared.harness_manifests", "SPAWN_SPECIALIZED_SUBAGENTS_HARNESS_MANIFEST"),
    "get_harness_manifest": ("harnessiq.shared.harness_manifests", "get_harness_manifest"),
    "list_harness_manifests": ("harnessiq.shared.harness_manifests", "list_harness_manifests"),
    "register_harness_manifest": ("harnessiq.shared.harness_manifests", "register_harness_manifest"),
    "register_harness_manifests": ("harnessiq.shared.harness_manifests", "register_harness_manifests"),
    "ArtifactSpec": ("harnessiq.shared.formalization", "ArtifactSpec"),
    "BudgetSpec": ("harnessiq.shared.formalization", "BudgetSpec"),
    "FieldSpec": ("harnessiq.shared.formalization", "FieldSpec"),
    "FormalizationDescription": ("harnessiq.shared.formalization", "FormalizationDescription"),
    "FormalizationEnforcementType": ("harnessiq.shared.formalization", "FormalizationEnforcementType"),
    "FormalizationHookName": ("harnessiq.shared.formalization", "FormalizationHookName"),
    "HookBehaviorSpec": ("harnessiq.shared.formalization", "HookBehaviorSpec"),
    "LayerRuleRecord": ("harnessiq.shared.formalization", "LayerRuleRecord"),
    "RoleSpec": ("harnessiq.shared.formalization", "RoleSpec"),
    "StageSpec": ("harnessiq.shared.formalization", "StageSpec"),
    "StateFieldSpec": ("harnessiq.shared.formalization", "StateFieldSpec"),
    "StateUpdateRule": ("harnessiq.shared.formalization", "StateUpdateRule"),
    "EnvVarName": ("harnessiq.shared.validated", "EnvVarName"),
    "HttpUrl": ("harnessiq.shared.validated", "HttpUrl"),
    "NonEmptyString": ("harnessiq.shared.validated", "NonEmptyString"),
    "NonNegativeInt": ("harnessiq.shared.validated", "NonNegativeInt"),
    "PositiveInt": ("harnessiq.shared.validated", "PositiveInt"),
    "ProviderFamilyName": ("harnessiq.shared.validated", "ProviderFamilyName"),
    "ToolDescription": ("harnessiq.shared.validated", "ToolDescription"),
    "parse_bounded_int": ("harnessiq.shared.validated", "parse_bounded_int"),
    "parse_positive_number": ("harnessiq.shared.validated", "parse_positive_number"),
    "AnthropicCountTokensRequestDTO": ("harnessiq.shared.dtos", "AnthropicCountTokensRequestDTO"),
    "AnthropicMessageDTO": ("harnessiq.shared.dtos", "AnthropicMessageDTO"),
    "AnthropicMessageRequestDTO": ("harnessiq.shared.dtos", "AnthropicMessageRequestDTO"),
    "GeminiCacheCreateRequestDTO": ("harnessiq.shared.dtos", "GeminiCacheCreateRequestDTO"),
    "GeminiContentDTO": ("harnessiq.shared.dtos", "GeminiContentDTO"),
    "GeminiCountTokensRequestDTO": ("harnessiq.shared.dtos", "GeminiCountTokensRequestDTO"),
    "GeminiGenerateContentRequestDTO": ("harnessiq.shared.dtos", "GeminiGenerateContentRequestDTO"),
    "GeminiGenerationConfigDTO": ("harnessiq.shared.dtos", "GeminiGenerationConfigDTO"),
    "GeminiSystemInstructionDTO": ("harnessiq.shared.dtos", "GeminiSystemInstructionDTO"),
    "GrokChatCompletionRequestDTO": ("harnessiq.shared.dtos", "GrokChatCompletionRequestDTO"),
    "GrokSearchParametersDTO": ("harnessiq.shared.dtos", "GrokSearchParametersDTO"),
    "OpenAIChatCompletionRequestDTO": ("harnessiq.shared.dtos", "OpenAIChatCompletionRequestDTO"),
    "OpenAIEmbeddingRequestDTO": ("harnessiq.shared.dtos", "OpenAIEmbeddingRequestDTO"),
    "OpenAIResponseInputMessageDTO": ("harnessiq.shared.dtos", "OpenAIResponseInputMessageDTO"),
    "OpenAIResponseRequestDTO": ("harnessiq.shared.dtos", "OpenAIResponseRequestDTO"),
    "ProviderMessageDTO": ("harnessiq.shared.dtos", "ProviderMessageDTO"),
}


def __getattr__(name: str) -> Any:
    if name in _EXPORTED_MODULES:
        module = import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    export = _ATTRIBUTE_EXPORTS.get(name)
    if export is None:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
    module_name, attribute_name = export
    module = import_module(module_name)
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted([*globals(), *_EXPORTED_MODULES, *_ATTRIBUTE_EXPORTS])


__all__ = [
    "AppError",
    "ConfigurationError",
    "dtos",
    "EnvVarName",
    "EMAIL_HARNESS_MANIFEST",
    "EXA_OUTREACH_HARNESS_MANIFEST",
    "ExternalServiceError",
    "HARNESS_MANIFESTS",
    "HARNESS_MANIFESTS_BY_AGENT_NAME",
    "HARNESS_MANIFESTS_BY_CLI_COMMAND",
    "HarnessManifest",
    "HarnessMemoryEntryFormat",
    "HarnessMemoryEntryKind",
    "HarnessMemoryFileSpec",
    "HarnessParameterSpec",
    "HarnessParameterType",
    "HttpUrl",
    "INSTAGRAM_HARNESS_MANIFEST",
    "KNOWT_HARNESS_MANIFEST",
    "LEADS_HARNESS_MANIFEST",
    "LINKEDIN_HARNESS_MANIFEST",
    "AnthropicCountTokensRequestDTO",
    "AnthropicMessageDTO",
    "AnthropicMessageRequestDTO",
    "ArtifactSpec",
    "BudgetSpec",
    "MISSION_DRIVEN_HARNESS_MANIFEST",
    "FieldSpec",
    "FormalizationDescription",
    "FormalizationEnforcementType",
    "FormalizationHookName",
    "NonEmptyString",
    "NonNegativeInt",
    "NotFoundError",
    "GeminiCacheCreateRequestDTO",
    "GeminiContentDTO",
    "GeminiCountTokensRequestDTO",
    "GeminiGenerateContentRequestDTO",
    "GeminiGenerationConfigDTO",
    "GeminiSystemInstructionDTO",
    "GrokChatCompletionRequestDTO",
    "GrokSearchParametersDTO",
    "OpenAIChatCompletionRequestDTO",
    "OpenAIEmbeddingRequestDTO",
    "OpenAIResponseInputMessageDTO",
    "OpenAIResponseRequestDTO",
    "PositiveInt",
    "PROSPECTING_HARNESS_MANIFEST",
    "ProviderMessageDTO",
    "ProviderFamilyName",
    "RESEARCH_SWEEP_HARNESS_MANIFEST",
    "HookBehaviorSpec",
    "LayerRuleRecord",
    "SPAWN_SPECIALIZED_SUBAGENTS_HARNESS_MANIFEST",
    "ResourceNotFoundError",
    "RoleSpec",
    "StageSpec",
    "StateError",
    "StateFieldSpec",
    "StateUpdateRule",
    "ToolDescription",
    "ValidationError",
    "get_harness_manifest",
    "list_harness_manifests",
    "parse_bounded_int",
    "parse_positive_number",
    "register_harness_manifest",
    "register_harness_manifests",
]
