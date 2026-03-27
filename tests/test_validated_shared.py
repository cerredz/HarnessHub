"""Tests for shared validated scalar value objects."""

from __future__ import annotations

import unittest

from harnessiq.shared import (
    EnvVarName,
    HttpUrl,
    NonEmptyString,
    NonNegativeInt,
    PositiveInt,
    ProviderFamilyName,
    parse_bounded_int,
    parse_positive_number,
)


class ValidatedSharedTests(unittest.TestCase):
    def test_non_empty_string_trims_whitespace(self) -> None:
        value = NonEmptyString("  hello  ", field_name="greeting")

        self.assertEqual(value, "hello")
        self.assertEqual(value.value, "hello")

    def test_non_empty_string_rejects_blank_text(self) -> None:
        with self.assertRaisesRegex(ValueError, "greeting must not be blank"):
            NonEmptyString("   ", field_name="greeting")

    def test_env_var_name_requires_shell_safe_identifier(self) -> None:
        self.assertEqual(EnvVarName("HARNESSIQ_API_KEY"), "HARNESSIQ_API_KEY")
        with self.assertRaisesRegex(ValueError, "environment variable name"):
            EnvVarName("bad-name")

    def test_provider_family_name_lowercases_and_validates(self) -> None:
        self.assertEqual(ProviderFamilyName(" OpenAI "), "openai")
        with self.assertRaisesRegex(ValueError, "lowercase provider identifier"):
            ProviderFamilyName("bad-family")

    def test_http_url_requires_http_or_https(self) -> None:
        self.assertEqual(HttpUrl("https://api.openai.com"), "https://api.openai.com")
        with self.assertRaisesRegex(ValueError, "http or https URL"):
            HttpUrl("ftp://example.com")

    def test_non_negative_int_rejects_negative_values(self) -> None:
        self.assertEqual(NonNegativeInt(0), 0)
        with self.assertRaisesRegex(ValueError, "greater than or equal to zero"):
            NonNegativeInt(-1, field_name="index")

    def test_positive_int_rejects_zero(self) -> None:
        self.assertEqual(PositiveInt(2), 2)
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            PositiveInt(0, field_name="count")

    def test_parse_bounded_int_enforces_inclusive_bounds(self) -> None:
        self.assertEqual(parse_bounded_int(5, field_name="steps", minimum=3, maximum=10), 5)
        with self.assertRaisesRegex(ValueError, "greater than or equal to 3"):
            parse_bounded_int(2, field_name="steps", minimum=3, maximum=10)
        with self.assertRaisesRegex(ValueError, "less than or equal to 10"):
            parse_bounded_int(11, field_name="steps", minimum=3, maximum=10)

    def test_integer_validators_reject_booleans(self) -> None:
        with self.assertRaisesRegex(ValueError, "count must be an integer"):
            PositiveInt(True, field_name="count")

    def test_parse_positive_number_accepts_float_and_rejects_zero(self) -> None:
        self.assertEqual(parse_positive_number(1.5, field_name="timeout_seconds"), 1.5)
        with self.assertRaisesRegex(ValueError, "greater than zero"):
            parse_positive_number(0, field_name="timeout_seconds")


if __name__ == "__main__":
    unittest.main()
