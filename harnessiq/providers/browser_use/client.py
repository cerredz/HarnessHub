"""Thin Browser Use Cloud API client wrapper."""

from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Mapping
from urllib import parse

from harnessiq.providers.http import RequestExecutor, request_json
from harnessiq.shared.http import ProviderHTTPError
from harnessiq.shared.dtos import ProviderPayloadRequestDTO, ProviderPayloadResultDTO

from .api import (
    DEFAULT_BASE_URL,
    browser_upload_url,
    browser_url,
    browsers_url,
    build_headers,
    marketplace_skill_clone_url,
    marketplace_skill_execute_url,
    marketplace_skill_url,
    marketplace_skills_url,
    profile_url,
    profiles_url,
    session_purge_url,
    session_share_url,
    session_upload_url,
    session_url,
    sessions_url,
    skill_cancel_url,
    skill_execute_url,
    skill_execution_output_url,
    skill_executions_url,
    skill_refine_url,
    skill_rollback_url,
    skill_url,
    skills_url,
    task_logs_url,
    task_output_file_url,
    task_status_url,
    task_url,
    tasks_url,
)
from .requests import (
    build_create_browser_request,
    build_create_profile_request,
    build_create_session_request,
    build_create_skill_request,
    build_create_task_request,
    build_execute_skill_request,
    build_refine_skill_request,
    build_update_browser_request,
    build_update_profile_request,
    build_update_session_request,
    build_update_skill_request,
    build_update_task_request,
    build_upload_url_request,
)

_retryable_status_codes = frozenset({429})
_retry_backoff_seconds = 0.5


