"""
===============================================================================
File: harnessiq/interfaces/formalization/artifacts.py

What this file does:
- Defines part of the abstract formalization interface surface used to describe
  harness behavior declaratively.
- Compatibility re-exports for artifact-formalization runtime types.

Use cases:
- Subclass or import these interfaces when building a new formalization layer
  family or behavior.

How to use it:
- Use the abstractions here to declare behavior, rules, and configuration in a
  form the runtime can later inspect or enforce.

Intent:
- Keep formalization contracts explicit and composable so harness rules are
  visible in code and docs.
===============================================================================
"""

from harnessiq.formalization.artifacts import (
    ArtifactNotFoundError,
    CompletionRequirement,
    FORMAT_EXTENSION_MAP,
    FORMAT_TOOL_MAP,
    InjectionPolicy,
    InputArtifactLayer,
    InputArtifactSpec,
    OnOversize,
    OutputArtifactMissingError,
    OutputArtifactLayer,
    OutputArtifactSpec,
    SupportedInputFormat,
    SupportedOutputFormat,
    resolve_artifact_path,
    resolve_output_path,
    resolve_write_tool_key,
    validate_input_artifact_specs,
    validate_output_artifact_specs,
)

__all__ = [
    "ArtifactNotFoundError",
    "CompletionRequirement",
    "FORMAT_EXTENSION_MAP",
    "FORMAT_TOOL_MAP",
    "InjectionPolicy",
    "InputArtifactLayer",
    "InputArtifactSpec",
    "OnOversize",
    "OutputArtifactMissingError",
    "OutputArtifactLayer",
    "OutputArtifactSpec",
    "SupportedInputFormat",
    "SupportedOutputFormat",
    "resolve_artifact_path",
    "resolve_output_path",
    "resolve_write_tool_key",
    "validate_input_artifact_specs",
    "validate_output_artifact_specs",
]
