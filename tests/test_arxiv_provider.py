"""Tests for the arXiv provider layer.

Covers ``ArxivConfig``, ``ArxivClient``, ``parse_arxiv_feed``,
``parse_arxiv_entry``, URL builders, and the operation catalog.
Tool factory and registry integration tests are added in the
registration ticket (issue-141).
"""

from __future__ import annotations

import os
import tempfile
import unittest
from typing import Any
from unittest.mock import patch

from harnessiq.providers.arxiv.api import (
    _extract_arxiv_id,
    get_paper_url,
    parse_arxiv_entry,
    parse_arxiv_feed,
    pdf_url,
    search_url,
)
from harnessiq.providers.arxiv.client import ArxivClient, ArxivConfig
from harnessiq.providers.arxiv.operations import (
    build_arxiv_operation_catalog,
    get_arxiv_operation,
)
from harnessiq.shared.dtos import ProviderPayloadRequestDTO

# ---------------------------------------------------------------------------
# Shared fixture data
# ---------------------------------------------------------------------------

_SAMPLE_ATOM = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2301.12345v1</id>
    <title>Attention Is All You Need</title>
    <summary>  A landmark transformer paper.  </summary>
    <published>2017-06-12T00:00:00Z</published>
    <updated>2017-06-12T00:00:00Z</updated>
    <author><name>Ashish Vaswani</name></author>
    <author><name>Noam Shazeer</name></author>
    <category term="cs.LG" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cs.CL" scheme="http://arxiv.org/schemas/atom"/>
    <arxiv:primary_category term="cs.LG"
      scheme="http://arxiv.org/schemas/atom"/>
    <link rel="alternate" href="https://arxiv.org/abs/2301.12345"
      type="text/html"/>
    <link rel="related" href="https://arxiv.org/pdf/2301.12345"
      type="application/pdf" title="pdf"/>
  </entry>
</feed>"""

_EMPTY_ATOM = '<feed xmlns="http://www.w3.org/2005/Atom"></feed>'

_MULTI_ENTRY_ATOM = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v5</id>
    <title>Paper One</title>
    <summary>First paper.</summary>
    <published>2017-06-12T00:00:00Z</published>
    <updated>2017-06-12T00:00:00Z</updated>
    <author><name>Author A</name></author>
    <category term="cs.LG" scheme="http://arxiv.org/schemas/atom"/>
    <arxiv:primary_category term="cs.LG"
      scheme="http://arxiv.org/schemas/atom"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/1810.04805v2</id>
    <title>Paper Two</title>
    <summary>Second paper.</summary>
    <published>2018-10-11T00:00:00Z</published>
    <updated>2018-10-11T00:00:00Z</updated>
    <author><name>Author B</name></author>
    <category term="cs.CL" scheme="http://arxiv.org/schemas/atom"/>
    <arxiv:primary_category term="cs.CL"
      scheme="http://arxiv.org/schemas/atom"/>
  </entry>
</feed>"""


# ---------------------------------------------------------------------------
# ArxivConfigTests
# ---------------------------------------------------------------------------


class ArxivConfigTests(unittest.TestCase):
    def test_default_construction_succeeds(self) -> None:
        c = ArxivConfig()
        self.assertEqual(c.base_url, "https://export.arxiv.org")
        self.assertEqual(c.timeout_seconds, 30.0)
        self.assertEqual(c.delay_seconds, 0.0)

    def test_custom_values_accepted(self) -> None:
        c = ArxivConfig(
            base_url="https://custom.arxiv.org",
            timeout_seconds=15.0,
            delay_seconds=3.0,
        )
        self.assertEqual(c.base_url, "https://custom.arxiv.org")
        self.assertEqual(c.timeout_seconds, 15.0)
        self.assertEqual(c.delay_seconds, 3.0)

    def test_blank_base_url_raises(self) -> None:
        with self.assertRaises(ValueError, msg="blank base_url"):
            ArxivConfig(base_url="")

    def test_whitespace_base_url_raises(self) -> None:
        with self.assertRaises(ValueError, msg="whitespace base_url"):
            ArxivConfig(base_url="   ")

    def test_zero_timeout_raises(self) -> None:
        with self.assertRaises(ValueError):
            ArxivConfig(timeout_seconds=0.0)

    def test_negative_timeout_raises(self) -> None:
        with self.assertRaises(ValueError):
            ArxivConfig(timeout_seconds=-1.0)

    def test_negative_delay_raises(self) -> None:
        with self.assertRaises(ValueError):
            ArxivConfig(delay_seconds=-0.1)

    def test_zero_delay_accepted(self) -> None:
        c = ArxivConfig(delay_seconds=0.0)
        self.assertEqual(c.delay_seconds, 0.0)

    def test_config_is_frozen(self) -> None:
        c = ArxivConfig()
        with self.assertRaises((AttributeError, TypeError)):
            c.timeout_seconds = 99.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ArxivApiTests
