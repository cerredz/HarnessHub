"""Tests for harnessiq.providers.coresignal."""

from __future__ import annotations

import unittest

from harnessiq.providers.coresignal import (
    CoreSignalClient,
    CoreSignalCredentials,
    build_company_filter_request,
    build_employee_filter_request,
    build_es_dsl_request,
    build_job_filter_request,
)
from harnessiq.providers.coresignal.api import (
    DEFAULT_BASE_URL,
    build_headers,
    company_collect_url,
    company_es_dsl_url,
    company_filter_search_url,
    employee_collect_url,
    employee_es_dsl_url,
    employee_filter_search_url,
    job_collect_url,
    job_es_dsl_url,
    job_filter_search_url,
)


def _fake_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
    return {"method": method, "url": url, "kwargs": kwargs}


def _make_client(**kwargs: object) -> CoreSignalClient:
    return CoreSignalClient(api_key="test-key", request_executor=_fake_executor, **kwargs)


class CoreSignalCredentialsTests(unittest.TestCase):
    def test_credentials_stores_api_key(self) -> None:
        creds = CoreSignalCredentials(api_key="cs_test_abc123")
        self.assertEqual(creds["api_key"], "cs_test_abc123")

    def test_credentials_is_typed_dict(self) -> None:
        creds = CoreSignalCredentials(api_key="my-key")
        self.assertIsInstance(creds, dict)
        self.assertIn("api_key", creds)


class CoreSignalApiHelpersTests(unittest.TestCase):
    def test_default_base_url(self) -> None:
        self.assertEqual(DEFAULT_BASE_URL, "https://api.coresignal.com/cdapi/v2")

    def test_build_headers_uses_apikey_lowercase(self) -> None:
        headers = build_headers("myapikey")
        self.assertIn("apikey", headers)
        self.assertEqual(headers["apikey"], "myapikey")

    def test_build_headers_does_not_use_authorization(self) -> None:
        headers = build_headers("myapikey")
        self.assertNotIn("Authorization", headers)

    def test_build_headers_does_not_use_x_api_key(self) -> None:
        headers = build_headers("myapikey")
        self.assertNotIn("X-Api-Key", headers)

    def test_build_headers_merges_extra(self) -> None:
        headers = build_headers("key", extra_headers={"Accept": "application/json"})
        self.assertEqual(headers["Accept"], "application/json")
        self.assertIn("apikey", headers)

    def test_employee_filter_search_url(self) -> None:
        url = employee_filter_search_url()
        self.assertIn("/employee_base/search/filter", url)

    def test_employee_collect_url_includes_id(self) -> None:
        url = employee_collect_url(employee_id="42")
        self.assertIn("/employee_base/collect/42", url)

    def test_employee_collect_url_integer_id(self) -> None:
        url = employee_collect_url(employee_id=99)
        self.assertIn("/employee_base/collect/99", url)

    def test_employee_es_dsl_url(self) -> None:
        url = employee_es_dsl_url()
        self.assertIn("/employee_base/search/es_dsl", url)

    def test_company_filter_search_url(self) -> None:
        url = company_filter_search_url()
        self.assertIn("/company_base/search/filter", url)

    def test_company_collect_url_includes_id(self) -> None:
        url = company_collect_url(company_id="100")
        self.assertIn("/company_base/collect/100", url)

    def test_company_es_dsl_url(self) -> None:
        url = company_es_dsl_url()
        self.assertIn("/company_base/search/es_dsl", url)

    def test_job_filter_search_url(self) -> None:
        url = job_filter_search_url()
        self.assertIn("/job_base/search/filter", url)

    def test_job_collect_url_includes_id(self) -> None:
        url = job_collect_url(job_id="77")
        self.assertIn("/job_base/collect/77", url)

    def test_job_es_dsl_url(self) -> None:
        url = job_es_dsl_url()
        self.assertIn("/job_base/search/es_dsl", url)

    def test_custom_base_url_respected(self) -> None:
        url = employee_filter_search_url("https://custom.example.com")
        self.assertTrue(url.startswith("https://custom.example.com"))


