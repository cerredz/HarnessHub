"""
===============================================================================
File: harnessiq/formalization/artifacts/__init__.py

What this file does:
- Defines the package-level export surface for
  `harnessiq/formalization/artifacts` within the HarnessIQ runtime.
- Artifact-formalization runtime specs, helpers, and exceptions.

Use cases:
- Import ArtifactNotFoundError, CompletionRequirement, FORMAT_EXTENSION_MAP,
  FORMAT_TOOL_MAP, InjectionPolicy, InputArtifactLayer from one stable package
  entry point.
- Read this module to understand what `harnessiq/formalization/artifacts`
  intends to expose publicly.

How to use it:
- Import from `harnessiq/formalization/artifacts` when you want the supported
  facade instead of reaching through deeper internal modules.

Intent:
- Keep the public surface for `harnessiq/formalization/artifacts` explicit,
  discoverable, and easier to maintain.
===============================================================================
"""

from .exceptions import ArtifactNotFoundError, OutputArtifactMissingError
from .format_map import (
    FORMAT_EXTENSION_MAP,
    FORMAT_TOOL_MAP,
    resolve_artifact_path,
    resolve_output_path,
    resolve_write_tool_key,
)
from .input_layer import InputArtifactLayer
from .input_spec import (
    InjectionPolicy,
    InputArtifactSpec,
    OnOversize,
    SupportedInputFormat,
    validate_input_artifact_specs,
)
from .output_layer import OutputArtifactLayer
from .output_spec import (
    CompletionRequirement,
    OutputArtifactSpec,
    SupportedOutputFormat,
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
