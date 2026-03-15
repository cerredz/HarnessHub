"""Tests for the Salesforge provider client and request builders."""

from __future__ import annotations

import unittest

from harnessiq.providers.salesforge import (
    SalesforgeClient,
    SalesforgeCredentials,
    build_add_contacts_to_sequence_request,
    build_add_unsubscribe_request,
    build_create_contact_request,
    build_create_sequence_request,
    build_remove_unsubscribe_request,
    build_update_contact_request,
    build_update_sequence_request,
)
from harnessiq.providers.salesforge.api import (
    build_headers,
    contact_activity_url,
    contact_url,
    contacts_url,
    mailbox_url,
    mailboxes_url,
    sequence_contact_url,
    sequence_contacts_url,
    sequence_pause_url,
    sequence_resume_url,
    sequence_stats_url,
    sequence_url,
    sequences_url,
    unsubscribe_url,
)


class SalesforgeCredentialsTests(unittest.TestCase):
    def test_credentials_type_holds_api_key(self) -> None:
        creds = SalesforgeCredentials(api_key="sf_key")
        self.assertEqual(creds["api_key"], "sf_key")


class SalesforgeHeaderTests(unittest.TestCase):
    def test_build_headers_uses_bearer_auth(self) -> None:
        headers = build_headers("sf_key")
        self.assertEqual(headers["Authorization"], "Bearer sf_key")

    def test_build_headers_merges_extra_headers(self) -> None:
        headers = build_headers("sf_key", extra_headers={"X-Custom": "val"})
        self.assertEqual(headers["X-Custom"], "val")
        self.assertIn("Authorization", headers)


class SalesforgeURLTests(unittest.TestCase):
    BASE = "https://api.salesforge.ai"

    def test_sequences_url(self) -> None:
        self.assertEqual(sequences_url(), f"{self.BASE}/public/api/v1/sequence")

    def test_sequence_url(self) -> None:
        self.assertEqual(sequence_url("seq_1"), f"{self.BASE}/public/api/v1/sequence/seq_1")

    def test_sequence_pause_url(self) -> None:
        self.assertIn("/pause", sequence_pause_url("seq_1"))

    def test_sequence_resume_url(self) -> None:
        self.assertIn("/resume", sequence_resume_url("seq_1"))

    def test_sequence_stats_url(self) -> None:
        self.assertIn("/stats", sequence_stats_url("seq_1"))

    def test_sequence_contacts_url(self) -> None:
        self.assertIn("/contact", sequence_contacts_url("seq_1"))

    def test_sequence_contact_url(self) -> None:
        url = sequence_contact_url("seq_1", "c_1")
        self.assertIn("seq_1", url)
        self.assertIn("c_1", url)

    def test_contacts_url(self) -> None:
        self.assertEqual(contacts_url(), f"{self.BASE}/public/api/v1/contact")

    def test_contact_url(self) -> None:
        self.assertIn("c_42", contact_url("c_42"))

    def test_contact_activity_url(self) -> None:
        self.assertIn("/activity", contact_activity_url("c_42"))

    def test_mailboxes_url(self) -> None:
        self.assertEqual(mailboxes_url(), f"{self.BASE}/public/api/v1/mailbox")

    def test_mailbox_url(self) -> None:
        self.assertIn("mb_1", mailbox_url("mb_1"))

    def test_unsubscribe_url(self) -> None:
        self.assertEqual(unsubscribe_url(), f"{self.BASE}/public/api/v1/unsubscribe")