# ---------------------------------------------------------------------------


class ArxivApiTests(unittest.TestCase):
    def test_search_url_contains_query(self) -> None:
        url = search_url(
            "https://export.arxiv.org",
            query="ti:attention",
            max_results=10,
            start=0,
            sort_by="relevance",
            sort_order="descending",
        )
        self.assertIn("search_query=ti%3Aattention", url)
        self.assertIn("max_results=10", url)
        self.assertIn("sortBy=relevance", url)
        self.assertIn("sortOrder=descending", url)
        self.assertIn("start=0", url)

    def test_search_url_pagination(self) -> None:
        url = search_url(
            "https://export.arxiv.org",
            query="all:transformer",
            max_results=50,
            start=100,
            sort_by="submittedDate",
            sort_order="ascending",
        )
        self.assertIn("start=100", url)
        self.assertIn("max_results=50", url)
        self.assertIn("sortBy=submittedDate", url)
        self.assertIn("sortOrder=ascending", url)

    def test_search_url_base_trailing_slash_stripped(self) -> None:
        url = search_url(
            "https://export.arxiv.org/",
            query="au:hinton",
            max_results=5,
            start=0,
            sort_by="relevance",
            sort_order="descending",
        )
        self.assertFalse(url.startswith("https://export.arxiv.org//"))

    def test_get_paper_url_contains_id(self) -> None:
        url = get_paper_url("https://export.arxiv.org", "2301.12345")
        self.assertIn("id%3A2301.12345", url)
        self.assertIn("max_results=1", url)

    def test_pdf_url_format(self) -> None:
        self.assertEqual(pdf_url("2301.12345"), "https://arxiv.org/pdf/2301.12345")

    def test_pdf_url_old_style_id(self) -> None:
        self.assertEqual(
            pdf_url("hep-ph/9901257"), "https://arxiv.org/pdf/hep-ph/9901257"
        )

    def test_extract_arxiv_id_strips_version(self) -> None:
        self.assertEqual(
            _extract_arxiv_id("http://arxiv.org/abs/2301.12345v1"), "2301.12345"
        )

    def test_extract_arxiv_id_old_style(self) -> None:
        self.assertEqual(
            _extract_arxiv_id("http://arxiv.org/abs/hep-ph/9901257v2"),
            "hep-ph/9901257",
        )

    def test_extract_arxiv_id_no_version(self) -> None:
        self.assertEqual(
            _extract_arxiv_id("http://arxiv.org/abs/2301.12345"), "2301.12345"
        )

    def test_parse_arxiv_feed_single_entry(self) -> None:
        results = parse_arxiv_feed(_SAMPLE_ATOM)
        self.assertEqual(len(results), 1)

    def test_parse_arxiv_feed_empty_returns_empty_list(self) -> None:
        self.assertEqual(parse_arxiv_feed(_EMPTY_ATOM), [])

    def test_parse_arxiv_feed_multiple_entries(self) -> None:
        results = parse_arxiv_feed(_MULTI_ENTRY_ATOM)
        self.assertEqual(len(results), 2)

    def test_parse_arxiv_feed_invalid_xml_raises(self) -> None:
        with self.assertRaises(ValueError):
            parse_arxiv_feed("<not valid xml><<")

    def test_parse_arxiv_entry_fields(self) -> None:
        results = parse_arxiv_feed(_SAMPLE_ATOM)
        r = results[0]
        self.assertEqual(r["arxiv_id"], "2301.12345")
        self.assertEqual(r["title"], "Attention Is All You Need")
        self.assertEqual(r["authors"], ["Ashish Vaswani", "Noam Shazeer"])
        self.assertEqual(r["summary"], "A landmark transformer paper.")
        self.assertEqual(r["published"], "2017-06-12T00:00:00Z")
        self.assertEqual(r["updated"], "2017-06-12T00:00:00Z")
        self.assertIn("cs.LG", r["categories"])
        self.assertIn("cs.CL", r["categories"])
        self.assertEqual(r["primary_category"], "cs.LG")
        self.assertEqual(r["pdf_url"], "https://arxiv.org/pdf/2301.12345")
        self.assertEqual(r["abs_url"], "https://arxiv.org/abs/2301.12345")

    def test_parse_arxiv_entry_summary_stripped(self) -> None:
        """Summary whitespace is stripped."""
        results = parse_arxiv_feed(_SAMPLE_ATOM)
        self.assertFalse(results[0]["summary"].startswith(" "))
        self.assertFalse(results[0]["summary"].endswith(" "))

    def test_parse_arxiv_entry_missing_pdf_link_falls_back(self) -> None:
        """When the feed omits the pdf link, pdf_url is derived from arxiv_id."""
        no_pdf_link = """\
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/1234.56789v1</id>
    <title>No PDF Link</title>
    <summary>Abstract.</summary>
    <published>2020-01-01T00:00:00Z</published>
    <updated>2020-01-01T00:00:00Z</updated>
    <author><name>Someone</name></author>
  </entry>
</feed>"""
        results = parse_arxiv_feed(no_pdf_link)
        self.assertEqual(results[0]["pdf_url"], "https://arxiv.org/pdf/1234.56789")


