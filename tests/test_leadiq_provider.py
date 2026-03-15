"""Tests for the LeadIQ provider client and GraphQL request builders."""

from __future__ import annotations

import unittest

from harnessiq.providers.leadiq import (
    LeadIQClient,
    LeadIQCredentials,
    build_add_tag_to_contact_request,
    build_capture_leads_request,
    build_enrich_contact_request,
    build_find_person_by_linkedin_request,
    build_get_capture_status_request,
    build_get_captures_request,
    build_get_contact_details_request,
    build_get_tags_request,
    build_get_team_activity_request,
    build_remove_tag_from_contact_request,
    build_search_companies_request,
    build_search_contacts_request,
)
from harnessiq.providers.leadiq.api import build_headers


class LeadIQCredentialsTests(unittest.TestCase):
    def test_credentials_type_holds_api_key(self) -> None:
        creds = LeadIQCredentials(api_key="liq_key")
        self.assertEqual(creds["api_key"], "liq_key")


class LeadIQHeaderTests(unittest.TestCase):
    def test_build_headers_uses_basic_auth(self) -> None:
        import base64

        headers = build_headers("liq_key")
        expected = "Basic " + base64.b64encode(b"liq_key:").decode("ascii")
        self.assertEqual(headers["Authorization"], expected)

    def test_build_headers_merges_extra_headers(self) -> None:
        headers = build_headers("liq_key", extra_headers={"X-Custom": "val"})
        self.assertEqual(headers["X-Custom"], "val")
        self.assertIn("Authorization", headers)


class LeadIQRequestBuilderTests(unittest.TestCase):
    def test_build_search_contacts_has_query_and_variables(self) -> None:
        payload = build_search_contacts_request(name="Alice")
        self.assertIn("query", payload)
        self.assertIn("variables", payload)
        self.assertIn("filter", payload["variables"])
        self.assertEqual(payload["variables"]["filter"]["name"], "Alice")

    def test_build_search_contacts_omits_empty_filter_when_no_criteria(self) -> None:
        payload = build_search_contacts_request()
        # No filter key when all criteria are None
        self.assertNotIn("filter", payload["variables"])

    def test_build_search_contacts_pagination(self) -> None:
        payload = build_search_contacts_request(page=2, per_page=10)
        self.assertEqual(payload["variables"]["page"], 2)
        self.assertEqual(payload["variables"]["perPage"], 10)

    def test_build_search_companies_includes_filter(self) -> None:
        payload = build_search_companies_request(name="Acme", domain="acme.com")
        self.assertEqual(payload["variables"]["filter"]["name"], "Acme")
        self.assertEqual(payload["variables"]["filter"]["domain"], "acme.com")

    def test_build_search_companies_employee_count_range(self) -> None:
        payload = build_search_companies_request(
            employee_count_min=50, employee_count_max=500
        )
        self.assertEqual(payload["variables"]["filter"]["employeeCountMin"], 50)
        self.assertEqual(payload["variables"]["filter"]["employeeCountMax"], 500)

    def test_build_find_person_by_linkedin_uses_url_variable(self) -> None:
        payload = build_find_person_by_linkedin_request("https://linkedin.com/in/alice")
        self.assertEqual(payload["variables"]["linkedinUrl"], "https://linkedin.com/in/alice")
        self.assertIn("findPersonByLinkedIn", payload["query"])

    def test_build_enrich_contact_uses_mutation(self) -> None:
        payload = build_enrich_contact_request("c_123")
        self.assertEqual(payload["variables"]["contactId"], "c_123")
        self.assertIn("mutation", payload["query"])
        self.assertIn("enrichContact", payload["query"])

    def test_build_capture_leads_copies_contacts(self) -> None:
        contacts = [{"firstName": "Alice", "email": "a@b.com"}]
        payload = build_capture_leads_request(contacts)
        self.assertEqual(payload["variables"]["contacts"][0]["firstName"], "Alice")
        contacts[0]["firstName"] = "mutated"
        self.assertEqual(payload["variables"]["contacts"][0]["firstName"], "Alice")

    def test_build_get_captures_omits_none_pagination(self) -> None:
        payload = build_get_captures_request()
        self.assertNotIn("page", payload["variables"])

    def test_build_get_captures_includes_pagination(self) -> None:
        payload = build_get_captures_request(page=1, per_page=25)
        self.assertEqual(payload["variables"]["page"], 1)

    def test_build_get_contact_details_uses_contact_id(self) -> None:
        payload = build_get_contact_details_request("c_456")
        self.assertEqual(payload["variables"]["contactId"], "c_456")

    def test_build_get_capture_status_uses_capture_id(self) -> None:
        payload = build_get_capture_status_request("cap_789")
        self.assertEqual(payload["variables"]["captureId"], "cap_789")

    def test_build_get_tags_has_empty_variables(self) -> None:
        payload = build_get_tags_request()
        self.assertEqual(payload["variables"], {})
        self.assertIn("getTags", payload["query"])

    def test_build_add_tag_to_contact(self) -> None:
        payload = build_add_tag_to_contact_request("c_1", "t_1")
        self.assertEqual(payload["variables"]["contactId"], "c_1")
        self.assertEqual(payload["variables"]["tagId"], "t_1")
        self.assertIn("mutation", payload["query"])

    def test_build_remove_tag_from_contact(self) -> None:
        payload = build_remove_tag_from_contact_request("c_1", "t_1")
        self.assertIn("removeTagFromContact", payload["query"])


class LeadIQClientTests(unittest.TestCase):
    def _make_client(self, captured: list[dict]) -> LeadIQClient:
        def fake_executor(method, url, *, headers=None, json_body=None, timeout_seconds=60.0):
            captured.append({"method": method, "url": url, "json_body": json_body, "headers": headers})
            return {"data": {}}

        return LeadIQClient(api_key="liq_key", request_executor=fake_executor)

    def test_client_is_frozen_dataclass(self) -> None:
        client = LeadIQClient(api_key="key")
        with self.assertRaises(Exception):
            client.api_key = "modified"  # type: ignore[misc]

    def test_all_operations_use_post_to_graphql(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.search_contacts(name="Alice")
        client.search_companies(name="Acme")
        client.find_person_by_linkedin("https://linkedin.com/in/alice")
        client.enrich_contact("c_1")
        client.get_tags()
        for call in captured:
            self.assertEqual(call["method"], "POST")
            self.assertIn("/graphql", call["url"])

    def test_search_contacts_sends_correct_query(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.search_contacts(name="Alice", company="Acme")
        body = captured[0]["json_body"]
        self.assertIn("searchContacts", body["query"])
        self.assertEqual(body["variables"]["filter"]["name"], "Alice")

    def test_headers_include_basic_auth(self) -> None:
        import base64

        captured: list[dict] = []
        client = self._make_client(captured)
        client.get_tags()
        expected = "Basic " + base64.b64encode(b"liq_key:").decode("ascii")
        self.assertEqual(captured[0]["headers"]["Authorization"], expected)

    def test_capture_leads_sends_mutation(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.capture_leads([{"firstName": "Alice"}])
        self.assertIn("captureLeads", captured[0]["json_body"]["query"])


if __name__ == "__main__":
    unittest.main()
