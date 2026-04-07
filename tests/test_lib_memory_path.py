"""Tests for harnessiq.lib.memory.MemoryPathInput."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from harnessiq.lib.memory import MemoryPathInput


class TestMemoryPathInputConstruction:
    def test_accepts_existing_directory(self, tmp_path: Path) -> None:
        m = MemoryPathInput(str(tmp_path))
        assert m.path == tmp_path.resolve()

    def test_accepts_nonexistent_path(self) -> None:
        m = MemoryPathInput("/tmp/harnessiq_test_nonexistent_xyz_12345")
        assert isinstance(m.path, Path)

    def test_resolves_to_absolute_path(self) -> None:
        m = MemoryPathInput("relative/memory/path")
        assert m.path.is_absolute()

    def test_strips_surrounding_whitespace(self, tmp_path: Path) -> None:
        m = MemoryPathInput(f"  {tmp_path}  ")
        assert m.path == tmp_path.resolve()

    def test_repr_includes_resolved_path(self, tmp_path: Path) -> None:
        m = MemoryPathInput(str(tmp_path))
        assert "MemoryPathInput(" in repr(m)
        assert repr(str(tmp_path.resolve())) in repr(m)

    def test_str_returns_resolved_string(self, tmp_path: Path) -> None:
        m = MemoryPathInput(str(tmp_path))
        assert str(m) == str(tmp_path.resolve())


class TestMemoryPathInputValidation:
    def test_raises_type_error_for_non_string(self) -> None:
        with pytest.raises(TypeError, match="must be a str"):
            MemoryPathInput(123)  # type: ignore[arg-type]

    def test_raises_type_error_for_none(self) -> None:
        with pytest.raises(TypeError, match="must be a str"):
            MemoryPathInput(None)  # type: ignore[arg-type]

    def test_raises_value_error_for_empty_string(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            MemoryPathInput("")

    def test_raises_value_error_for_whitespace_only(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            MemoryPathInput("   ")

    def test_raises_value_error_for_null_byte(self) -> None:
        with pytest.raises(ValueError, match="null bytes"):
            MemoryPathInput("/tmp/foo\x00bar")

    def test_raises_value_error_when_existing_path_is_a_file(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as f:
            fname = f.name
        try:
            with pytest.raises(ValueError, match="not a directory"):
                MemoryPathInput(fname)
        finally:
            os.unlink(fname)


class TestMemoryPathInputFromStr:
    def test_from_str_returns_none_for_none_input(self) -> None:
        assert MemoryPathInput.from_str(None) is None

    def test_from_str_returns_instance_for_valid_string(self, tmp_path: Path) -> None:
        result = MemoryPathInput.from_str(str(tmp_path))
        assert isinstance(result, MemoryPathInput)
        assert result.path == tmp_path.resolve()

    def test_from_str_propagates_validation_errors(self) -> None:
        with pytest.raises(ValueError, match="must not be empty"):
            MemoryPathInput.from_str("")


class TestMemoryPathInputEquality:
    def test_equal_instances_with_same_path(self, tmp_path: Path) -> None:
        a = MemoryPathInput(str(tmp_path))
        b = MemoryPathInput(str(tmp_path))
        assert a == b

    def test_hash_equal_for_equal_instances(self, tmp_path: Path) -> None:
        a = MemoryPathInput(str(tmp_path))
        b = MemoryPathInput(str(tmp_path))
        assert hash(a) == hash(b)

    def test_not_equal_for_different_paths(self, tmp_path: Path) -> None:
        a = MemoryPathInput(str(tmp_path))
        b = MemoryPathInput(str(tmp_path / "sub"))
        assert a != b

    def test_not_equal_to_unrelated_type(self, tmp_path: Path) -> None:
        m = MemoryPathInput(str(tmp_path))
        assert m != str(tmp_path)
