"""LangSmith tracing helpers for custom agent run functions."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from functools import wraps
from typing import Any, ParamSpec, TypeVar, overload

from harnessiq.providers.base import normalize_messages
from harnessiq.shared.providers import ProviderMessage, ProviderName, RequestPayload
from harnessiq.shared.tools import ToolArguments, ToolDefinition

P = ParamSpec("P")
R = TypeVar("R")
_SCALAR_TYPES = (str, int, float, bool, type(None))


def _get_langsmith_module() -> Any:
    """Import LangSmith lazily so tests can replace the integration boundary."""
    try:
        import langsmith as ls
    except ImportError as exc:  # pragma: no cover - exercised only in missing dependency setups
        message = "langsmith is required for tracing helpers. Install dependencies from requirements.txt."
        raise RuntimeError(message) from exc
    return ls


def _serialize_trace_value(value: Any) -> Any:
    """Convert values into a JSON-safe structure for trace inputs and outputs."""
    if isinstance(value, ToolDefinition):
        return value.as_dict()
    if isinstance(value, _SCALAR_TYPES):
        return value
    if isinstance(value, Mapping):
        return {str(key): _serialize_trace_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_serialize_trace_value(item) for item in value]

    as_dict = getattr(value, "as_dict", None)
    if callable(as_dict):
        return _serialize_trace_value(as_dict())

    return repr(value)


def _serialize_messages(messages: Sequence[ProviderMessage]) -> list[ProviderMessage]:
    """Copy message payloads into the canonical trace shape."""
    return normalize_messages(list(messages))


def _serialize_tools(tools: Sequence[ToolDefinition]) -> list[dict[str, Any]]:
    """Copy canonical tool definitions into trace-safe payloads."""
    return [tool.as_dict() for tool in tools]


def _copy_tags(tags: Sequence[str] | None) -> list[str] | None:
    return list(tags) if tags else None


def _copy_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if metadata is None:
        return None
    copied = _serialize_trace_value(dict(metadata))
    return copied if isinstance(copied, dict) else {"metadata": copied}


def _serialize_call_arguments(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "args": _serialize_trace_value(list(args)),
        "kwargs": _serialize_trace_value(kwargs),
    }


def _serialize_model_inputs(
    *,
    provider: ProviderName,
    model_name: str,
    system_prompt: str,
    messages: Sequence[ProviderMessage],
    tools: Sequence[ToolDefinition],
    request_payload: RequestPayload | None,
) -> dict[str, Any]:
    inputs: dict[str, Any] = {
        "provider": provider,
        "model_name": model_name,
        "system_prompt": system_prompt,
        "messages": _serialize_messages(messages),
        "tools": _serialize_tools(tools),
    }
    if request_payload is not None:
        inputs["request_payload"] = _serialize_trace_value(request_payload)
    return inputs


def _serialize_tool_inputs(
    *,
    tool_name: str,
    arguments: ToolArguments,
    tool_key: str | None,
) -> dict[str, Any]:
    inputs = {
        "tool_name": tool_name,
        "arguments": _serialize_trace_value(arguments),
    }
    if tool_key is not None:
        inputs["tool_key"] = tool_key
    return inputs


def _trace_sync_operation(
    operation: Callable[[], R],
    *,
    name: str,
    run_type: str,
    inputs: dict[str, Any],
    output_key: str,
    project_name: str | None,
    tags: Sequence[str] | None,
    metadata: Mapping[str, Any] | None,
    client: Any | None,
    enabled: bool | None,
) -> R:
    ls = _get_langsmith_module()
    context_kwargs: dict[str, Any] = {}
    if project_name is not None:
        context_kwargs["project_name"] = project_name
    if client is not None:
        context_kwargs["client"] = client
    if enabled is not None:
        context_kwargs["enabled"] = enabled

    with ls.tracing_context(**context_kwargs):
        with ls.trace(
            name,
            run_type=run_type,
            inputs=inputs,
            tags=_copy_tags(tags),
            metadata=_copy_metadata(metadata),
        ) as run_tree:
            try:
                result = operation()
            except Exception as exc:
                run_tree.end(error=str(exc))
                raise
            run_tree.end(outputs={output_key: _serialize_trace_value(result)})
            return result


async def _trace_async_operation(
    operation: Callable[[], Awaitable[R]],
    *,
    name: str,
    run_type: str,
    inputs: dict[str, Any],
    output_key: str,
    project_name: str | None,
    tags: Sequence[str] | None,
    metadata: Mapping[str, Any] | None,
    client: Any | None,
    enabled: bool | None,
) -> R:
    ls = _get_langsmith_module()
    context_kwargs: dict[str, Any] = {}
    if project_name is not None:
        context_kwargs["project_name"] = project_name
    if client is not None:
        context_kwargs["client"] = client
    if enabled is not None:
        context_kwargs["enabled"] = enabled

    with ls.tracing_context(**context_kwargs):
        async with ls.trace(
            name,
            run_type=run_type,
            inputs=inputs,
            tags=_copy_tags(tags),
            metadata=_copy_metadata(metadata),
        ) as run_tree:
            try:
                result = await operation()
            except Exception as exc:
                run_tree.end(error=str(exc))
                raise
            run_tree.end(outputs={output_key: _serialize_trace_value(result)})
            return result


@overload
def trace_agent_run(
    run_function: Callable[P, R],
    *,
    name: str | None = None,
    project_name: str | None = None,
    tags: Sequence[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
    client: Any | None = None,
    enabled: bool | None = None,
) -> Callable[P, R]:
    ...


@overload
def trace_agent_run(
    run_function: None = None,
    *,
    name: str | None = None,
    project_name: str | None = None,
    tags: Sequence[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
    client: Any | None = None,
    enabled: bool | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    ...


def trace_agent_run(
    run_function: Callable[P, R] | None = None,
    *,
    name: str | None = None,
    project_name: str | None = None,
    tags: Sequence[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
    client: Any | None = None,
    enabled: bool | None = None,
) -> Callable[P, R] | Callable[[Callable[P, R]], Callable[P, R]]:
    """Wrap a synchronous custom agent run function in a LangSmith root trace."""

    def decorator(target: Callable[P, R]) -> Callable[P, R]:
        trace_name = name or target.__name__

        @wraps(target)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            return _trace_sync_operation(
                lambda: target(*args, **kwargs),
                name=trace_name,
                run_type="chain",
                inputs=_serialize_call_arguments(args, kwargs),
                output_key="output",
                project_name=project_name,
                tags=tags,
                metadata=metadata,
                client=client,
                enabled=enabled,
            )

        return wrapped

    if run_function is None:
        return decorator
    return decorator(run_function)


@overload
def trace_async_agent_run(
    run_function: Callable[P, Awaitable[R]],
    *,
    name: str | None = None,
    project_name: str | None = None,
    tags: Sequence[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
    client: Any | None = None,
    enabled: bool | None = None,
) -> Callable[P, Awaitable[R]]:
    ...


@overload
def trace_async_agent_run(
    run_function: None = None,
    *,
    name: str | None = None,
    project_name: str | None = None,
    tags: Sequence[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
    client: Any | None = None,
    enabled: bool | None = None,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    ...


def trace_async_agent_run(
    run_function: Callable[P, Awaitable[R]] | None = None,
    *,
    name: str | None = None,
    project_name: str | None = None,
    tags: Sequence[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
    client: Any | None = None,
    enabled: bool | None = None,
) -> Callable[P, Awaitable[R]] | Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Wrap an asynchronous custom agent run function in a LangSmith root trace."""

    def decorator(target: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        trace_name = name or target.__name__

        @wraps(target)
        async def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            return await _trace_async_operation(
                lambda: target(*args, **kwargs),
                name=trace_name,
                run_type="chain",
                inputs=_serialize_call_arguments(args, kwargs),
                output_key="output",
                project_name=project_name,
                tags=tags,
                metadata=metadata,
                client=client,
                enabled=enabled,
            )

        return wrapped

    if run_function is None:
        return decorator
    return decorator(run_function)


def trace_model_call(
    operation: Callable[[], R],
    *,
    provider: ProviderName,
    model_name: str,
    system_prompt: str,
    messages: Sequence[ProviderMessage],
    tools: Sequence[ToolDefinition] = (),
    request_payload: RequestPayload | None = None,
    name: str | None = None,
    project_name: str | None = None,
    tags: Sequence[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
    client: Any | None = None,
    enabled: bool | None = None,
) -> R:
    """Execute a synchronous model call inside a LangSmith `llm` span."""
    trace_name = name or f"{provider}.model_call"
    return _trace_sync_operation(
        operation,
        name=trace_name,
        run_type="llm",
        inputs=_serialize_model_inputs(
            provider=provider,
            model_name=model_name,
            system_prompt=system_prompt,
            messages=messages,
            tools=tools,
            request_payload=request_payload,
        ),
        output_key="response",
        project_name=project_name,
        tags=tags,
        metadata=metadata,
        client=client,
        enabled=enabled,
    )


async def trace_async_model_call(
    operation: Callable[[], Awaitable[R]],
    *,
    provider: ProviderName,
    model_name: str,
    system_prompt: str,
    messages: Sequence[ProviderMessage],
    tools: Sequence[ToolDefinition] = (),
    request_payload: RequestPayload | None = None,
    name: str | None = None,
    project_name: str | None = None,
    tags: Sequence[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
    client: Any | None = None,
    enabled: bool | None = None,
) -> R:
    """Execute an asynchronous model call inside a LangSmith `llm` span."""
    trace_name = name or f"{provider}.model_call"
    return await _trace_async_operation(
        operation,
        name=trace_name,
        run_type="llm",
        inputs=_serialize_model_inputs(
            provider=provider,
            model_name=model_name,
            system_prompt=system_prompt,
            messages=messages,
            tools=tools,
            request_payload=request_payload,
        ),
        output_key="response",
        project_name=project_name,
        tags=tags,
        metadata=metadata,
        client=client,
        enabled=enabled,
    )


def trace_tool_call(
    operation: Callable[[], R],
    *,
    tool_name: str,
    arguments: ToolArguments,
    tool_key: str | None = None,
    name: str | None = None,
    project_name: str | None = None,
    tags: Sequence[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
    client: Any | None = None,
    enabled: bool | None = None,
) -> R:
    """Execute a synchronous tool call inside a LangSmith `tool` span."""
    trace_name = name or tool_name
    return _trace_sync_operation(
        operation,
        name=trace_name,
        run_type="tool",
        inputs=_serialize_tool_inputs(tool_name=tool_name, arguments=arguments, tool_key=tool_key),
        output_key="result",
        project_name=project_name,
        tags=tags,
        metadata=metadata,
        client=client,
        enabled=enabled,
    )


async def trace_async_tool_call(
    operation: Callable[[], Awaitable[R]],
    *,
    tool_name: str,
    arguments: ToolArguments,
    tool_key: str | None = None,
    name: str | None = None,
    project_name: str | None = None,
    tags: Sequence[str] | None = None,
    metadata: Mapping[str, Any] | None = None,
    client: Any | None = None,
    enabled: bool | None = None,
) -> R:
    """Execute an asynchronous tool call inside a LangSmith `tool` span."""
    trace_name = name or tool_name
    return await _trace_async_operation(
        operation,
        name=trace_name,
        run_type="tool",
        inputs=_serialize_tool_inputs(tool_name=tool_name, arguments=arguments, tool_key=tool_key),
        output_key="result",
        project_name=project_name,
        tags=tags,
        metadata=metadata,
        client=client,
        enabled=enabled,
    )


__all__ = [
    "trace_agent_run",
    "trace_async_agent_run",
    "trace_model_call",
    "trace_async_model_call",
    "trace_tool_call",
    "trace_async_tool_call",
]
