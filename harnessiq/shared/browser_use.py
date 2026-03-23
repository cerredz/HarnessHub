"""Browser Use shared operation metadata."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BrowserUseOperation:
    """Metadata for one Browser Use Cloud API operation."""

    name: str
    category: str
    description: str

    def summary(self) -> str:
        return self.name


_CATALOG: OrderedDict[str, BrowserUseOperation] = OrderedDict(
    [
        ("create_task", BrowserUseOperation("create_task", "Task", "Create and start a new Browser Use task.")),
        ("list_tasks", BrowserUseOperation("list_tasks", "Task", "List Browser Use tasks with optional filtering.")),
        ("get_task", BrowserUseOperation("get_task", "Task", "Fetch detailed Browser Use task information.")),
        ("get_task_status", BrowserUseOperation("get_task_status", "Task", "Fetch lightweight task status optimized for polling.")),
        ("stop_task", BrowserUseOperation("stop_task", "Task", "Stop a running Browser Use task.")),
        ("stop_task_and_session", BrowserUseOperation("stop_task_and_session", "Task", "Stop a running task and its associated session.")),
        ("get_task_logs", BrowserUseOperation("get_task_logs", "Task", "Get the download URL for a task log bundle.")),
        ("get_task_output_file", BrowserUseOperation("get_task_output_file", "Task", "Get the download URL for one task output file.")),
        ("create_session", BrowserUseOperation("create_session", "Session", "Create a Browser Use task session.")),
        ("list_sessions", BrowserUseOperation("list_sessions", "Session", "List Browser Use sessions.")),
        ("get_session", BrowserUseOperation("get_session", "Session", "Fetch detailed Browser Use session information.")),
        ("stop_session", BrowserUseOperation("stop_session", "Session", "Stop a Browser Use session and its running tasks.")),
        ("delete_session", BrowserUseOperation("delete_session", "Session", "Delete a Browser Use session.")),
        ("get_session_share", BrowserUseOperation("get_session_share", "Session", "Fetch a Browser Use public session share.")),
        ("create_session_share", BrowserUseOperation("create_session_share", "Session", "Create or return a Browser Use public session share.")),
        ("delete_session_share", BrowserUseOperation("delete_session_share", "Session", "Delete a Browser Use public session share.")),
        ("purge_session", BrowserUseOperation("purge_session", "Session", "Purge Browser Use session data for zero-data-retention projects.")),
        ("create_profile", BrowserUseOperation("create_profile", "Profile", "Create a Browser Use browser profile.")),
        ("list_profiles", BrowserUseOperation("list_profiles", "Profile", "List Browser Use browser profiles.")),
        ("get_profile", BrowserUseOperation("get_profile", "Profile", "Fetch Browser Use browser profile details.")),
        ("update_profile", BrowserUseOperation("update_profile", "Profile", "Update a Browser Use browser profile.")),
        ("delete_profile", BrowserUseOperation("delete_profile", "Profile", "Delete a Browser Use browser profile.")),
        ("create_browser", BrowserUseOperation("create_browser", "Browser", "Create a standalone Browser Use browser session.")),
        ("list_browsers", BrowserUseOperation("list_browsers", "Browser", "List standalone Browser Use browser sessions.")),
        ("get_browser", BrowserUseOperation("get_browser", "Browser", "Fetch standalone Browser Use browser session details.")),
        ("stop_browser", BrowserUseOperation("stop_browser", "Browser", "Stop a standalone Browser Use browser session.")),
        ("create_session_upload_url", BrowserUseOperation("create_session_upload_url", "File", "Create a presigned upload URL for a Browser Use task session file.")),
        ("create_browser_upload_url", BrowserUseOperation("create_browser_upload_url", "File", "Create a presigned upload URL for a standalone Browser Use browser file.")),
        ("create_skill", BrowserUseOperation("create_skill", "Skill", "Create a Browser Use skill.")),
        ("list_skills", BrowserUseOperation("list_skills", "Skill", "List Browser Use skills.")),
        ("get_skill", BrowserUseOperation("get_skill", "Skill", "Fetch Browser Use skill details.")),
        ("update_skill", BrowserUseOperation("update_skill", "Skill", "Update a Browser Use skill.")),
        ("delete_skill", BrowserUseOperation("delete_skill", "Skill", "Delete a Browser Use skill.")),
        ("cancel_skill", BrowserUseOperation("cancel_skill", "Skill", "Cancel Browser Use skill generation.")),
        ("execute_skill", BrowserUseOperation("execute_skill", "Skill", "Execute a Browser Use skill.")),
        ("refine_skill", BrowserUseOperation("refine_skill", "Skill", "Refine a Browser Use skill using feedback and test artifacts.")),
        ("rollback_skill", BrowserUseOperation("rollback_skill", "Skill", "Rollback a Browser Use skill to the previous version.")),
        ("list_skill_executions", BrowserUseOperation("list_skill_executions", "Skill", "List Browser Use skill executions.")),
        ("get_skill_execution_output", BrowserUseOperation("get_skill_execution_output", "Skill", "Fetch the output for one Browser Use skill execution.")),
        ("list_marketplace_skills", BrowserUseOperation("list_marketplace_skills", "Marketplace", "List Browser Use marketplace skills.")),
        ("get_marketplace_skill", BrowserUseOperation("get_marketplace_skill", "Marketplace", "Fetch Browser Use marketplace skill details.")),
        ("clone_marketplace_skill", BrowserUseOperation("clone_marketplace_skill", "Marketplace", "Clone a Browser Use marketplace skill into the current account.")),
        ("execute_marketplace_skill", BrowserUseOperation("execute_marketplace_skill", "Marketplace", "Execute a Browser Use marketplace skill.")),
    ]
)


def build_browser_use_operation_catalog() -> tuple[BrowserUseOperation, ...]:
    """Return all registered Browser Use operations in stable order."""

    return tuple(_CATALOG.values())


def get_browser_use_operation(name: str) -> BrowserUseOperation:
    """Return one Browser Use operation or raise a clear error."""

    try:
        return _CATALOG[name]
    except KeyError:
        known = ", ".join(_CATALOG)
        raise ValueError(f"Unknown Browser Use operation '{name}'. Known: {known}") from None


__all__ = [
    "BrowserUseOperation",
    "build_browser_use_operation_catalog",
    "get_browser_use_operation",
]
