"""Tests for the ZoomInfo provider client and request builders."""

from __future__ import annotations

import unittest

from harnessiq.providers.zoominfo import (
    DEFAULT_BASE_URL,
    ZoomInfoClient,
    ZoomInfoCredentials,
    authenticate_url,
    build_authenticate_request,
    build_enrich_company_request,
    build_enrich_contact_request,
    build_enrich_ip_request,
    build_headers,
    build_lookup_outputfields_request,
    build_search_company_request,
    build_search_contact_request,
    build_search_intent_request,
    build_search_news_request,
    build_search_scoop_request,
    enrich_company_url,
    enrich_contact_url,
    lookup_outputfields_url,
    search_company_url,
    search_contact_url,
    search_intent_url,
    usage_url,
)


class ZoomInfoCredentialsTests(unittest.TestCase):
    """Tests for the ZoomInfoCredentials TypedDict."""

    def test_credentials_accepts_username_and_password(self) -> None:
        creds: ZoomInfoCredentials = {"username": "user@example.com", "password": "secret"}
        self.assertEqual(creds["username"], "user@example.com")
        self.assertEqual(creds["password"], "secret")

    def test_credentials_is_typed_dict(self) -> None:
        import typing
        self.assertTrue(issubclass(ZoomInfoCredentials, dict))

    def test_credentials_keys(self) -> None:
        creds: ZoomInfoCredentials = {"username": "u", "password": "p"}
        self.assertIn("username", creds)
        self.assertIn("password", creds)


class ZoomInfoApiHelpersTests(unittest.TestCase):
    """Tests for api.py URL builders and header helpers."""

    def test_default_base_url(self) -> None:
        self.assertEqual(DEFAULT_BASE_URL, "https://api.zoominfo.com")

    def test_build_headers_includes_bearer_token(self) -> None:
        headers = build_headers("my_jwt_token")
        self.assertEqual(headers["Authorization"], "Bearer my_jwt_token")

    def test_build_headers_accepts_extra_headers(self) -> None:
        headers = build_headers("tok", extra_headers={"X-Custom": "val"})
        self.assertEqual(headers["Authorization"], "Bearer tok")
        self.assertEqual(headers["X-Custom"], "val")

    def test_authenticate_url_default(self) -> None:
        self.assertEqual(authenticate_url(), "https://api.zoominfo.com/authenticate")

    def test_authenticate_url_custom_base(self) -> None:
        self.assertEqual(authenticate_url("https://sandbox.zoominfo.com"), "https://sandbox.zoominfo.com/authenticate")

    def test_search_contact_url(self) -> None:
        self.assertEqual(search_contact_url(), "https://api.zoominfo.com/search/contact")

    def test_search_company_url(self) -> None:
        self.assertEqual(search_company_url(), "https://api.zoominfo.com/search/company")

    def test_search_intent_url(self) -> None:
        self.assertEqual(search_intent_url(), "https://api.zoominfo.com/search/intent")

    def test_enrich_contact_url(self) -> None:
        self.assertEqual(enrich_contact_url(), "https://api.zoominfo.com/enrich/contact")

    def test_enrich_company_url(self) -> None:
        self.assertEqual(enrich_company_url(), "https://api.zoominfo.com/enrich/company")

    def test_lookup_outputfields_url(self) -> None:
        self.assertEqual(lookup_outputfields_url(), "https://api.zoominfo.com/lookup/outputfields")

    def test_usage_url(self) -> None:
        self.assertEqual(usage_url(), "https://api.zoominfo.com/usage")