# ---------------------------------------------------------------------------
# ArxivOperationTests
# ---------------------------------------------------------------------------


class ArxivOperationTests(unittest.TestCase):
    def test_catalog_has_four_operations(self) -> None:
        ops = build_arxiv_operation_catalog()
        self.assertEqual(len(ops), 4)

    def test_catalog_insertion_order(self) -> None:
        names = [op.name for op in build_arxiv_operation_catalog()]
        self.assertEqual(names, ["search", "search_raw", "get_paper", "download_paper"])

    def test_get_operation_search(self) -> None:
        op = get_arxiv_operation("search")
        self.assertEqual(op.name, "search")
        self.assertEqual(op.category, "Search")

    def test_get_operation_search_raw(self) -> None:
        op = get_arxiv_operation("search_raw")
        self.assertEqual(op.category, "Search")

    def test_get_operation_get_paper(self) -> None:
        op = get_arxiv_operation("get_paper")
        self.assertEqual(op.category, "Retrieval")

    def test_get_operation_download_paper(self) -> None:
        op = get_arxiv_operation("download_paper")
        self.assertEqual(op.category, "Download")

    def test_unknown_operation_raises_with_available_names(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            get_arxiv_operation("nonexistent")
        self.assertIn("nonexistent", str(ctx.exception))
        self.assertIn("search", str(ctx.exception))

    def test_summary_returns_name(self) -> None:
        op = get_arxiv_operation("search")
        self.assertEqual(op.summary(), "search")

    def test_operations_are_frozen(self) -> None:
        op = get_arxiv_operation("search")
        with self.assertRaises((AttributeError, TypeError)):
            op.name = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ArxivClientTests
# ---------------------------------------------------------------------------


def _fake_executor(xml_text: str) -> Any:
    """Return a request executor that always returns *xml_text*."""

    def _exec(
        method: str,
        url: str,
        *,
        headers: Any = None,
        json_body: Any = None,
        timeout_seconds: float = 30.0,
    ) -> str:
        return xml_text

    return _exec


class ArxivClientTests(unittest.TestCase):
    def _client(self, xml: str = _SAMPLE_ATOM) -> ArxivClient:
        return ArxivClient(
            config=ArxivConfig(),
            request_executor=_fake_executor(xml),
        )

    def test_default_client_constructs(self) -> None:
        client = ArxivClient()
        self.assertIsNotNone(client.config)

    def test_search_returns_parsed_records(self) -> None:
        results = self._client().search(query="ti:attention")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["arxiv_id"], "2301.12345")

    def test_search_passes_all_params_to_url(self) -> None:
        captured: list[str] = []

        def _exec(
            method: str,
            url: str,
            *,
            headers: Any = None,
            json_body: Any = None,
            timeout_seconds: float = 30.0,
        ) -> str:
            captured.append(url)
            return _EMPTY_ATOM

        client = ArxivClient(config=ArxivConfig(), request_executor=_exec)
        client.search(
            query="au:hinton",
            max_results=25,
            start=50,
            sort_by="submittedDate",
            sort_order="ascending",
        )
        self.assertEqual(len(captured), 1)
        self.assertIn("max_results=25", captured[0])
        self.assertIn("start=50", captured[0])
        self.assertIn("submittedDate", captured[0])
        self.assertIn("ascending", captured[0])

    def test_search_empty_results(self) -> None:
        results = self._client(xml=_EMPTY_ATOM).search(query="zzz_no_results")
        self.assertEqual(results, [])

    def test_search_raw_returns_string(self) -> None:
        xml = self._client().search_raw(query="ti:attention")
        self.assertIsInstance(xml, str)
        self.assertIn("<feed", xml)

    def test_get_paper_found(self) -> None:
        result = self._client().get_paper("2301.12345")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["arxiv_id"], "2301.12345")

    def test_get_paper_not_found_returns_none(self) -> None:
        result = self._client(xml=_EMPTY_ATOM).get_paper("0000.00000")
        self.assertIsNone(result)

    def test_download_paper_writes_bytes(self) -> None:
        pdf_bytes = b"%PDF-1.4 fake pdf content"

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = mock_urlopen.return_value.__enter__.return_value
            mock_response.read.return_value = pdf_bytes

            with tempfile.TemporaryDirectory() as tmpdir:
                save_path = os.path.join(tmpdir, "paper.pdf")
                client = ArxivClient(config=ArxivConfig())
                returned = client.download_paper("2301.12345", save_path)

                self.assertEqual(returned, save_path)
                with open(save_path, "rb") as fh:
                    self.assertEqual(fh.read(), pdf_bytes)

    def test_non_string_executor_response_raises(self) -> None:
        def _json_executor(
            method: str,
            url: str,
            *,
            headers: Any = None,
            json_body: Any = None,
            timeout_seconds: float = 30.0,
        ) -> dict[str, object]:
            return {"unexpected": "json"}

        client = ArxivClient(config=ArxivConfig(), request_executor=_json_executor)
        from harnessiq.providers.http import ProviderHTTPError

        with self.assertRaises(ProviderHTTPError):
            client.search(query="test")

    def test_delay_is_applied_before_request(self) -> None:
        """When delay_seconds > 0, time.sleep is called."""
        calls: list[float] = []

        def _exec(
            method: str,
            url: str,
            *,
            headers: Any = None,
            json_body: Any = None,
            timeout_seconds: float = 30.0,
        ) -> str:
            return _EMPTY_ATOM

        client = ArxivClient(
            config=ArxivConfig(delay_seconds=0.01),
            request_executor=_exec,
        )
        with patch("harnessiq.providers.arxiv.client.time.sleep") as mock_sleep:
            client.search(query="test")
            mock_sleep.assert_called_once()
            self.assertAlmostEqual(mock_sleep.call_args[0][0], 0.01)

    def test_no_delay_when_zero(self) -> None:
        """When delay_seconds == 0.0, time.sleep is not called."""

        def _exec(
            method: str,
            url: str,
            *,
            headers: Any = None,
            json_body: Any = None,
            timeout_seconds: float = 30.0,
        ) -> str:
            return _EMPTY_ATOM

        client = ArxivClient(config=ArxivConfig(delay_seconds=0.0), request_executor=_exec)
        with patch("harnessiq.providers.arxiv.client.time.sleep") as mock_sleep:
            client.search(query="test")
            mock_sleep.assert_not_called()

    def test_execute_operation_accepts_payload_request_dto(self) -> None:
        client = self._client()

        result = client.execute_operation(
            ProviderPayloadRequestDTO(
                operation="search",
                payload={"query": "ti:attention"},
            )
        )

        self.assertEqual(result.operation, "search")
        self.assertEqual(result.result_fields["count"], 1)


