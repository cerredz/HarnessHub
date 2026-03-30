"""Deterministic CLI probe helpers for the Instagram browser-reuse task."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from harnessiq.agents import AgentModelRequest, AgentModelResponse
from harnessiq.integrations.instagram_playwright import create_search_backend
from harnessiq.shared.tools import ToolCall


class _TwoSearchModel:
    """Issue two Instagram searches, then stop."""

    def __init__(self) -> None:
        self._turn_index = 0
        self._log_path = (
            Path(__file__).resolve().parents[1]
            / "fix-instagram-browser-reuse"
            / "cli-probe-model.jsonl"
        )

    def generate_turn(self, request: AgentModelRequest) -> AgentModelResponse:
        self._turn_index += 1
        self._write_event(
            {
                "turn_index": self._turn_index,
                "tool_keys": [tool.key for tool in request.tools],
                "parameter_titles": [section.title for section in request.parameter_sections],
                "transcript": request.render_transcript(),
            }
        )
        if self._turn_index == 1:
            return AgentModelResponse(
                assistant_message="Search the first keyword.",
                tool_calls=(ToolCall(tool_key="instagram.search_keyword", arguments={"keyword": "ai educator"}),),
                should_continue=True,
            )
        if self._turn_index == 2:
            return AgentModelResponse(
                assistant_message="Search the second keyword.",
                tool_calls=(ToolCall(tool_key="instagram.search_keyword", arguments={"keyword": "stem creator"}),),
                should_continue=True,
            )
        return AgentModelResponse(
            assistant_message="Done.",
            should_continue=False,
        )

    def _write_event(self, payload: dict[str, Any]) -> None:
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with self._log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True))
            handle.write("\n")


def create_two_search_model() -> _TwoSearchModel:
    """Return a deterministic model factory for CLI probing."""
    return _TwoSearchModel()


class _LoggingSearchBackend:
    """Wrap the real Instagram Playwright backend and persist debug events."""

    def __init__(self) -> None:
        self._backend = create_search_backend()
        self._log_path = (
            Path(__file__).resolve().parents[1]
            / "fix-instagram-browser-reuse"
            / "cli-probe-log.jsonl"
        )

    def search_keyword(self, *, keyword: str, max_results: int) -> Any:
        self._write_event(
            "before_search",
            {
                "keyword": keyword,
                "max_results": max_results,
                "session_id": id(getattr(self._backend, "_session", None)),
                "page_id": id(getattr(self._backend, "_search_page", None)),
            },
        )
        try:
            result = self._backend.search_keyword(keyword=keyword, max_results=max_results)
        except Exception as exc:
            self._write_event(
                "search_error",
                {
                    "keyword": keyword,
                    "error": str(exc),
                    "session_id": id(getattr(self._backend, "_session", None)),
                    "page_id": id(getattr(self._backend, "_search_page", None)),
                    "page_count": self._page_count(),
                },
            )
            raise
        self._write_event(
            "after_search",
            {
                "keyword": keyword,
                "lead_count": result.search_record.lead_count,
                "email_count": result.search_record.email_count,
                "session_id": id(getattr(self._backend, "_session", None)),
                "page_id": id(getattr(self._backend, "_search_page", None)),
                "page_count": self._page_count(),
            },
        )
        return result

    def close(self) -> None:
        self._write_event(
            "close",
            {
                "session_id": id(getattr(self._backend, "_session", None)),
                "page_id": id(getattr(self._backend, "_search_page", None)),
                "page_count": self._page_count(),
            },
        )
        close = getattr(self._backend, "close", None)
        if callable(close):
            close()

    def _page_count(self) -> int | None:
        session = getattr(self._backend, "_session", None)
        context = getattr(session, "_context", None)
        pages = getattr(context, "pages", None)
        if pages is None:
            return None
        try:
            return len(pages)
        except Exception:
            return None

    def _write_event(self, event: str, payload: dict[str, Any]) -> None:
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "event": event,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with self._log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True))
            handle.write("\n")


def create_logging_search_backend() -> _LoggingSearchBackend:
    """Return the real backend wrapped with file logging for CLI repro."""
    return _LoggingSearchBackend()
