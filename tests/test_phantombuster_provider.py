"""Tests for the PhantomBuster provider client and request builders."""

from __future__ import annotations

import unittest

from harnessiq.providers.phantombuster import (
    PhantomBusterClient,
    PhantomBusterCredentials,
    build_abort_agent_request,
    build_delete_agent_request,
    build_fetch_phantom_request,
    build_launch_agent_request,
    build_save_agent_argument_request,
)
from harnessiq.providers.phantombuster.api import (
    agent_fetch_output_url,
    agent_fetch_url,
    agents_abort_url,
    agents_delete_url,
    agents_fetch_all_url,
    agents_launch_url,
    agents_save_argument_url,
    build_headers,
    container_fetch_url,
    containers_fetch_all_url,
    org_members_url,
    phantoms_fetch_all_url,
    phantoms_fetch_url,
    script_fetch_url,
    scripts_fetch_all_url,
    user_me_url,
)


class PhantomBusterCredentialsTests(unittest.TestCase):
    def test_credentials_holds_api_key(self) -> None:
        creds = PhantomBusterCredentials(api_key="pb_key")
        self.assertEqual(creds["api_key"], "pb_key")


class PhantomBusterHeaderTests(unittest.TestCase):
    def test_build_headers_uses_x_phantombuster_key(self) -> None:
        headers = build_headers("pb_key")
        self.assertEqual(headers["X-Phantombuster-Key"], "pb_key")

    def test_build_headers_merges_extra_headers(self) -> None:
        headers = build_headers("pb_key", extra_headers={"X-Custom": "val"})
        self.assertEqual(headers["X-Custom"], "val")
        self.assertIn("X-Phantombuster-Key", headers)


class PhantomBusterURLTests(unittest.TestCase):
    BASE = "https://api.phantombuster.com"

    def test_agent_fetch_url_includes_id(self) -> None:
        url = agent_fetch_url("agent_1")
        self.assertIn("id=agent_1", url)
        self.assertIn("/agents/fetch", url)

    def test_agents_fetch_all_url(self) -> None:
        url = agents_fetch_all_url()
        self.assertIn("/agents/fetch-all", url)

    def test_agents_launch_url(self) -> None:
        self.assertIn("/agents/launch", agents_launch_url())

    def test_agents_abort_url(self) -> None:
        self.assertIn("/agents/abort", agents_abort_url())

    def test_agents_delete_url(self) -> None:
        self.assertIn("/agents/delete", agents_delete_url())

    def test_agent_fetch_output_url_includes_id_and_with_output(self) -> None:
        url = agent_fetch_output_url("a_1")
        self.assertIn("id=a_1", url)
        self.assertIn("withOutput=true", url)

    def test_agent_fetch_output_url_with_mode(self) -> None:
        url = agent_fetch_output_url("a_1", mode="json")
        self.assertIn("mode=json", url)

    def test_agents_save_argument_url(self) -> None:
        self.assertIn("save-agent-argument", agents_save_argument_url())

    def test_container_fetch_url_includes_id(self) -> None:
        url = container_fetch_url("c_1")
        self.assertIn("id=c_1", url)

    def test_containers_fetch_all_url_includes_agent_id(self) -> None:
        url = containers_fetch_all_url("agent_1")
        self.assertIn("agentId=agent_1", url)

    def test_containers_fetch_all_url_with_status(self) -> None:
        url = containers_fetch_all_url("agent_1", status="finished")
        self.assertIn("status=finished", url)

    def test_phantoms_fetch_url(self) -> None:
        self.assertIn("/phantoms/fetch", phantoms_fetch_url())

    def test_phantoms_fetch_all_url(self) -> None:
        self.assertIn("/phantoms/fetch-all", phantoms_fetch_all_url())

    def test_user_me_url(self) -> None:
        self.assertIn("/user/me", user_me_url())

    def test_org_members_url(self) -> None:
        self.assertIn("/orgs/fetch-members", org_members_url())

    def test_scripts_fetch_all_url(self) -> None:
        self.assertIn("/scripts/fetch-all", scripts_fetch_all_url())

    def test_script_fetch_url_includes_id(self) -> None:
        url = script_fetch_url("s_1")
        self.assertIn("id=s_1", url)