# ---------------------------------------------------------------------------
# ArxivToolsTests
# ---------------------------------------------------------------------------


class ArxivToolsTests(unittest.TestCase):
    """Tests for create_arxiv_tools() and the arxiv.request tool handler."""

    def _client(self, xml: str = _SAMPLE_ATOM) -> ArxivClient:
        return ArxivClient(
            config=ArxivConfig(),
            request_executor=_fake_executor(xml),
        )

    def test_create_arxiv_tools_no_args_returns_one_tool(self) -> None:
        from harnessiq.tools.arxiv import create_arxiv_tools

        tools = create_arxiv_tools()
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0].key, "arxiv.request")

    def test_create_arxiv_tools_with_client(self) -> None:
        from harnessiq.tools.arxiv import create_arxiv_tools

        tools = create_arxiv_tools(client=self._client())
        self.assertEqual(len(tools), 1)

    def test_create_arxiv_tools_with_config(self) -> None:
        from harnessiq.tools.arxiv import create_arxiv_tools

        tools = create_arxiv_tools(credentials=ArxivConfig())
        self.assertEqual(len(tools), 1)

    def test_allowed_operations_filters_enum(self) -> None:
        from harnessiq.tools.arxiv import create_arxiv_tools

        tools = create_arxiv_tools(
            client=self._client(), allowed_operations=["search"]
        )
        schema = tools[0].definition.input_schema
        self.assertEqual(schema["properties"]["operation"]["enum"], ["search"])

    def test_unknown_allowed_operation_raises(self) -> None:
        from harnessiq.tools.arxiv import create_arxiv_tools

        with self.assertRaises(ValueError):
            create_arxiv_tools(allowed_operations=["nonexistent"])

    def test_handler_search_returns_results_and_count(self) -> None:
        from harnessiq.tools.arxiv import create_arxiv_tools

        tools = create_arxiv_tools(client=self._client())
        result = tools[0].handler({"operation": "search", "query": "ti:attention"})
        self.assertEqual(result["operation"], "search")
        self.assertIn("results", result)
        self.assertIn("count", result)
        self.assertEqual(result["count"], len(result["results"]))

    def test_handler_search_raw_returns_xml_string(self) -> None:
        from harnessiq.tools.arxiv import create_arxiv_tools

        tools = create_arxiv_tools(client=self._client())
        result = tools[0].handler({"operation": "search_raw", "query": "ti:attention"})
        self.assertEqual(result["operation"], "search_raw")
        self.assertIsInstance(result["xml"], str)

    def test_handler_get_paper_returns_paper_dict(self) -> None:
        from harnessiq.tools.arxiv import create_arxiv_tools

        tools = create_arxiv_tools(client=self._client())
        result = tools[0].handler(
            {"operation": "get_paper", "paper_id": "2301.12345"}
        )
        self.assertEqual(result["operation"], "get_paper")
        self.assertIn("paper", result)

    def test_handler_download_paper_returns_saved_to(self) -> None:
        from harnessiq.tools.arxiv import create_arxiv_tools

        pdf_bytes = b"%PDF-1.4 content"
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_response = mock_urlopen.return_value.__enter__.return_value
            mock_response.read.return_value = pdf_bytes
            with tempfile.TemporaryDirectory() as tmpdir:
                save_path = os.path.join(tmpdir, "paper.pdf")
                tools = create_arxiv_tools()
                result = tools[0].handler(
                    {
                        "operation": "download_paper",
                        "paper_id": "2301.12345",
                        "save_path": save_path,
                    }
                )
                self.assertEqual(result["operation"], "download_paper")
                self.assertEqual(result["saved_to"], save_path)

    def test_handler_missing_query_raises(self) -> None:
        from harnessiq.tools.arxiv import create_arxiv_tools

        tools = create_arxiv_tools(client=self._client())
        with self.assertRaises(ValueError) as ctx:
            tools[0].handler({"operation": "search"})
        self.assertIn("query", str(ctx.exception))

    def test_handler_unknown_operation_raises(self) -> None:
        from harnessiq.tools.arxiv import create_arxiv_tools

        tools = create_arxiv_tools(client=self._client())
        with self.assertRaises(ValueError):
            tools[0].handler({"operation": "invalid_op"})

    def test_handler_missing_operation_raises(self) -> None:
        from harnessiq.tools.arxiv import create_arxiv_tools

        tools = create_arxiv_tools(client=self._client())
        with self.assertRaises(ValueError):
            tools[0].handler({})

    def test_tool_key_constant_matches(self) -> None:
        from harnessiq.shared.tools import ARXIV_REQUEST
        from harnessiq.tools.arxiv import create_arxiv_tools

        tools = create_arxiv_tools()
        self.assertEqual(tools[0].key, ARXIV_REQUEST)

    def test_pagination_params_forwarded_to_search(self) -> None:
        from harnessiq.tools.arxiv import create_arxiv_tools

        captured_urls: list[str] = []

        def _capturing_exec(
            method: str,
            url: str,
            *,
            headers: Any = None,
            json_body: Any = None,
            timeout_seconds: float = 30.0,
        ) -> str:
            captured_urls.append(url)
            return _EMPTY_ATOM

        client = ArxivClient(config=ArxivConfig(), request_executor=_capturing_exec)
        tools = create_arxiv_tools(client=client)
        tools[0].handler(
            {
                "operation": "search",
                "query": "all:transformer",
                "max_results": 50,
                "start": 100,
                "sort_by": "submittedDate",
                "sort_order": "ascending",
            }
        )
        self.assertEqual(len(captured_urls), 1)
        self.assertIn("max_results=50", captured_urls[0])
        self.assertIn("start=100", captured_urls[0])


