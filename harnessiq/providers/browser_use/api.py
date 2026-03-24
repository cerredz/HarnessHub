"""Browser Use Cloud endpoint and authentication helpers."""

from __future__ import annotations

from typing import Mapping

from harnessiq.providers.base import omit_none_values
from harnessiq.providers.http import join_url
from harnessiq.shared.providers import BROWSER_USE_DEFAULT_BASE_URL as DEFAULT_BASE_URL


def build_headers(api_key: str, *, extra_headers: Mapping[str, str] | None = None) -> dict[str, str]:
    """Build the headers required for Browser Use Cloud API requests."""

    headers = omit_none_values({"X-Browser-Use-API-Key": api_key})
    if extra_headers:
        headers.update(extra_headers)
    return headers


def tasks_url(base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, "/tasks")


def task_url(task_id: str, base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, f"/tasks/{task_id}")


def task_status_url(task_id: str, base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, f"/tasks/{task_id}/status")


def task_logs_url(task_id: str, base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, f"/tasks/{task_id}/logs")


def task_output_file_url(task_id: str, file_id: str, base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, f"/files/tasks/{task_id}/output-files/{file_id}")


def sessions_url(base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, "/sessions")


def session_url(session_id: str, base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, f"/sessions/{session_id}")


def session_share_url(session_id: str, base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, f"/sessions/{session_id}/public-share")


def session_purge_url(session_id: str, base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, f"/sessions/{session_id}/purge")


def profiles_url(base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, "/profiles")


def profile_url(profile_id: str, base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, f"/profiles/{profile_id}")


def browsers_url(base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, "/browsers")


def browser_url(session_id: str, base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, f"/browsers/{session_id}")


def session_upload_url(session_id: str, base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, f"/files/sessions/{session_id}/presigned-url")


def browser_upload_url(session_id: str, base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, f"/files/browsers/{session_id}/presigned-url")


def skills_url(base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, "/skills")


def skill_url(skill_id: str, base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, f"/skills/{skill_id}")


def skill_cancel_url(skill_id: str, base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, f"/skills/{skill_id}/cancel")


def skill_execute_url(skill_id: str, base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, f"/skills/{skill_id}/execute")


def skill_refine_url(skill_id: str, base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, f"/skills/{skill_id}/refine")


def skill_rollback_url(skill_id: str, base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, f"/skills/{skill_id}/rollback")


def skill_executions_url(skill_id: str, base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, f"/skills/{skill_id}/executions")


def skill_execution_output_url(skill_id: str, execution_id: str, base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, f"/skills/{skill_id}/executions/{execution_id}/output")


def marketplace_skills_url(base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, "/marketplace/skills")


def marketplace_skill_url(slug: str, base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, f"/marketplace/skills/{slug}")


def marketplace_skill_clone_url(skill_id: str, base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, f"/marketplace/skills/{skill_id}/clone")


def marketplace_skill_execute_url(skill_id: str, base_url: str = DEFAULT_BASE_URL) -> str:
    return join_url(base_url, f"/marketplace/skills/{skill_id}/execute")


__all__ = [
    "DEFAULT_BASE_URL",
    "browser_upload_url",
    "browser_url",
    "browsers_url",
    "build_headers",
    "marketplace_skill_clone_url",
    "marketplace_skill_execute_url",
    "marketplace_skill_url",
    "marketplace_skills_url",
    "profile_url",
    "profiles_url",
    "session_purge_url",
    "session_share_url",
    "session_upload_url",
    "session_url",
    "sessions_url",
    "skill_cancel_url",
    "skill_execute_url",
    "skill_execution_output_url",
    "skill_executions_url",
    "skill_refine_url",
    "skill_rollback_url",
    "skill_url",
    "skills_url",
    "task_logs_url",
    "task_output_file_url",
    "task_status_url",
    "task_url",
    "tasks_url",
]