class SalesforgeRequestBuilderTests(unittest.TestCase):
    def test_create_sequence_required_fields(self) -> None:
        payload = build_create_sequence_request(name="My Sequence", mailbox_id="mb_1")
        self.assertEqual(payload["name"], "My Sequence")
        self.assertEqual(payload["mailboxId"], "mb_1")

    def test_create_sequence_omits_optional_none(self) -> None:
        payload = build_create_sequence_request(name="Seq", mailbox_id="mb_1")
        self.assertNotIn("dailyLimit", payload)
        self.assertNotIn("timezone", payload)
        self.assertNotIn("trackOpen", payload)

    def test_create_sequence_includes_optional_fields(self) -> None:
        payload = build_create_sequence_request(
            name="Seq",
            mailbox_id="mb_1",
            daily_limit=50,
            timezone="UTC",
            track_open=True,
            track_click=False,
            stop_on_auto_reply=True,
        )
        self.assertEqual(payload["dailyLimit"], 50)
        self.assertEqual(payload["timezone"], "UTC")
        self.assertTrue(payload["trackOpen"])
        self.assertFalse(payload["trackClick"])
        self.assertTrue(payload["stopOnAutoReply"])

    def test_update_sequence_omits_all_none(self) -> None:
        payload = build_update_sequence_request()
        self.assertEqual(len(payload), 0)

    def test_update_sequence_partial_fields(self) -> None:
        payload = build_update_sequence_request(name="Updated", daily_limit=100)
        self.assertEqual(payload["name"], "Updated")
        self.assertEqual(payload["dailyLimit"], 100)
        self.assertNotIn("timezone", payload)

    def test_add_contacts_to_sequence_copies_list(self) -> None:
        contacts = [{"email": "a@b.com"}]
        payload = build_add_contacts_to_sequence_request(contacts)
        self.assertEqual(payload["contacts"][0]["email"], "a@b.com")
        contacts[0]["email"] = "mutated"
        self.assertEqual(payload["contacts"][0]["email"], "a@b.com")

    def test_create_contact_required_fields(self) -> None:
        payload = build_create_contact_request(
            first_name="Alice", last_name="Smith", email="alice@example.com"
        )
        self.assertEqual(payload["firstName"], "Alice")
        self.assertEqual(payload["lastName"], "Smith")
        self.assertEqual(payload["email"], "alice@example.com")

    def test_create_contact_omits_optional_none(self) -> None:
        payload = build_create_contact_request(
            first_name="Alice", last_name="Smith", email="alice@example.com"
        )
        self.assertNotIn("companyName", payload)
        self.assertNotIn("title", payload)
        self.assertNotIn("linkedinUrl", payload)
        self.assertNotIn("phone", payload)
        self.assertNotIn("customFields", payload)

    def test_create_contact_includes_all_optional(self) -> None:
        payload = build_create_contact_request(
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
            company_name="Acme",
            title="VP",
            linkedin_url="https://linkedin.com/in/alice",
            phone="+1234567890",
            custom_fields={"key": "val"},
        )
        self.assertEqual(payload["companyName"], "Acme")
        self.assertEqual(payload["title"], "VP")
        self.assertEqual(payload["linkedinUrl"], "https://linkedin.com/in/alice")
        self.assertEqual(payload["phone"], "+1234567890")
        self.assertEqual(payload["customFields"], {"key": "val"})

    def test_update_contact_omits_all_none(self) -> None:
        payload = build_update_contact_request()
        self.assertEqual(len(payload), 0)

    def test_update_contact_partial(self) -> None:
        payload = build_update_contact_request(email="new@example.com", title="CEO")
        self.assertEqual(payload["email"], "new@example.com")
        self.assertEqual(payload["title"], "CEO")
        self.assertNotIn("firstName", payload)

    def test_add_unsubscribe_request(self) -> None:
        payload = build_add_unsubscribe_request("unsub@example.com")
        self.assertEqual(payload["email"], "unsub@example.com")

    def test_remove_unsubscribe_request(self) -> None:
        payload = build_remove_unsubscribe_request("unsub@example.com")
        self.assertEqual(payload["email"], "unsub@example.com")


