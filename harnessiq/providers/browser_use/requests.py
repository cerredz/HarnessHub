"""Browser Use Cloud request payload builders."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from harnessiq.providers.base import omit_none_values


def build_create_task_request(
    task: str,
    *,
    session_id: str | None = None,
    llm: str | None = None,
    start_url: str | None = None,
    max_steps: int | None = None,
    structured_output: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    secrets: Mapping[str, Any] | None = None,
    allowed_domains: list[str] | None = None,
    highlight_elements: bool | None = None,
    flash_mode: bool | None = None,
    thinking: bool | None = None,
    vision: bool | str | None = None,
    system_prompt_extension: str | None = None,
    judge: bool | None = None,
    judge_ground_truth: str | None = None,
    judge_llm: str | None = None,
    skill_ids: list[str] | None = None,
    op_vault_id: str | None = None,
    session_settings: Mapping[str, Any] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    payload = omit_none_values(
        {
            "task": task,
            "sessionId": session_id,
            "llm": llm,
            "startUrl": start_url,
            "maxSteps": max_steps,
            "structuredOutput": structured_output,
            "metadata": _copy_mapping(metadata),
            "secrets": _copy_mapping(secrets),
            "allowedDomains": deepcopy(allowed_domains) if allowed_domains is not None else None,
            "highlightElements": highlight_elements,
            "flashMode": flash_mode,
            "thinking": thinking,
            "vision": vision,
            "systemPromptExtension": system_prompt_extension,
            "judge": judge,
            "judgeGroundTruth": judge_ground_truth,
            "judgeLlm": judge_llm,
            "skillIds": deepcopy(skill_ids) if skill_ids is not None else None,
            "opVaultId": op_vault_id,
            "sessionSettings": _copy_mapping(session_settings),
        }
    )
    payload.update(_copy_mapping(extra) or {})
    return payload


def build_update_task_request(action: str, **extra: Any) -> dict[str, Any]:
    payload = {"action": action}
    payload.update(_copy_mapping(extra) or {})
    return payload


def build_create_session_request(
    *,
    profile_id: str | None = None,
    proxy_country_code: str | None = None,
    start_url: str | None = None,
    browser_screen_width: int | None = None,
    browser_screen_height: int | None = None,
    persist_memory: bool | None = None,
    keep_alive: bool | None = None,
    custom_proxy: Mapping[str, Any] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    payload = omit_none_values(
        {
            "profileId": profile_id,
            "proxyCountryCode": proxy_country_code,
            "startUrl": start_url,
            "browserScreenWidth": browser_screen_width,
            "browserScreenHeight": browser_screen_height,
            "persistMemory": persist_memory,
            "keepAlive": keep_alive,
            "customProxy": _copy_mapping(custom_proxy),
        }
    )
    payload.update(_copy_mapping(extra) or {})
    return payload


def build_update_session_request(action: str, **extra: Any) -> dict[str, Any]:
    payload = {"action": action}
    payload.update(_copy_mapping(extra) or {})
    return payload


def build_create_profile_request(*, name: str | None = None, user_id: str | None = None, **extra: Any) -> dict[str, Any]:
    payload = omit_none_values({"name": name, "userId": user_id})
    payload.update(_copy_mapping(extra) or {})
    return payload


def build_update_profile_request(*, name: str | None = None, user_id: str | None = None, **extra: Any) -> dict[str, Any]:
    return build_create_profile_request(name=name, user_id=user_id, **extra)


def build_create_browser_request(
    *,
    profile_id: str | None = None,
    proxy_country_code: str | None = None,
    timeout: int | None = None,
    browser_screen_width: int | None = None,
    browser_screen_height: int | None = None,
    allow_resizing: bool | None = None,
    custom_proxy: Mapping[str, Any] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    payload = omit_none_values(
        {
            "profileId": profile_id,
            "proxyCountryCode": proxy_country_code,
            "timeout": timeout,
            "browserScreenWidth": browser_screen_width,
            "browserScreenHeight": browser_screen_height,
            "allowResizing": allow_resizing,
            "customProxy": _copy_mapping(custom_proxy),
        }
    )
    payload.update(_copy_mapping(extra) or {})
    return payload


def build_update_browser_request(action: str, **extra: Any) -> dict[str, Any]:
    payload = {"action": action}
    payload.update(_copy_mapping(extra) or {})
    return payload


def build_upload_url_request(*, file_name: str, content_type: str, size_bytes: int, **extra: Any) -> dict[str, Any]:
    payload = {"fileName": file_name, "contentType": content_type, "sizeBytes": size_bytes}
    payload.update(_copy_mapping(extra) or {})
    return payload


def build_create_skill_request(
    *,
    goal: str,
    agent_prompt: str,
    title: str | None = None,
    description: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    payload = omit_none_values(
        {
            "goal": goal,
            "agentPrompt": agent_prompt,
            "title": title,
            "description": description,
        }
    )
    payload.update(_copy_mapping(extra) or {})
    return payload


def build_update_skill_request(
    *,
    title: str | None = None,
    description: str | None = None,
    categories: list[str] | None = None,
    domains: list[str] | None = None,
    is_enabled: bool | None = None,
    **extra: Any,
) -> dict[str, Any]:
    payload = omit_none_values(
        {
            "title": title,
            "description": description,
            "categories": deepcopy(categories) if categories is not None else None,
            "domains": deepcopy(domains) if domains is not None else None,
            "isEnabled": is_enabled,
        }
    )
    payload.update(_copy_mapping(extra) or {})
    return payload


def build_execute_skill_request(
    *,
    parameters: Mapping[str, Any] | None = None,
    session_id: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    payload = omit_none_values({"parameters": _copy_mapping(parameters), "sessionId": session_id})
    payload.update(_copy_mapping(extra) or {})
    return payload


def build_refine_skill_request(
    *,
    feedback: str,
    test_output: str | None = None,
    test_logs: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    payload = omit_none_values({"feedback": feedback, "testOutput": test_output, "testLogs": test_logs})
    payload.update(_copy_mapping(extra) or {})
    return payload


def _copy_mapping(value: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return deepcopy(dict(value))


__all__ = [
    "build_create_browser_request",
    "build_create_profile_request",
    "build_create_session_request",
    "build_create_skill_request",
    "build_create_task_request",
    "build_execute_skill_request",
    "build_refine_skill_request",
    "build_update_browser_request",
    "build_update_profile_request",
    "build_update_session_request",
    "build_update_skill_request",
    "build_update_task_request",
    "build_upload_url_request",
]