class CoreSignalRequestBuildersTests(unittest.TestCase):
    def test_build_employee_filter_includes_defaults(self) -> None:
        payload = build_employee_filter_request()
        self.assertEqual(payload["page"], 1)
        self.assertEqual(payload["size"], 10)

    def test_build_employee_filter_with_fields(self) -> None:
        payload = build_employee_filter_request(name="Alice", title="Engineer", company_name="Acme")
        self.assertEqual(payload["name"], "Alice")
        self.assertEqual(payload["title"], "Engineer")
        self.assertEqual(payload["company_name"], "Acme")

    def test_build_employee_filter_omits_none_fields(self) -> None:
        payload = build_employee_filter_request(name="Bob")
        self.assertNotIn("title", payload)
        self.assertNotIn("location", payload)

    def test_build_employee_filter_custom_pagination(self) -> None:
        payload = build_employee_filter_request(page=3, size=25)
        self.assertEqual(payload["page"], 3)
        self.assertEqual(payload["size"], 25)

    def test_build_es_dsl_request_includes_query(self) -> None:
        query = {"match": {"name": "John"}}
        payload = build_es_dsl_request(query)
        self.assertEqual(payload["query"], {"match": {"name": "John"}})

    def test_build_es_dsl_request_defaults(self) -> None:
        payload = build_es_dsl_request({"match_all": {}})
        self.assertEqual(payload["size"], 10)
        self.assertEqual(payload["from"], 0)

    def test_build_es_dsl_request_custom_pagination(self) -> None:
        payload = build_es_dsl_request({"match_all": {}}, size=50, from_=100)
        self.assertEqual(payload["size"], 50)
        self.assertEqual(payload["from"], 100)

    def test_build_es_dsl_request_deep_copies_query(self) -> None:
        query = {"match": {"name": "Alice"}}
        payload = build_es_dsl_request(query)
        query["match"]["name"] = "Modified"
        self.assertEqual(payload["query"]["match"]["name"], "Alice")

    def test_build_company_filter_with_fields(self) -> None:
        payload = build_company_filter_request(name="Acme", website="acme.com", industry="tech")
        self.assertEqual(payload["name"], "Acme")
        self.assertEqual(payload["website"], "acme.com")
        self.assertEqual(payload["industry"], "tech")

    def test_build_company_filter_omits_none_fields(self) -> None:
        payload = build_company_filter_request(name="Acme")
        self.assertNotIn("country", payload)

    def test_build_job_filter_with_fields(self) -> None:
        payload = build_job_filter_request(title="Engineer", company_name="Acme", location="NYC")
        self.assertEqual(payload["title"], "Engineer")
        self.assertEqual(payload["location"], "NYC")

    def test_build_job_filter_with_date_range(self) -> None:
        payload = build_job_filter_request(date_from="2024-01-01", date_to="2024-06-30")
        self.assertEqual(payload["date_from"], "2024-01-01")
        self.assertEqual(payload["date_to"], "2024-06-30")

    def test_build_job_filter_omits_none_fields(self) -> None:
        payload = build_job_filter_request(title="Developer")
        self.assertNotIn("company_name", payload)
        self.assertNotIn("date_from", payload)