class SalesforgeClientTests(unittest.TestCase):
    def _make_client(self, captured: list[dict]) -> SalesforgeClient:
        def fake_executor(method, url, *, headers=None, json_body=None, timeout_seconds=60.0):
            captured.append({"method": method, "url": url, "json_body": json_body, "headers": headers})
            return {"data": {}}

        return SalesforgeClient(api_key="sf_key", request_executor=fake_executor)

    def test_client_is_frozen_dataclass(self) -> None:
        client = SalesforgeClient(api_key="key")
        with self.assertRaises(Exception):
            client.api_key = "modified"  # type: ignore[misc]

    def test_list_sequences_uses_get(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.list_sequences()
        self.assertEqual(captured[0]["method"], "GET")
        self.assertIn("/sequence", captured[0]["url"])

    def test_create_sequence_uses_post(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.create_sequence(name="Test Seq", mailbox_id="mb_1")
        self.assertEqual(captured[0]["method"], "POST")
        self.assertEqual(captured[0]["json_body"]["name"], "Test Seq")

    def test_get_sequence_uses_get_with_id(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.get_sequence("seq_42")
        self.assertEqual(captured[0]["method"], "GET")
        self.assertIn("seq_42", captured[0]["url"])

    def test_update_sequence_uses_patch(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.update_sequence("seq_1", name="Updated")
        self.assertEqual(captured[0]["method"], "PATCH")
        self.assertIn("seq_1", captured[0]["url"])

    def test_delete_sequence_uses_delete(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.delete_sequence("seq_1")
        self.assertEqual(captured[0]["method"], "DELETE")

    def test_pause_sequence_uses_post(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.pause_sequence("seq_1")
        self.assertEqual(captured[0]["method"], "POST")
        self.assertIn("pause", captured[0]["url"])

    def test_resume_sequence_uses_post(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.resume_sequence("seq_1")
        self.assertIn("resume", captured[0]["url"])

    def test_get_sequence_stats_uses_get(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.get_sequence_stats("seq_1")
        self.assertIn("stats", captured[0]["url"])

    def test_add_contacts_to_sequence_uses_post(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.add_contacts_to_sequence("seq_1", [{"email": "a@b.com"}])
        self.assertEqual(captured[0]["method"], "POST")
        self.assertIn("seq_1", captured[0]["url"])

    def test_list_sequence_contacts_uses_get(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.list_sequence_contacts("seq_1")
        self.assertEqual(captured[0]["method"], "GET")

    def test_remove_contact_from_sequence_uses_delete(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.remove_contact_from_sequence("seq_1", "c_1")
        self.assertEqual(captured[0]["method"], "DELETE")
        self.assertIn("c_1", captured[0]["url"])

    def test_list_contacts_uses_get(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.list_contacts()
        self.assertEqual(captured[0]["method"], "GET")
        self.assertIn("/contact", captured[0]["url"])

    def test_create_contact_uses_post(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.create_contact(first_name="Alice", last_name="Smith", email="alice@ex.com")
        self.assertEqual(captured[0]["method"], "POST")
        self.assertEqual(captured[0]["json_body"]["firstName"], "Alice")

    def test_get_contact_uses_get_with_id(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.get_contact("c_99")
        self.assertIn("c_99", captured[0]["url"])

    def test_update_contact_uses_patch(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.update_contact("c_1", title="CTO")
        self.assertEqual(captured[0]["method"], "PATCH")

    def test_delete_contact_uses_delete(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.delete_contact("c_1")
        self.assertEqual(captured[0]["method"], "DELETE")

    def test_get_contact_activity_uses_get(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.get_contact_activity("c_1")
        self.assertIn("activity", captured[0]["url"])

    def test_list_mailboxes_uses_get(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.list_mailboxes()
        self.assertIn("/mailbox", captured[0]["url"])

    def test_get_mailbox_uses_get_with_id(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.get_mailbox("mb_5")
        self.assertIn("mb_5", captured[0]["url"])

    def test_list_unsubscribed_uses_get(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.list_unsubscribed()
        self.assertIn("/unsubscribe", captured[0]["url"])

    def test_add_unsubscribe_uses_post(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.add_unsubscribe("unsub@example.com")
        self.assertEqual(captured[0]["method"], "POST")
        self.assertEqual(captured[0]["json_body"]["email"], "unsub@example.com")

    def test_remove_unsubscribe_uses_delete(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.remove_unsubscribe("unsub@example.com")
        self.assertEqual(captured[0]["method"], "DELETE")
        self.assertEqual(captured[0]["json_body"]["email"], "unsub@example.com")

    def test_headers_include_bearer_auth(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.list_sequences()
        self.assertEqual(captured[0]["headers"]["Authorization"], "Bearer sf_key")

    def test_custom_base_url_is_used(self) -> None:
        captured: list[dict] = []

        def fake_executor(method, url, *, headers=None, json_body=None, timeout_seconds=60.0):
            captured.append({"url": url})
            return {}

        client = SalesforgeClient(api_key="key", base_url="https://custom.example.com", request_executor=fake_executor)
        client.list_sequences()
        self.assertIn("custom.example.com", captured[0]["url"])


if __name__ == "__main__":
    unittest.main()