# ---------------------------------------------------------------------------
# ArxivRegistryIntegrationTests
# ---------------------------------------------------------------------------


class ArxivRegistryIntegrationTests(unittest.TestCase):
    """Verify arXiv is correctly wired into ToolsetRegistry."""

    def test_get_arxiv_request_without_credentials_succeeds(self) -> None:
        from harnessiq.toolset.registry import ToolsetRegistry

        registry = ToolsetRegistry()
        tool = registry.get("arxiv.request")
        self.assertEqual(tool.key, "arxiv.request")

    def test_get_family_arxiv_without_credentials_succeeds(self) -> None:
        from harnessiq.toolset.registry import ToolsetRegistry

        registry = ToolsetRegistry()
        tools = registry.get_family("arxiv")
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0].key, "arxiv.request")

    def test_existing_provider_still_requires_credentials(self) -> None:
        """Regression: exa.request must still fail without credentials."""
        from harnessiq.toolset.registry import ToolsetRegistry

        registry = ToolsetRegistry()
        with self.assertRaises(ValueError) as ctx:
            registry.get("exa.request")
        self.assertIn("credentials", str(ctx.exception).lower())

    def test_existing_family_still_requires_credentials(self) -> None:
        """Regression: exa family must still fail without credentials."""
        from harnessiq.toolset.registry import ToolsetRegistry

        registry = ToolsetRegistry()
        with self.assertRaises(ValueError):
            registry.get_family("exa")

    def test_arxiv_appears_in_provider_entries(self) -> None:
        from harnessiq.toolset.catalog import PROVIDER_ENTRY_INDEX

        self.assertIn("arxiv.request", PROVIDER_ENTRY_INDEX)

    def test_arxiv_entry_requires_credentials_false(self) -> None:
        from harnessiq.toolset.catalog import PROVIDER_ENTRY_INDEX

        entry = PROVIDER_ENTRY_INDEX["arxiv.request"]
        self.assertFalse(entry.requires_credentials)

    def test_infer_provider_name_arxiv(self) -> None:
        from harnessiq.providers.http import _infer_provider_name

        self.assertEqual(_infer_provider_name("https://export.arxiv.org/api/query"), "arxiv")
        self.assertEqual(_infer_provider_name("https://arxiv.org/pdf/2301.12345"), "arxiv")


if __name__ == "__main__":
    unittest.main()
