"""Tests for harnessiq.providers.proxycurl."""

from __future__ import annotations

import unittest
import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from harnessiq.providers.proxycurl import (
        ProxycurlClient,
        ProxycurlCredentials,
        build_list_company_jobs_params,
        build_list_employees_params,
        build_lookup_person_by_email_params,
        build_personal_contacts_params,
        build_personal_emails_params,
        build_resolve_company_params,
        build_resolve_email_params,
        build_resolve_person_params,
        build_scrape_company_params,
        build_scrape_person_params,
        build_search_jobs_params,
    )

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from harnessiq.providers.proxycurl.api import (
        DEFAULT_BASE_URL,
        build_headers,
        get_personal_contacts_url,
        get_personal_emails_url,
        list_company_employees_url,
        list_company_jobs_url,
        lookup_person_by_email_url,
        resolve_company_linkedin_url,
        resolve_email_to_profile_url,
        resolve_person_linkedin_url,
        scrape_linkedin_company_url,
        scrape_linkedin_person_url,
        search_jobs_url,
    )


def _fake_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
    return {"method": method, "url": url, "kwargs": kwargs}


def _make_client(**kwargs: object) -> ProxycurlClient:
    return ProxycurlClient(api_key="test-key", request_executor=_fake_executor, **kwargs)


class ProxycurlDeprecationWarningTests(unittest.TestCase):
    def test_import_raises_deprecation_warning(self) -> None:
        import importlib
        import sys

        # Remove cached modules to force re-import
        for mod in list(sys.modules.keys()):
            if "proxycurl" in mod:
                del sys.modules[mod]

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            import harnessiq.providers.proxycurl  # noqa: F401

        deprecation_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
        self.assertTrue(len(deprecation_warnings) >= 1)
        self.assertIn("January 2025", str(deprecation_warnings[0].message))


class ProxycurlCredentialsTests(unittest.TestCase):
    def test_credentials_stores_api_key(self) -> None:
        creds = ProxycurlCredentials(api_key="pk_test_123")
        self.assertEqual(creds["api_key"], "pk_test_123")

    def test_credentials_is_typed_dict(self) -> None:
        creds = ProxycurlCredentials(api_key="my-key")
        self.assertIsInstance(creds, dict)
        self.assertIn("api_key", creds)


class ProxycurlApiHelpersTests(unittest.TestCase):
    def test_default_base_url(self) -> None:
        self.assertEqual(DEFAULT_BASE_URL, "https://nubela.co/proxycurl/api")

    def test_build_headers_sets_bearer_token(self) -> None:
        headers = build_headers("mykey123")
        self.assertEqual(headers["Authorization"], "Bearer mykey123")

    def test_build_headers_merges_extra(self) -> None:
        headers = build_headers("key", extra_headers={"X-Custom": "value"})
        self.assertEqual(headers["X-Custom"], "value")
        self.assertIn("Authorization", headers)

    def test_scrape_linkedin_person_url_no_query(self) -> None:
        url = scrape_linkedin_person_url()
        self.assertEqual(url, "https://nubela.co/proxycurl/api/v2/linkedin")

    def test_scrape_linkedin_person_url_with_query(self) -> None:
        url = scrape_linkedin_person_url(query={"url": "https://linkedin.com/in/test"})
        self.assertIn("url=", url)
        self.assertIn("/v2/linkedin", url)

    def test_resolve_person_linkedin_url(self) -> None:
        url = resolve_person_linkedin_url()
        self.assertIn("/linkedin/person/resolve", url)

    def test_lookup_person_by_email_url(self) -> None:
        url = lookup_person_by_email_url()
        self.assertIn("/v2/linkedin/person/lookup", url)

    def test_scrape_linkedin_company_url(self) -> None:
        url = scrape_linkedin_company_url()
        self.assertIn("/linkedin/company", url)

    def test_resolve_company_linkedin_url(self) -> None:
        url = resolve_company_linkedin_url()
        self.assertIn("/linkedin/company/resolve", url)

    def test_list_company_employees_url(self) -> None:
        url = list_company_employees_url()
        self.assertIn("/linkedin/company/employees", url)

    def test_list_company_jobs_url(self) -> None:
        url = list_company_jobs_url()
        self.assertIn("/linkedin/company/job", url)

    def test_search_jobs_url(self) -> None:
        url = search_jobs_url()
        self.assertIn("/linkedin/jobs/search", url)

    def test_resolve_email_to_profile_url(self) -> None:
        url = resolve_email_to_profile_url()
        self.assertIn("/linkedin/profile/email/resolve", url)

    def test_get_personal_emails_url(self) -> None:
        url = get_personal_emails_url()
        self.assertIn("/contact-api/personal-email", url)

    def test_get_personal_contacts_url(self) -> None:
        url = get_personal_contacts_url()
        self.assertIn("/contact-api/personal-contact", url)

    def test_custom_base_url_respected(self) -> None:
        url = scrape_linkedin_person_url("https://custom.example.com")
        self.assertTrue(url.startswith("https://custom.example.com"))


