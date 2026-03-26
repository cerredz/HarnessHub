"""Custom hook creation helpers for Harnessiq."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from harnessiq.shared.hooks import HookDefinition, HookHandler, HookPhase, RegisteredHook


def define_hook_tool(
    *,
    key: str,
    description: str,
    phases: Sequence[HookPhase],
    handler: HookHandler,
    name: str | None = None,
    priority: int = 100,
) -> RegisteredHook:
    """Create and return a runtime hook object."""
    resolved_name = name if name is not None else _name_from_key(key)
    definition = HookDefinition(
        key=key,
        name=resolved_name,
        description=description,
        phases=tuple(phases),
        priority=priority,
    )
    return RegisteredHook(definition=definition, handler=handler)


def hook_tool(
    *,
    key: str,
    description: str,
    phases: Sequence[HookPhase],
    name: str | None = None,
    priority: int = 100,
) -> Callable[[HookHandler], RegisteredHook]:
    """Decorator that converts a callable into a registered hook."""

    def decorator(handler: HookHandler) -> RegisteredHook:
        return define_hook_tool(
            key=key,
            description=description,
            phases=phases,
            handler=handler,
            name=name,
            priority=priority,
        )

    return decorator


def _name_from_key(key: str) -> str:
    return key.rsplit(".", 1)[-1]


__all__ = ["define_hook_tool", "hook_tool"]