class CoreSignalClientTests(unittest.TestCase):
    def _client(self) -> CoreSignalClient:
        return _make_client()

    def test_client_stores_api_key(self) -> None:
        client = CoreSignalClient(api_key="cs-key")
        self.assertEqual(client.api_key, "cs-key")

    def test_client_default_base_url(self) -> None:
        client = CoreSignalClient(api_key="key")
        self.assertEqual(client.base_url, DEFAULT_BASE_URL)

    def test_search_employees_by_filter_posts(self) -> None:
        client = self._client()
        result = client.search_employees_by_filter(name="Alice", title="Engineer")
        self.assertEqual(result["method"], "POST")
        self.assertIn("/employee_base/search/filter", result["url"])

    def test_search_employees_by_filter_payload(self) -> None:
        captured: dict[str, object] = {}

        def recording_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured.update(kwargs)
            return {}

        client = CoreSignalClient(api_key="key", request_executor=recording_executor)
        client.search_employees_by_filter(name="Alice", company_name="Acme")
        body = captured["json_body"]
        self.assertEqual(body["name"], "Alice")
        self.assertEqual(body["company_name"], "Acme")

    def test_get_employee_sends_get(self) -> None:
        client = self._client()
        result = client.get_employee("123")
        self.assertEqual(result["method"], "GET")
        self.assertIn("/employee_base/collect/123", result["url"])

    def test_get_employee_integer_id(self) -> None:
        client = self._client()
        result = client.get_employee(456)
        self.assertIn("/employee_base/collect/456", result["url"])

    def test_search_employees_es_dsl_posts(self) -> None:
        client = self._client()
        result = client.search_employees_es_dsl({"match_all": {}})
        self.assertEqual(result["method"], "POST")
        self.assertIn("/employee_base/search/es_dsl", result["url"])

    def test_search_employees_es_dsl_payload(self) -> None:
        captured: dict[str, object] = {}

        def recording_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured.update(kwargs)
            return {}

        client = CoreSignalClient(api_key="key", request_executor=recording_executor)
        client.search_employees_es_dsl({"match": {"title": "Engineer"}}, size=5, from_=10)
        body = captured["json_body"]
        self.assertEqual(body["query"], {"match": {"title": "Engineer"}})
        self.assertEqual(body["size"], 5)
        self.assertEqual(body["from"], 10)

    def test_search_companies_by_filter_posts(self) -> None:
        client = self._client()
        result = client.search_companies_by_filter(name="Acme")
        self.assertEqual(result["method"], "POST")
        self.assertIn("/company_base/search/filter", result["url"])

    def test_get_company_sends_get(self) -> None:
        client = self._client()
        result = client.get_company("789")
        self.assertEqual(result["method"], "GET")
        self.assertIn("/company_base/collect/789", result["url"])

    def test_search_companies_es_dsl_posts(self) -> None:
        client = self._client()
        result = client.search_companies_es_dsl({"match_all": {}})
        self.assertEqual(result["method"], "POST")
        self.assertIn("/company_base/search/es_dsl", result["url"])

    def test_search_jobs_by_filter_posts(self) -> None:
        client = self._client()
        result = client.search_jobs_by_filter(title="Python Developer")
        self.assertEqual(result["method"], "POST")
        self.assertIn("/job_base/search/filter", result["url"])

    def test_get_job_sends_get(self) -> None:
        client = self._client()
        result = client.get_job("job-001")
        self.assertEqual(result["method"], "GET")
        self.assertIn("/job_base/collect/job-001", result["url"])

    def test_search_jobs_es_dsl_posts(self) -> None:
        client = self._client()
        result = client.search_jobs_es_dsl({"match_all": {}})
        self.assertEqual(result["method"], "POST")
        self.assertIn("/job_base/search/es_dsl", result["url"])

    def test_apikey_header_passed_to_executor(self) -> None:
        captured: dict[str, object] = {}

        def recording_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured.update(kwargs)
            return {}

        client = CoreSignalClient(api_key="secret-api-key", request_executor=recording_executor)
        client.get_employee("1")
        headers = captured.get("headers", {})
        self.assertEqual(headers["apikey"], "secret-api-key")
        self.assertNotIn("Authorization", headers)

    def test_timeout_passed_to_executor(self) -> None:
        captured: dict[str, object] = {}

        def recording_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured.update(kwargs)
            return {}

        client = CoreSignalClient(api_key="key", timeout_seconds=45.0, request_executor=recording_executor)
        client.search_employees_by_filter()
        self.assertEqual(captured["timeout_seconds"], 45.0)

    def test_get_methods_send_no_json_body(self) -> None:
        captured: dict[str, object] = {}

        def recording_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured.update(kwargs)
            return {}

        client = CoreSignalClient(api_key="key", request_executor=recording_executor)
        client.get_company("42")
        self.assertIsNone(captured.get("json_body"))

    def test_custom_base_url_used_by_client(self) -> None:
        client = CoreSignalClient(
            api_key="key",
            base_url="https://proxy.example.com",
            request_executor=_fake_executor,
        )
        result = client.search_employees_by_filter()
        self.assertTrue(result["url"].startswith("https://proxy.example.com"))

    def test_search_jobs_by_filter_with_date_range(self) -> None:
        captured: dict[str, object] = {}

        def recording_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured.update(kwargs)
            return {}

        client = CoreSignalClient(api_key="key", request_executor=recording_executor)
        client.search_jobs_by_filter(title="Dev", date_from="2024-01-01", date_to="2024-12-31")
        body = captured["json_body"]
        self.assertEqual(body["date_from"], "2024-01-01")
        self.assertEqual(body["date_to"], "2024-12-31")


if __name__ == "__main__":
    unittest.main()