class ProxycurlRequestBuildersTests(unittest.TestCase):
    def test_build_scrape_person_params_required_only(self) -> None:
        params = build_scrape_person_params(url="https://linkedin.com/in/test")
        self.assertEqual(params["url"], "https://linkedin.com/in/test")
        self.assertNotIn("skills", params)

    def test_build_scrape_person_params_with_optional(self) -> None:
        params = build_scrape_person_params(
            url="https://linkedin.com/in/test",
            skills="include",
            inferred_salary="include",
        )
        self.assertEqual(params["skills"], "include")
        self.assertEqual(params["inferred_salary"], "include")

    def test_build_resolve_person_params_omits_nones(self) -> None:
        params = build_resolve_person_params(first_name="John", last_name="Doe")
        self.assertEqual(params["first_name"], "John")
        self.assertNotIn("company_domain", params)

    def test_build_lookup_person_by_email_params(self) -> None:
        params = build_lookup_person_by_email_params(email_address="test@example.com")
        self.assertEqual(params["email_address"], "test@example.com")

    def test_build_scrape_company_params(self) -> None:
        params = build_scrape_company_params(url="https://linkedin.com/company/test")
        self.assertEqual(params["url"], "https://linkedin.com/company/test")

    def test_build_scrape_company_params_with_flags(self) -> None:
        params = build_scrape_company_params(
            url="https://linkedin.com/company/test",
            categories="include",
            funding_data="include",
        )
        self.assertEqual(params["categories"], "include")

    def test_build_resolve_company_params(self) -> None:
        params = build_resolve_company_params(company_name="Acme Corp")
        self.assertEqual(params["company_name"], "Acme Corp")

    def test_build_list_employees_params(self) -> None:
        params = build_list_employees_params(url="https://linkedin.com/company/test", page_size=10)
        self.assertEqual(params["url"], "https://linkedin.com/company/test")
        self.assertEqual(params["page_size"], 10)

    def test_build_list_company_jobs_params(self) -> None:
        params = build_list_company_jobs_params(url="https://linkedin.com/company/test", keyword="python")
        self.assertEqual(params["keyword"], "python")

    def test_build_search_jobs_params(self) -> None:
        params = build_search_jobs_params(keyword="engineer", experience_level="senior")
        self.assertEqual(params["keyword"], "engineer")
        self.assertEqual(params["experience_level"], "senior")

    def test_build_resolve_email_params(self) -> None:
        params = build_resolve_email_params(email="test@example.com")
        self.assertEqual(params["email"], "test@example.com")

    def test_build_personal_emails_params(self) -> None:
        params = build_personal_emails_params(
            linkedin_profile_url="https://linkedin.com/in/test",
            page_size=5,
        )
        self.assertEqual(params["page_size"], 5)

    def test_build_personal_contacts_params(self) -> None:
        params = build_personal_contacts_params(linkedin_profile_url="https://linkedin.com/in/test")
        self.assertEqual(params["linkedin_profile_url"], "https://linkedin.com/in/test")
        self.assertNotIn("page_size", params)