@dataclass(frozen=True, slots=True)
class BrowserUseClient:
    """Minimal Browser Use Cloud API client."""

    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 60.0
    max_retries: int = 3
    request_executor: RequestExecutor = request_json

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise ValueError("Browser Use api_key must not be blank.")
        if not self.base_url.strip():
            raise ValueError("Browser Use base_url must not be blank.")
        if self.timeout_seconds <= 0:
            raise ValueError("Browser Use timeout_seconds must be greater than zero.")
        if self.max_retries < 0:
            raise ValueError("Browser Use max_retries must be zero or greater.")

    def create_task(self, task: str, **payload: Any) -> Any:
        return self._request("POST", tasks_url(self.base_url), json_body=build_create_task_request(task, **payload))

    def list_tasks(
        self,
        *,
        page_size: int | None = None,
        page_number: int | None = None,
        session_id: str | None = None,
        filter_by: str | None = None,
        after: str | None = None,
        before: str | None = None,
    ) -> Any:
        return self._request(
            "GET",
            tasks_url(self.base_url),
            query={
                "pageSize": page_size,
                "pageNumber": page_number,
                "sessionId": session_id,
                "filterBy": filter_by,
                "after": after,
                "before": before,
            },
        )

    def get_task(self, task_id: str) -> Any:
        return self._request("GET", task_url(task_id, self.base_url))

    def get_task_status(self, task_id: str) -> Any:
        return self._request("GET", task_status_url(task_id, self.base_url))

    def stop_task(self, task_id: str, **extra: Any) -> Any:
        return self._request("PATCH", task_url(task_id, self.base_url), json_body=build_update_task_request("stop", **extra))

    def stop_task_and_session(self, task_id: str, **extra: Any) -> Any:
        return self._request("PATCH", task_url(task_id, self.base_url), json_body=build_update_task_request("stop_task_and_session", **extra))

    def get_task_logs(self, task_id: str) -> Any:
        return self._request("GET", task_logs_url(task_id, self.base_url))

    def get_task_output_file(self, task_id: str, file_id: str) -> Any:
        return self._request("GET", task_output_file_url(task_id, file_id, self.base_url))

    def create_session(self, **payload: Any) -> Any:
        return self._request("POST", sessions_url(self.base_url), json_body=build_create_session_request(**payload))

    def list_sessions(self, *, page_size: int | None = None, page_number: int | None = None, filter_by: str | None = None) -> Any:
        return self._request(
            "GET",
            sessions_url(self.base_url),
            query={"pageSize": page_size, "pageNumber": page_number, "filterBy": filter_by},
        )

    def get_session(self, session_id: str) -> Any:
        return self._request("GET", session_url(session_id, self.base_url))

    def stop_session(self, session_id: str, **extra: Any) -> Any:
        return self._request("PATCH", session_url(session_id, self.base_url), json_body=build_update_session_request("stop", **extra))

    def delete_session(self, session_id: str) -> Any:
        return self._request("DELETE", session_url(session_id, self.base_url))

    def get_session_share(self, session_id: str) -> Any:
        return self._request("GET", session_share_url(session_id, self.base_url))

    def create_session_share(self, session_id: str) -> Any:
        return self._request("POST", session_share_url(session_id, self.base_url))

    def delete_session_share(self, session_id: str) -> Any:
        return self._request("DELETE", session_share_url(session_id, self.base_url))

    def purge_session(self, session_id: str) -> Any:
        return self._request("POST", session_purge_url(session_id, self.base_url))

    def create_profile(self, **payload: Any) -> Any:
        return self._request("POST", profiles_url(self.base_url), json_body=build_create_profile_request(**payload))

    def list_profiles(self, *, page_size: int | None = None, page_number: int | None = None, query: str | None = None) -> Any:
        return self._request(
            "GET",
            profiles_url(self.base_url),
            query={"pageSize": page_size, "pageNumber": page_number, "query": query},
        )

    def get_profile(self, profile_id: str) -> Any:
        return self._request("GET", profile_url(profile_id, self.base_url))

    def update_profile(self, profile_id: str, **payload: Any) -> Any:
        return self._request("PATCH", profile_url(profile_id, self.base_url), json_body=build_update_profile_request(**payload))

    def delete_profile(self, profile_id: str) -> Any:
        return self._request("DELETE", profile_url(profile_id, self.base_url))

    def create_browser(self, **payload: Any) -> Any:
        return self._request("POST", browsers_url(self.base_url), json_body=build_create_browser_request(**payload))

    def list_browsers(self, *, page_size: int | None = None, page_number: int | None = None, filter_by: str | None = None) -> Any:
        return self._request(
            "GET",
            browsers_url(self.base_url),
            query={"pageSize": page_size, "pageNumber": page_number, "filterBy": filter_by},
        )

    def get_browser(self, session_id: str) -> Any:
        return self._request("GET", browser_url(session_id, self.base_url))

    def stop_browser(self, session_id: str, **extra: Any) -> Any:
        return self._request("PATCH", browser_url(session_id, self.base_url), json_body=build_update_browser_request("stop", **extra))

    def create_session_upload_url(self, session_id: str, *, file_name: str, content_type: str, size_bytes: int, **extra: Any) -> Any:
        return self._request(
            "POST",
            session_upload_url(session_id, self.base_url),
            json_body=build_upload_url_request(file_name=file_name, content_type=content_type, size_bytes=size_bytes, **extra),
        )

    def create_browser_upload_url(self, session_id: str, *, file_name: str, content_type: str, size_bytes: int, **extra: Any) -> Any:
        return self._request(
            "POST",
            browser_upload_url(session_id, self.base_url),
            json_body=build_upload_url_request(file_name=file_name, content_type=content_type, size_bytes=size_bytes, **extra),
        )

    def create_skill(self, *, goal: str, agent_prompt: str, title: str | None = None, description: str | None = None, **extra: Any) -> Any:
        return self._request(
            "POST",
            skills_url(self.base_url),
            json_body=build_create_skill_request(goal=goal, agent_prompt=agent_prompt, title=title, description=description, **extra),
        )

    def list_skills(
        self,
        *,
        page_size: int | None = None,
        page_number: int | None = None,
        is_public: bool | None = None,
        is_enabled: bool | None = None,
        category: str | None = None,
        query: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> Any:
        return self._request(
            "GET",
            skills_url(self.base_url),
            query={
                "pageSize": page_size,
                "pageNumber": page_number,
                "isPublic": is_public,
                "isEnabled": is_enabled,
                "category": category,
                "query": query,
                "fromDate": from_date,
                "toDate": to_date,
            },
        )

    def get_skill(self, skill_id: str) -> Any:
        return self._request("GET", skill_url(skill_id, self.base_url))

    def update_skill(self, skill_id: str, **payload: Any) -> Any:
        return self._request("PATCH", skill_url(skill_id, self.base_url), json_body=build_update_skill_request(**payload))

    def delete_skill(self, skill_id: str) -> Any:
        return self._request("DELETE", skill_url(skill_id, self.base_url))

    def cancel_skill(self, skill_id: str) -> Any:
        return self._request("POST", skill_cancel_url(skill_id, self.base_url))

    def execute_skill(self, skill_id: str, *, parameters: Mapping[str, Any] | None = None, session_id: str | None = None, **extra: Any) -> Any:
        return self._request(
            "POST",
            skill_execute_url(skill_id, self.base_url),
            json_body=build_execute_skill_request(parameters=parameters, session_id=session_id, **extra),
        )

    def refine_skill(self, skill_id: str, *, feedback: str, test_output: str | None = None, test_logs: str | None = None, **extra: Any) -> Any:
        return self._request(
            "POST",
            skill_refine_url(skill_id, self.base_url),
            json_body=build_refine_skill_request(feedback=feedback, test_output=test_output, test_logs=test_logs, **extra),
        )

    def rollback_skill(self, skill_id: str) -> Any:
        return self._request("POST", skill_rollback_url(skill_id, self.base_url))

    def list_skill_executions(self, skill_id: str, *, page_size: int | None = None, page_number: int | None = None) -> Any:
        return self._request(
            "GET",
            skill_executions_url(skill_id, self.base_url),
            query={"pageSize": page_size, "pageNumber": page_number},
        )

    def get_skill_execution_output(self, skill_id: str, execution_id: str) -> Any:
        return self._request("GET", skill_execution_output_url(skill_id, execution_id, self.base_url))

    def list_marketplace_skills(
        self,
        *,
        page_size: int | None = None,
        page_number: int | None = None,
        category: str | None = None,
        query: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> Any:
        return self._request(
            "GET",
            marketplace_skills_url(self.base_url),
            query={
                "pageSize": page_size,
                "pageNumber": page_number,
                "category": category,
                "query": query,
                "fromDate": from_date,
                "toDate": to_date,
            },
        )

    def get_marketplace_skill(self, slug: str) -> Any:
        return self._request("GET", marketplace_skill_url(slug, self.base_url))

    def clone_marketplace_skill(self, skill_id: str) -> Any:
        return self._request("POST", marketplace_skill_clone_url(skill_id, self.base_url))

    def execute_marketplace_skill(self, skill_id: str, *, parameters: Mapping[str, Any] | None = None, session_id: str | None = None, **extra: Any) -> Any:
        return self._request(
            "POST",
            marketplace_skill_execute_url(skill_id, self.base_url),
            json_body=build_execute_skill_request(parameters=parameters, session_id=session_id, **extra),
        )

    def execute_operation(self, request: ProviderPayloadRequestDTO) -> ProviderPayloadResultDTO:
        """Execute one Browser Use operation from a DTO envelope."""
        handler = getattr(self, request.operation, None)
        if handler is None or not callable(handler):
            raise ValueError(f"Unsupported Browser Use operation '{request.operation}'.")
        result = handler(**request.payload)
        return ProviderPayloadResultDTO(operation=request.operation, result=result)

    def _request(
        self,
        method: str,
        url: str,
        *,
        json_body: Mapping[str, Any] | None = None,
        query: Mapping[str, Any] | None = None,
    ) -> Any:
        headers = build_headers(self.api_key)
        resolved_url = _append_query(url, query)
        attempts_remaining = self.max_retries
        while True:
            try:
                return self.request_executor(
                    method,
                    resolved_url,
                    headers=headers,
                    json_body=dict(json_body) if json_body is not None else None,
                    timeout_seconds=self.timeout_seconds,
                )
            except ProviderHTTPError as exc:
                if exc.status_code not in _retryable_status_codes or attempts_remaining <= 0:
                    raise
                time.sleep(_retry_delay_seconds(self.max_retries - attempts_remaining))
                attempts_remaining -= 1


def _append_query(url: str, query: Mapping[str, Any] | None) -> str:
    if not query:
        return url
    filtered: dict[str, str] = {}
    for key, value in query.items():
        if value is None:
            continue
        if isinstance(value, bool):
            filtered[str(key)] = "true" if value else "false"
        else:
            filtered[str(key)] = str(value)
    if not filtered:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{parse.urlencode(filtered)}"


def _retry_delay_seconds(attempt_number: int) -> float:
    return min(_retry_backoff_seconds * (2 ** max(0, attempt_number)), 10.0)


__all__ = ["BrowserUseClient"]