class ZoomInfoRequestBuildersTests(unittest.TestCase):
    """Tests for requests.py payload builders."""

    def test_build_authenticate_request(self) -> None:
        payload = build_authenticate_request("user@example.com", "secret")
        self.assertEqual(payload["username"], "user@example.com")
        self.assertEqual(payload["password"], "secret")

    def test_build_search_contact_request_required_fields(self) -> None:
        payload = build_search_contact_request(
            output_fields=["firstName", "lastName"],
            match_filter={"firstName": "Alice"},
        )
        self.assertEqual(payload["outputFields"], ["firstName", "lastName"])
        self.assertEqual(payload["matchFilter"], {"firstName": "Alice"})
        self.assertNotIn("rpp", payload)
        self.assertNotIn("page", payload)

    def test_build_search_contact_request_with_pagination(self) -> None:
        payload = build_search_contact_request(
            output_fields=["email"],
            match_filter={},
            rpp=10,
            page=2,
        )
        self.assertEqual(payload["rpp"], 10)
        self.assertEqual(payload["page"], 2)

    def test_build_search_company_request(self) -> None:
        payload = build_search_company_request(
            output_fields=["name", "website"],
            match_filter={"name": "Acme"},
            rpp=5,
        )
        self.assertEqual(payload["outputFields"], ["name", "website"])
        self.assertEqual(payload["matchFilter"]["name"], "Acme")
        self.assertEqual(payload["rpp"], 5)
        self.assertNotIn("page", payload)

    def test_build_search_intent_request(self) -> None:
        payload = build_search_intent_request(
            company_ids=[123, 456],
            topics=["cloud computing", "AI"],
        )
        self.assertEqual(payload["companyIds"], [123, 456])
        self.assertEqual(payload["topics"], ["cloud computing", "AI"])
        self.assertNotIn("startDate", payload)

    def test_build_search_intent_request_with_dates(self) -> None:
        payload = build_search_intent_request(
            company_ids=[1],
            topics=["security"],
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
        self.assertEqual(payload["startDate"], "2024-01-01")
        self.assertEqual(payload["endDate"], "2024-12-31")

    def test_build_enrich_contact_request(self) -> None:
        payload = build_enrich_contact_request(
            match_input=[{"emailAddress": "alice@example.com"}],
            output_fields=["firstName", "lastName"],
        )
        self.assertEqual(payload["matchInput"], [{"emailAddress": "alice@example.com"}])
        self.assertEqual(payload["outputFields"], ["firstName", "lastName"])

    def test_build_enrich_contact_request_no_output_fields(self) -> None:
        payload = build_enrich_contact_request(
            match_input=[{"emailAddress": "bob@example.com"}],
        )
        self.assertNotIn("outputFields", payload)

    def test_build_enrich_company_request(self) -> None:
        payload = build_enrich_company_request(
            match_input=[{"name": "Acme Corp", "website": "acme.com"}],
        )
        self.assertEqual(payload["matchInput"][0]["name"], "Acme Corp")

    def test_build_enrich_ip_request(self) -> None:
        payload = build_enrich_ip_request("192.168.1.1", output_fields=["company"])
        self.assertEqual(payload["ipAddress"], "192.168.1.1")
        self.assertEqual(payload["outputFields"], ["company"])

    def test_build_lookup_outputfields_request(self) -> None:
        payload = build_lookup_outputfields_request("contact")
        self.assertEqual(payload["entity"], "contact")

    def test_build_search_news_request_empty(self) -> None:
        payload = build_search_news_request()
        self.assertIsInstance(payload, dict)

    def test_build_search_scoop_request_with_filter(self) -> None:
        payload = build_search_scoop_request(match_filter={"type": "hiring"}, rpp=20)
        self.assertEqual(payload["matchFilter"]["type"], "hiring")
        self.assertEqual(payload["rpp"], 20)


class ZoomInfoClientTests(unittest.TestCase):
    """Tests for the ZoomInfoClient dataclass."""

    def _make_client(self, captured: list[dict], jwt_result: str = "test_jwt") -> ZoomInfoClient:
        def fake_executor(
            method: str,
            url: str,
            *,
            headers=None,
            json_body=None,
            timeout_seconds: float = 60.0,
        ):
            captured.append({"method": method, "url": url, "headers": headers, "json_body": json_body})
            if "/authenticate" in url:
                return {"jwt": jwt_result}
            return {"data": []}

        return ZoomInfoClient(
            username="user@example.com",
            password="pass123",
            request_executor=fake_executor,
        )

    def test_client_is_frozen_dataclass(self) -> None:
        import dataclasses
        self.assertTrue(dataclasses.is_dataclass(ZoomInfoClient))
        fields = {f.name for f in dataclasses.fields(ZoomInfoClient)}
        self.assertIn("username", fields)
        self.assertIn("password", fields)

    def test_authenticate_posts_to_authenticate_endpoint(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        jwt = client.authenticate()

        self.assertEqual(jwt, "test_jwt")
        self.assertEqual(len(captured), 1)
        call = captured[0]
        self.assertEqual(call["method"], "POST")
        self.assertEqual(call["url"], "https://api.zoominfo.com/authenticate")
        self.assertEqual(call["json_body"]["username"], "user@example.com")
        self.assertEqual(call["json_body"]["password"], "pass123")

    def test_authenticate_returns_jwt_string(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured, jwt_result="real_jwt_abc123")
        result = client.authenticate()
        self.assertEqual(result, "real_jwt_abc123")

    def test_search_contacts_posts_to_correct_url(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.search_contacts(
            "my_jwt",
            output_fields=["firstName", "email"],
            match_filter={"firstName": "Alice"},
        )
        call = captured[0]
        self.assertEqual(call["method"], "POST")
        self.assertEqual(call["url"], "https://api.zoominfo.com/search/contact")

    def test_search_contacts_sends_bearer_auth(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.search_contacts(
            "my_jwt",
            output_fields=["firstName"],
            match_filter={},
        )
        self.assertEqual(captured[0]["headers"]["Authorization"], "Bearer my_jwt")

    def test_search_contacts_passes_output_fields_and_filter(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.search_contacts(
            "tok",
            output_fields=["firstName", "lastName"],
            match_filter={"companyName": "Acme"},
            rpp=10,
            page=3,
        )
        body = captured[0]["json_body"]
        self.assertEqual(body["outputFields"], ["firstName", "lastName"])
        self.assertEqual(body["matchFilter"]["companyName"], "Acme")
        self.assertEqual(body["rpp"], 10)
        self.assertEqual(body["page"], 3)

    def test_search_companies_posts_to_correct_url(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.search_companies(
            "tok",
            output_fields=["name"],
            match_filter={"name": "Acme"},
        )
        self.assertEqual(captured[0]["url"], "https://api.zoominfo.com/search/company")

    def test_search_intent_posts_to_correct_url(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.search_intent(
            "tok",
            company_ids=[1, 2],
            topics=["cloud"],
        )
        call = captured[0]
        self.assertEqual(call["method"], "POST")
        self.assertEqual(call["url"], "https://api.zoominfo.com/search/intent")

    def test_search_intent_payload_structure(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.search_intent("tok", company_ids=[10, 20], topics=["AI", "ML"])
        body = captured[0]["json_body"]
        self.assertEqual(body["companyIds"], [10, 20])
        self.assertEqual(body["topics"], ["AI", "ML"])

    def test_enrich_contact_posts_to_correct_url(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.enrich_contact(
            "tok",
            match_input=[{"emailAddress": "a@b.com"}],
        )
        self.assertEqual(captured[0]["url"], "https://api.zoominfo.com/enrich/contact")
        self.assertEqual(captured[0]["method"], "POST")

    def test_enrich_company_posts_to_correct_url(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.enrich_company(
            "tok",
            match_input=[{"name": "Acme", "website": "acme.com"}],
        )
        self.assertEqual(captured[0]["url"], "https://api.zoominfo.com/enrich/company")

    def test_enrich_ip_posts_with_ip_address(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.enrich_ip("tok", "8.8.8.8")
        self.assertEqual(captured[0]["url"], "https://api.zoominfo.com/enrich/ip")
        self.assertEqual(captured[0]["json_body"]["ipAddress"], "8.8.8.8")

    def test_lookup_output_fields_sends_get(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.lookup_output_fields("tok", "contact")
        call = captured[0]
        self.assertEqual(call["method"], "GET")
        self.assertEqual(call["url"], "https://api.zoominfo.com/lookup/outputfields")
        self.assertEqual(call["json_body"]["entity"], "contact")

    def test_get_usage_sends_get_to_usage_url(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.get_usage("tok")
        self.assertEqual(captured[0]["method"], "GET")
        self.assertEqual(captured[0]["url"], "https://api.zoominfo.com/usage")
        self.assertIsNone(captured[0]["json_body"])

    def test_client_custom_base_url(self) -> None:
        captured: list[dict] = []

        def fake_executor(method, url, *, headers=None, json_body=None, timeout_seconds=60.0):
            captured.append({"method": method, "url": url})
            if "/authenticate" in url:
                return {"jwt": "tok"}
            return {}

        client = ZoomInfoClient(
            username="u",
            password="p",
            base_url="https://sandbox.zoominfo.com",
            request_executor=fake_executor,
        )
        client.get_usage("tok")
        self.assertEqual(captured[0]["url"], "https://sandbox.zoominfo.com/usage")

    def test_client_respects_timeout_seconds(self) -> None:
        timeouts_seen: list[float] = []

        def fake_executor(method, url, *, headers=None, json_body=None, timeout_seconds=60.0):
            timeouts_seen.append(timeout_seconds)
            if "/authenticate" in url:
                return {"jwt": "tok"}
            return {}

        client = ZoomInfoClient(
            username="u",
            password="p",
            timeout_seconds=15.0,
            request_executor=fake_executor,
        )
        client.authenticate()
        self.assertEqual(timeouts_seen[0], 15.0)

    def test_search_news_posts_to_news_url(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.search_news("tok", match_filter={"type": "funding"}, rpp=5)
        self.assertEqual(captured[0]["url"], "https://api.zoominfo.com/search/news")
        self.assertEqual(captured[0]["method"], "POST")

    def test_search_scoops_posts_to_scoop_url(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.search_scoops("tok", rpp=10)
        self.assertEqual(captured[0]["url"], "https://api.zoominfo.com/search/scoop")

    def test_bulk_enrich_contacts_posts_to_bulk_contact_url(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.bulk_enrich_contacts("tok", match_input=[{"emailAddress": "x@y.com"}])
        self.assertEqual(captured[0]["url"], "https://api.zoominfo.com/bulk/contact")
        self.assertEqual(captured[0]["method"], "POST")

    def test_bulk_enrich_companies_posts_to_bulk_company_url(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.bulk_enrich_companies("tok", match_input=[{"name": "Corp"}])
        self.assertEqual(captured[0]["url"], "https://api.zoominfo.com/bulk/company")


if __name__ == "__main__":
    unittest.main()