class ProxycurlClientTests(unittest.TestCase):
    def _client(self) -> ProxycurlClient:
        return _make_client()

    def test_client_stores_api_key(self) -> None:
        client = ProxycurlClient(api_key="my-key")
        self.assertEqual(client.api_key, "my-key")

    def test_client_default_base_url(self) -> None:
        client = ProxycurlClient(api_key="key")
        self.assertEqual(client.base_url, DEFAULT_BASE_URL)

    def test_scrape_person_profile_sends_get(self) -> None:
        client = self._client()
        result = client.scrape_person_profile(url="https://linkedin.com/in/test")
        self.assertEqual(result["method"], "GET")
        self.assertIn("/v2/linkedin", result["url"])
        self.assertIn("url=", result["url"])

    def test_scrape_person_profile_includes_skills_param(self) -> None:
        client = self._client()
        result = client.scrape_person_profile(url="https://linkedin.com/in/test", skills="include")
        self.assertIn("skills=include", result["url"])

    def test_resolve_person_profile_sends_get(self) -> None:
        client = self._client()
        result = client.resolve_person_profile(first_name="Jane", last_name="Smith")
        self.assertEqual(result["method"], "GET")
        self.assertIn("/linkedin/person/resolve", result["url"])

    def test_lookup_person_by_email_sends_get(self) -> None:
        client = self._client()
        result = client.lookup_person_by_email(email_address="jane@example.com")
        self.assertEqual(result["method"], "GET")
        self.assertIn("/v2/linkedin/person/lookup", result["url"])
        self.assertIn("email_address=", result["url"])

    def test_scrape_company_profile_sends_get(self) -> None:
        client = self._client()
        result = client.scrape_company_profile(url="https://linkedin.com/company/acme")
        self.assertEqual(result["method"], "GET")
        self.assertIn("/linkedin/company", result["url"])

    def test_resolve_company_profile_sends_get(self) -> None:
        client = self._client()
        result = client.resolve_company_profile(company_name="Acme")
        self.assertEqual(result["method"], "GET")
        self.assertIn("/linkedin/company/resolve", result["url"])

    def test_list_company_employees_sends_get(self) -> None:
        client = self._client()
        result = client.list_company_employees(url="https://linkedin.com/company/acme")
        self.assertEqual(result["method"], "GET")
        self.assertIn("/linkedin/company/employees", result["url"])

    def test_list_company_jobs_sends_get(self) -> None:
        client = self._client()
        result = client.list_company_jobs(url="https://linkedin.com/company/acme")
        self.assertEqual(result["method"], "GET")
        self.assertIn("/linkedin/company/job", result["url"])

    def test_search_jobs_sends_get(self) -> None:
        client = self._client()
        result = client.search_jobs(keyword="software engineer")
        self.assertEqual(result["method"], "GET")
        self.assertIn("/linkedin/jobs/search", result["url"])

    def test_resolve_email_to_profile_sends_get(self) -> None:
        client = self._client()
        result = client.resolve_email_to_profile(email="john@example.com")
        self.assertEqual(result["method"], "GET")
        self.assertIn("/linkedin/profile/email/resolve", result["url"])

    def test_get_personal_emails_sends_get(self) -> None:
        client = self._client()
        result = client.get_personal_emails(linkedin_profile_url="https://linkedin.com/in/test")
        self.assertEqual(result["method"], "GET")
        self.assertIn("/contact-api/personal-email", result["url"])

    def test_get_personal_contacts_sends_get(self) -> None:
        client = self._client()
        result = client.get_personal_contacts(linkedin_profile_url="https://linkedin.com/in/test")
        self.assertEqual(result["method"], "GET")
        self.assertIn("/contact-api/personal-contact", result["url"])

    def test_auth_header_passed_to_executor(self) -> None:
        captured: dict[str, object] = {}

        def recording_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured.update(kwargs)
            return {"ok": True}

        client = ProxycurlClient(api_key="secret-key", request_executor=recording_executor)
        client.scrape_person_profile(url="https://linkedin.com/in/test")
        headers = captured.get("headers", {})
        self.assertEqual(headers["Authorization"], "Bearer secret-key")

    def test_timeout_passed_to_executor(self) -> None:
        captured: dict[str, object] = {}

        def recording_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured.update(kwargs)
            return {}

        client = ProxycurlClient(api_key="key", timeout_seconds=30.0, request_executor=recording_executor)
        client.search_jobs(keyword="python")
        self.assertEqual(captured["timeout_seconds"], 30.0)

    def test_no_json_body_sent_on_get(self) -> None:
        captured: dict[str, object] = {}

        def recording_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured.update(kwargs)
            return {}

        client = ProxycurlClient(api_key="key", request_executor=recording_executor)
        client.list_company_employees(url="https://linkedin.com/company/test")
        self.assertIsNone(captured.get("json_body"))

    def test_custom_base_url_used_by_client(self) -> None:
        client = ProxycurlClient(
            api_key="key",
            base_url="https://proxy.example.com",
            request_executor=_fake_executor,
        )
        result = client.scrape_person_profile(url="https://linkedin.com/in/test")
        self.assertTrue(result["url"].startswith("https://proxy.example.com"))

    def test_get_personal_emails_page_size_in_url(self) -> None:
        client = self._client()
        result = client.get_personal_emails(
            linkedin_profile_url="https://linkedin.com/in/test",
            page_size=3,
        )
        self.assertIn("page_size=3", result["url"])

    def test_list_employees_role_search_in_url(self) -> None:
        client = self._client()
        result = client.list_company_employees(
            url="https://linkedin.com/company/acme",
            role_search="engineer",
        )
        self.assertIn("role_search=engineer", result["url"])


if __name__ == "__main__":
    unittest.main()
