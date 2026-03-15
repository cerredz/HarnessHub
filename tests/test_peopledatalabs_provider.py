"""Tests for the People Data Labs provider client and request builders."""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError
from typing import Any
from urllib.parse import parse_qs, urlparse

from harnessiq.providers.peopledatalabs import (
    DEFAULT_BASE_URL,
    PeopleDataLabsClient,
    PeopleDataLabsCredentials,
    autocomplete_url,
    build_company_bulk_request,
    build_company_search_request,
    build_headers,
    build_person_bulk_request,
    build_person_search_request,
    company_bulk_url,
    company_enrich_url,
    company_search_url,
    job_title_enrich_url,
    location_clean_url,
    person_bulk_url,
    person_enrich_url,
    person_identify_url,
    person_search_url,
    school_enrich_url,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(captured: list[dict[str, Any]]) -> PeopleDataLabsClient:
    """Return a client whose executor records every call in *captured*."""

    def fake_executor(
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: Any | None = None,
        timeout_seconds: float = 60.0,
    ) -> dict[str, Any]:
        captured.append(
            {"method": method, "url": url, "json_body": json_body, "headers": headers}
        )
        return {"data": {}, "status": 200}

    return PeopleDataLabsClient(api_key="pdl_key", request_executor=fake_executor)


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------


class TestPeopleDataLabsCredentials(unittest.TestCase):
    def test_credentials_is_typeddict(self) -> None:
        creds: PeopleDataLabsCredentials = {"api_key": "test_key"}
        self.assertEqual(creds["api_key"], "test_key")

    def test_credentials_has_api_key_field(self) -> None:
        # TypedDict keys are accessible; total=True is a static typing contract
        creds: PeopleDataLabsCredentials = {"api_key": "another_key"}
        self.assertIn("api_key", creds)


# ---------------------------------------------------------------------------
# build_headers
# ---------------------------------------------------------------------------


class TestBuildHeaders(unittest.TestCase):
    def test_includes_x_api_key(self) -> None:
        headers = build_headers("my_api_key")
        self.assertEqual(headers["X-Api-Key"], "my_api_key")

    def test_no_extra_headers_by_default(self) -> None:
        headers = build_headers("key")
        self.assertEqual(list(headers.keys()), ["X-Api-Key"])

    def test_extra_headers_are_merged(self) -> None:
        headers = build_headers("key", extra_headers={"X-Custom": "value"})
        self.assertEqual(headers["X-Api-Key"], "key")
        self.assertEqual(headers["X-Custom"], "value")

    def test_extra_headers_can_override(self) -> None:
        headers = build_headers("key", extra_headers={"X-Api-Key": "override"})
        self.assertEqual(headers["X-Api-Key"], "override")


# ---------------------------------------------------------------------------
# URL builders
# ---------------------------------------------------------------------------


class TestUrlBuilders(unittest.TestCase):
    def test_default_base_url(self) -> None:
        self.assertEqual(DEFAULT_BASE_URL, "https://api.peopledatalabs.com/v5")

    def test_person_enrich_url(self) -> None:
        self.assertEqual(
            person_enrich_url(), "https://api.peopledatalabs.com/v5/person/enrich"
        )

    def test_person_identify_url(self) -> None:
        self.assertEqual(
            person_identify_url(), "https://api.peopledatalabs.com/v5/person/identify"
        )

    def test_person_search_url(self) -> None:
        self.assertEqual(
            person_search_url(), "https://api.peopledatalabs.com/v5/person/search"
        )

    def test_person_bulk_url(self) -> None:
        self.assertEqual(
            person_bulk_url(), "https://api.peopledatalabs.com/v5/person/bulk"
        )

    def test_company_enrich_url(self) -> None:
        self.assertEqual(
            company_enrich_url(), "https://api.peopledatalabs.com/v5/company/enrich"
        )

    def test_company_search_url(self) -> None:
        self.assertEqual(
            company_search_url(), "https://api.peopledatalabs.com/v5/company/search"
        )

    def test_company_bulk_url(self) -> None:
        self.assertEqual(
            company_bulk_url(), "https://api.peopledatalabs.com/v5/company/bulk"
        )

    def test_school_enrich_url(self) -> None:
        self.assertEqual(
            school_enrich_url(), "https://api.peopledatalabs.com/v5/school/enrich"
        )

    def test_location_clean_url(self) -> None:
        self.assertEqual(
            location_clean_url(), "https://api.peopledatalabs.com/v5/location/clean"
        )

    def test_autocomplete_url(self) -> None:
        self.assertEqual(
            autocomplete_url(), "https://api.peopledatalabs.com/v5/autocomplete"
        )

    def test_job_title_enrich_url(self) -> None:
        self.assertEqual(
            job_title_enrich_url(),
            "https://api.peopledatalabs.com/v5/job_title/enrich",
        )

    def test_url_builders_respect_custom_base_url(self) -> None:
        custom = "https://custom.example.com"
        self.assertEqual(person_enrich_url(custom), "https://custom.example.com/person/enrich")


# ---------------------------------------------------------------------------
# Request payload builders
# ---------------------------------------------------------------------------


class TestPersonSearchRequest(unittest.TestCase):
    def test_build_with_query(self) -> None:
        query = {"match": {"job_title": "engineer"}}
        payload = build_person_search_request(query=query, size=5, from_=0)
        self.assertEqual(payload["query"], query)
        self.assertEqual(payload["size"], 5)
        self.assertEqual(payload["from"], 0)

    def test_build_with_sql(self) -> None:
        sql = "SELECT * FROM person WHERE job_title = 'engineer'"
        payload = build_person_search_request(sql=sql)
        self.assertEqual(payload["sql"], sql)
        self.assertNotIn("query", payload)

    def test_defaults(self) -> None:
        payload = build_person_search_request()
        self.assertEqual(payload["size"], 10)
        self.assertEqual(payload["from"], 0)

    def test_query_is_deep_copied(self) -> None:
        query: dict[str, Any] = {"key": [1, 2, 3]}
        payload = build_person_search_request(query=query)
        payload["query"]["key"].append(4)  # type: ignore[index]
        self.assertEqual(query["key"], [1, 2, 3])


class TestPersonBulkRequest(unittest.TestCase):
    def test_includes_requests_list(self) -> None:
        reqs = [{"params": {"email": "a@example.com"}}]
        payload = build_person_bulk_request(reqs)
        self.assertEqual(payload["requests"], reqs)

    def test_size_omitted_when_none(self) -> None:
        payload = build_person_bulk_request([])
        self.assertNotIn("size", payload)

    def test_size_included_when_provided(self) -> None:
        payload = build_person_bulk_request([], size=5)
        self.assertEqual(payload["size"], 5)

    def test_requests_list_is_deep_copied(self) -> None:
        reqs = [{"params": {"email": "a@example.com"}}]
        payload = build_person_bulk_request(reqs)
        payload["requests"][0]["params"]["email"] = "changed"  # type: ignore[index]
        self.assertEqual(reqs[0]["params"]["email"], "a@example.com")


class TestCompanySearchRequest(unittest.TestCase):
    def test_build_with_query(self) -> None:
        query = {"match": {"industry": "software"}}
        payload = build_company_search_request(query=query, size=3)
        self.assertEqual(payload["query"], query)
        self.assertEqual(payload["size"], 3)

    def test_build_with_sql(self) -> None:
        sql = "SELECT * FROM company WHERE industry = 'software'"
        payload = build_company_search_request(sql=sql)
        self.assertEqual(payload["sql"], sql)

    def test_defaults(self) -> None:
        payload = build_company_search_request()
        self.assertEqual(payload["size"], 10)
        self.assertEqual(payload["from"], 0)


class TestCompanyBulkRequest(unittest.TestCase):
    def test_includes_requests_list(self) -> None:
        reqs = [{"params": {"website": "acme.com"}}]
        payload = build_company_bulk_request(reqs)
        self.assertEqual(payload["requests"], reqs)

    def test_size_omitted_when_none(self) -> None:
        payload = build_company_bulk_request([])
        self.assertNotIn("size", payload)


# ---------------------------------------------------------------------------
# Client behavior
# ---------------------------------------------------------------------------


class TestPeopleDataLabsClientFrozen(unittest.TestCase):
    def test_frozen_dataclass_raises_on_mutation(self) -> None:
        client = PeopleDataLabsClient(api_key="key")
        with self.assertRaises(FrozenInstanceError):
            client.api_key = "new_key"  # type: ignore[misc]

    def test_default_base_url(self) -> None:
        client = PeopleDataLabsClient(api_key="key")
        self.assertEqual(client.base_url, DEFAULT_BASE_URL)

    def test_default_timeout(self) -> None:
        client = PeopleDataLabsClient(api_key="key")
        self.assertEqual(client.timeout_seconds, 60.0)


class TestPeopleDataLabsClientPersonMethods(unittest.TestCase):
    def setUp(self) -> None:
        self.captured: list[dict[str, Any]] = []
        self.client = _make_client(self.captured)

    def test_enrich_person_uses_get(self) -> None:
        self.client.enrich_person(email="alice@example.com")
        self.assertEqual(self.captured[0]["method"], "GET")

    def test_enrich_person_encodes_params_in_url(self) -> None:
        self.client.enrich_person(email="alice@example.com", name="Alice")
        url = self.captured[0]["url"]
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        self.assertIn("email", params)
        self.assertEqual(params["email"][0], "alice@example.com")
        self.assertIn("name", params)

    def test_enrich_person_omits_none_params(self) -> None:
        self.client.enrich_person(email="alice@example.com")
        url = self.captured[0]["url"]
        self.assertNotIn("phone", url)
        self.assertNotIn("linkedin_url", url)

    def test_enrich_person_sends_no_json_body(self) -> None:
        self.client.enrich_person(email="alice@example.com")
        self.assertIsNone(self.captured[0]["json_body"])

    def test_enrich_person_includes_api_key_header(self) -> None:
        self.client.enrich_person(email="alice@example.com")
        self.assertEqual(self.captured[0]["headers"]["X-Api-Key"], "pdl_key")

    def test_identify_person_uses_get(self) -> None:
        self.client.identify_person(email="bob@example.com")
        self.assertEqual(self.captured[0]["method"], "GET")

    def test_identify_person_url_contains_identify_path(self) -> None:
        self.client.identify_person(email="bob@example.com")
        self.assertIn("/person/identify", self.captured[0]["url"])

    def test_search_people_uses_post(self) -> None:
        self.client.search_people(sql="SELECT * FROM person")
        self.assertEqual(self.captured[0]["method"], "POST")

    def test_search_people_sends_json_body(self) -> None:
        self.client.search_people(sql="SELECT * FROM person", size=5)
        body = self.captured[0]["json_body"]
        self.assertIsNotNone(body)
        self.assertEqual(body["sql"], "SELECT * FROM person")
        self.assertEqual(body["size"], 5)

    def test_search_people_with_query_dict(self) -> None:
        query = {"match": {"job_title": "engineer"}}
        self.client.search_people(query=query)
        body = self.captured[0]["json_body"]
        self.assertEqual(body["query"], query)

    def test_search_people_url_contains_no_query_string(self) -> None:
        self.client.search_people(sql="SELECT * FROM person")
        url = self.captured[0]["url"]
        self.assertNotIn("?", url)

    def test_bulk_enrich_people_uses_post(self) -> None:
        self.client.bulk_enrich_people([{"params": {"email": "x@example.com"}}])
        self.assertEqual(self.captured[0]["method"], "POST")

    def test_bulk_enrich_people_sends_requests_in_body(self) -> None:
        reqs = [{"params": {"email": "x@example.com"}}]
        self.client.bulk_enrich_people(reqs)
        body = self.captured[0]["json_body"]
        self.assertEqual(body["requests"], reqs)

    def test_bulk_enrich_people_url_path(self) -> None:
        self.client.bulk_enrich_people([])
        self.assertIn("/person/bulk", self.captured[0]["url"])


class TestPeopleDataLabsClientCompanyMethods(unittest.TestCase):
    def setUp(self) -> None:
        self.captured: list[dict[str, Any]] = []
        self.client = _make_client(self.captured)

    def test_enrich_company_uses_get(self) -> None:
        self.client.enrich_company(name="Acme Corp")
        self.assertEqual(self.captured[0]["method"], "GET")

    def test_enrich_company_encodes_params_in_url(self) -> None:
        self.client.enrich_company(name="Acme Corp", website="acme.com")
        url = self.captured[0]["url"]
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        self.assertIn("name", params)
        self.assertIn("website", params)

    def test_enrich_company_omits_none_params(self) -> None:
        self.client.enrich_company(name="Acme Corp")
        url = self.captured[0]["url"]
        self.assertNotIn("ticker", url)

    def test_search_companies_uses_post(self) -> None:
        self.client.search_companies(sql="SELECT * FROM company")
        self.assertEqual(self.captured[0]["method"], "POST")

    def test_search_companies_sends_json_body(self) -> None:
        self.client.search_companies(sql="SELECT * FROM company", size=3)
        body = self.captured[0]["json_body"]
        self.assertEqual(body["sql"], "SELECT * FROM company")
        self.assertEqual(body["size"], 3)

    def test_bulk_enrich_companies_uses_post(self) -> None:
        self.client.bulk_enrich_companies([{"params": {"website": "acme.com"}}])
        self.assertEqual(self.captured[0]["method"], "POST")

    def test_bulk_enrich_companies_url_path(self) -> None:
        self.client.bulk_enrich_companies([])
        self.assertIn("/company/bulk", self.captured[0]["url"])


class TestPeopleDataLabsClientMiscMethods(unittest.TestCase):
    def setUp(self) -> None:
        self.captured: list[dict[str, Any]] = []
        self.client = _make_client(self.captured)

    def test_enrich_school_uses_get(self) -> None:
        self.client.enrich_school(name="MIT")
        self.assertEqual(self.captured[0]["method"], "GET")

    def test_enrich_school_url_contains_school_path(self) -> None:
        self.client.enrich_school(name="MIT")
        self.assertIn("/school/enrich", self.captured[0]["url"])

    def test_clean_location_uses_get(self) -> None:
        self.client.clean_location("San Francisco, CA")
        self.assertEqual(self.captured[0]["method"], "GET")

    def test_clean_location_encodes_param(self) -> None:
        self.client.clean_location("New York, NY")
        url = self.captured[0]["url"]
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        self.assertIn("location", params)
        self.assertEqual(params["location"][0], "New York, NY")

    def test_autocomplete_uses_get(self) -> None:
        self.client.autocomplete("job_title", "softw")
        self.assertEqual(self.captured[0]["method"], "GET")

    def test_autocomplete_encodes_all_params(self) -> None:
        self.client.autocomplete("job_title", "softw", size=5)
        url = self.captured[0]["url"]
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        self.assertEqual(params["field"][0], "job_title")
        self.assertEqual(params["text"][0], "softw")
        self.assertEqual(params["size"][0], "5")

    def test_enrich_job_title_uses_get(self) -> None:
        self.client.enrich_job_title("Software Engineer")
        self.assertEqual(self.captured[0]["method"], "GET")

    def test_enrich_job_title_encodes_param(self) -> None:
        self.client.enrich_job_title("Software Engineer")
        url = self.captured[0]["url"]
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        self.assertEqual(params["job_title"][0], "Software Engineer")

    def test_all_methods_pass_timeout_seconds(self) -> None:
        client = PeopleDataLabsClient(
            api_key="key",
            timeout_seconds=30.0,
            request_executor=lambda m, u, *, headers=None, json_body=None, timeout_seconds=60.0: {
                "timeout_seconds": timeout_seconds
            },
        )
        result = client.enrich_person(email="x@example.com")
        self.assertEqual(result["timeout_seconds"], 30.0)


if __name__ == "__main__":
    unittest.main()
