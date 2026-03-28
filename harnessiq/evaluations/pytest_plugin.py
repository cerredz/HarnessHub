"""Minimal pytest integration for Harnessiq eval suites."""

from __future__ import annotations

from collections.abc import Iterable

import pytest


def _normalize_categories(values: Iterable[object]) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, str):
            candidates = (value,)
        elif isinstance(value, (list, tuple, set, frozenset)):
            candidates = tuple(item for item in value if isinstance(item, str))
        else:
            continue
        for candidate in candidates:
            category = candidate.strip()
            if not category or category in seen:
                continue
            seen.add(category)
            normalized.append(category)
    return tuple(normalized)


def _item_categories(item: pytest.Item) -> tuple[str, ...]:
    categories: list[str] = []
    for marker in item.iter_markers(name="eval_category"):
        categories.extend(_normalize_categories(marker.args))
    return _normalize_categories(categories)


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("harnessiq evaluations")
    group.addoption(
        "--eval-category",
        action="append",
        default=[],
        help="Run only eval tests tagged with one or more eval categories.",
    )
    group.addoption(
        "--model",
        action="store",
        default=None,
        help="Model name exposed to eval tests through the eval_model fixture.",
    )


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "eval_category(*names): tag an evaluation test with one or more logical categories.",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    selected = _normalize_categories(config.getoption("--eval-category"))
    if not selected:
        return

    selected_set = set(selected)
    kept: list[pytest.Item] = []
    deselected: list[pytest.Item] = []
    for item in items:
        categories = _item_categories(item)
        if categories and not selected_set.isdisjoint(categories):
            kept.append(item)
            continue
        deselected.append(item)

    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = kept


@pytest.fixture
def eval_model(pytestconfig: pytest.Config) -> str | None:
    """Return the model selected for the current eval run, if any."""
    return pytestconfig.getoption("--model")


@pytest.fixture
def selected_eval_categories(pytestconfig: pytest.Config) -> tuple[str, ...]:
    """Return the category filter applied to the current pytest invocation."""
    return _normalize_categories(pytestconfig.getoption("--eval-category"))