class PhantomBusterRequestBuilderTests(unittest.TestCase):
    def test_launch_agent_required_id(self) -> None:
        payload = build_launch_agent_request("a_1")
        self.assertEqual(payload["id"], "a_1")

    def test_launch_agent_omits_optional_none(self) -> None:
        payload = build_launch_agent_request("a_1")
        self.assertNotIn("output", payload)
        self.assertNotIn("arguments", payload)
        self.assertNotIn("manualLaunch", payload)

    def test_launch_agent_includes_optional_fields(self) -> None:
        payload = build_launch_agent_request(
            "a_1",
            output="result_object",
            arguments={"key": "val"},
            manual_launch=True,
        )
        self.assertEqual(payload["output"], "result_object")
        self.assertEqual(payload["arguments"]["key"], "val")
        self.assertTrue(payload["manualLaunch"])

    def test_launch_agent_copies_arguments(self) -> None:
        args = {"key": "val"}
        payload = build_launch_agent_request("a_1", arguments=args)
        args["key"] = "mutated"
        self.assertEqual(payload["arguments"]["key"], "val")

    def test_abort_agent_request(self) -> None:
        payload = build_abort_agent_request("a_1")
        self.assertEqual(payload["id"], "a_1")

    def test_delete_agent_request(self) -> None:
        payload = build_delete_agent_request("a_1")
        self.assertEqual(payload["id"], "a_1")

    def test_save_agent_argument_copies_argument(self) -> None:
        arg = {"key": "val"}
        payload = build_save_agent_argument_request("a_1", arg)
        arg["key"] = "mutated"
        self.assertEqual(payload["argument"]["key"], "val")
        self.assertEqual(payload["id"], "a_1")

    def test_fetch_phantom_request(self) -> None:
        payload = build_fetch_phantom_request("ph_1")
        self.assertEqual(payload["id"], "ph_1")


class PhantomBusterClientTests(unittest.TestCase):
    def _make_client(self, captured: list[dict]) -> PhantomBusterClient:
        def fake_executor(method, url, *, headers=None, json_body=None, timeout_seconds=60.0):
            captured.append({"method": method, "url": url, "json_body": json_body, "headers": headers})
            return {}

        return PhantomBusterClient(api_key="pb_key", request_executor=fake_executor)

    def test_client_is_frozen_dataclass(self) -> None:
        client = PhantomBusterClient(api_key="key")
        with self.assertRaises(Exception):
            client.api_key = "modified"  # type: ignore[misc]

    def test_get_agent_uses_get(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.get_agent("a_1")
        self.assertEqual(captured[0]["method"], "GET")
        self.assertIn("id=a_1", captured[0]["url"])

    def test_list_agents_uses_get(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.list_agents()
        self.assertEqual(captured[0]["method"], "GET")
        self.assertIn("fetch-all", captured[0]["url"])

    def test_launch_agent_uses_post(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.launch_agent("a_1")
        self.assertEqual(captured[0]["method"], "POST")
        self.assertEqual(captured[0]["json_body"]["id"], "a_1")

    def test_abort_agent_uses_post(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.abort_agent("a_1")
        self.assertEqual(captured[0]["method"], "POST")
        self.assertIn("abort", captured[0]["url"])

    def test_delete_agent_uses_delete(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.delete_agent("a_1")
        self.assertEqual(captured[0]["method"], "DELETE")

    def test_fetch_agent_output_uses_get(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.fetch_agent_output("a_1", mode="json")
        self.assertEqual(captured[0]["method"], "GET")
        self.assertIn("withOutput=true", captured[0]["url"])

    def test_save_agent_argument_uses_post(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.save_agent_argument("a_1", {"key": "val"})
        self.assertEqual(captured[0]["method"], "POST")

    def test_get_container_uses_get(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.get_container("c_1")
        self.assertEqual(captured[0]["method"], "GET")
        self.assertIn("id=c_1", captured[0]["url"])

    def test_list_containers_uses_get_with_agent_id(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.list_containers("a_1", status="finished")
        self.assertIn("agentId=a_1", captured[0]["url"])
        self.assertIn("status=finished", captured[0]["url"])

    def test_get_phantom_uses_post(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.get_phantom("ph_1")
        self.assertEqual(captured[0]["method"], "POST")
        self.assertEqual(captured[0]["json_body"]["id"], "ph_1")

    def test_list_phantoms_uses_get(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.list_phantoms()
        self.assertEqual(captured[0]["method"], "GET")
        self.assertIn("fetch-all", captured[0]["url"])

    def test_get_user_info_uses_get(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.get_user_info()
        self.assertIn("/user/me", captured[0]["url"])

    def test_list_org_members_uses_get(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.list_org_members()
        self.assertIn("fetch-members", captured[0]["url"])

    def test_list_scripts_uses_get(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.list_scripts()
        self.assertIn("scripts/fetch-all", captured[0]["url"])

    def test_get_script_uses_get_with_id(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.get_script("s_1")
        self.assertIn("id=s_1", captured[0]["url"])

    def test_headers_include_x_phantombuster_key(self) -> None:
        captured: list[dict] = []
        client = self._make_client(captured)
        client.list_agents()
        self.assertEqual(captured[0]["headers"]["X-Phantombuster-Key"], "pb_key")

    def test_custom_base_url_is_used(self) -> None:
        captured: list[dict] = []

        def fake_executor(method, url, *, headers=None, json_body=None, timeout_seconds=60.0):
            captured.append({"url": url})
            return {}

        client = PhantomBusterClient(
            api_key="key",
            base_url="https://custom.example.com",
            request_executor=fake_executor,
        )
        client.list_agents()
        self.assertIn("custom.example.com", captured[0]["url"])


if __name__ == "__main__":
    unittest.main()
