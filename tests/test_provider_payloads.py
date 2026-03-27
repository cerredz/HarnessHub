"""Tests for shared provider payload helper utilities."""

from __future__ import annotations

import unittest

from harnessiq.shared.dtos import ProviderPayloadRequestDTO, ProviderPayloadResultDTO
from harnessiq.shared.provider_payloads import (
    execute_payload_operation,
    optional_payload_string_list,
    require_payload_string,
)


class ProviderPayloadHelpersTests(unittest.TestCase):
    def test_require_payload_string_trims_value(self) -> None:
        self.assertEqual(require_payload_string({"name": "  Alice  "}, "name"), "Alice")

    def test_optional_payload_string_list_trims_each_value(self) -> None:
        self.assertEqual(
            optional_payload_string_list({"tags": ["  one  ", "two"]}, "tags"),
            ["one", "two"],
        )

    def test_execute_payload_operation_wraps_result(self) -> None:
        class _Target:
            def ping(self, *, message: str) -> dict[str, str]:
                return {"echo": message}

        result = execute_payload_operation(
            _Target(),
            ProviderPayloadRequestDTO(operation="ping", payload={"message": "hello"}),
        )

        self.assertIsInstance(result, ProviderPayloadResultDTO)
        self.assertEqual(result.to_dict(), {"operation": "ping", "result": {"echo": "hello"}})

    def test_execute_payload_operation_rejects_private_operation(self) -> None:
        class _Target:
            def _hidden(self) -> None:
                raise AssertionError("should not be called")

        with self.assertRaises(ValueError):
            execute_payload_operation(
                _Target(),
                ProviderPayloadRequestDTO(operation="_hidden", payload={}),
            )


if __name__ == "__main__":
    unittest.main()
