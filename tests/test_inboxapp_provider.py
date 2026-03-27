"""Tests for harnessiq.providers.inboxapp."""
from __future__ import annotations
import unittest
from harnessiq.providers.inboxapp import InboxAppClient, InboxAppCredentials, build_inboxapp_operation_catalog, get_inboxapp_operation
from harnessiq.shared.tools import INBOXAPP_REQUEST
from harnessiq.tools.inboxapp import create_inboxapp_tools
from harnessiq.tools.registry import ToolRegistry
from harnessiq.shared.dtos import ProviderOperationRequestDTO

class InboxAppCredentialsTests(unittest.TestCase):

    def test_valid_credentials_accepted(self) -> None:
        c = InboxAppCredentials(api_key='key123')
        self.assertEqual(c.api_key, 'key123')

    def test_blank_api_key_raises(self) -> None:
        with self.assertRaises(ValueError):
            InboxAppCredentials(api_key='')

    def test_blank_api_key_whitespace_raises(self) -> None:
        with self.assertRaises(ValueError):
            InboxAppCredentials(api_key='   ')

    def test_zero_timeout_raises(self) -> None:
        with self.assertRaises(ValueError):
            InboxAppCredentials(api_key='key', timeout_seconds=0)

    def test_default_base_url_set(self) -> None:
        c = InboxAppCredentials(api_key='key')
        self.assertIn('inboxapp.com', c.base_url)

    def test_as_redacted_dict_excludes_raw_key(self) -> None:
        c = InboxAppCredentials(api_key='supersecretkey')
        summary = c.as_redacted_dict()
        self.assertNotIn('supersecretkey', str(summary))

class InboxAppApiTests(unittest.TestCase):

    def test_build_headers_produces_bearer_token(self) -> None:
        from harnessiq.providers.inboxapp.api import build_headers
        headers = build_headers('mykey')
        self.assertEqual(headers['Authorization'], 'Bearer mykey')

    def test_build_headers_with_extra_headers(self) -> None:
        from harnessiq.providers.inboxapp.api import build_headers
        headers = build_headers('mykey', extra_headers={'X-Custom': 'val'})
        self.assertEqual(headers['X-Custom'], 'val')
        self.assertIn('Authorization', headers)

class InboxAppOperationCatalogTests(unittest.TestCase):

    def test_catalog_is_non_empty(self) -> None:
        catalog = build_inboxapp_operation_catalog()
        self.assertGreater(len(catalog), 0)

    def test_catalog_covers_core_categories(self) -> None:
        catalog = build_inboxapp_operation_catalog()
        categories = {op.category for op in catalog}
        self.assertIn('Status', categories)
        self.assertIn('Thread', categories)
        self.assertIn('Prospect', categories)

    def test_create_thread_requires_payload(self) -> None:
        op = get_inboxapp_operation('create_thread')
        self.assertTrue(op.payload_required)
        self.assertEqual(op.method, 'POST')

    def test_get_thread_requires_thread_id(self) -> None:
        op = get_inboxapp_operation('get_thread')
        self.assertIn('thread_id', op.required_path_params)

    def test_get_operation_raises_for_unknown(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            get_inboxapp_operation('nonexistent_op')
        self.assertIn('nonexistent_op', str(ctx.exception))

class InboxAppClientTests(unittest.TestCase):

    def _client(self) -> InboxAppClient:
        creds = InboxAppCredentials(api_key='testkey')
        return InboxAppClient(credentials=creds, request_executor=lambda m, u, **kw: {'results': []})

    def test_prepare_request_list_statuses_url(self) -> None:
        prepared = self._client().prepare_request(ProviderOperationRequestDTO(operation='list_statuses'))
        self.assertIn('/statuses', prepared.url)
        self.assertEqual(prepared.method, 'GET')

    def test_prepare_request_interpolates_thread_id(self) -> None:
        prepared = self._client().prepare_request(ProviderOperationRequestDTO(operation='get_thread', path_params={'thread_id': 'thr_1'}))
        self.assertIn('thr_1', prepared.url)

    def test_prepare_request_sets_bearer_header(self) -> None:
        prepared = self._client().prepare_request(ProviderOperationRequestDTO(operation='list_threads'))
        self.assertEqual(prepared.headers['Authorization'], 'Bearer testkey')

    def test_prepare_request_raises_on_missing_path_param(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request(ProviderOperationRequestDTO(operation='get_status'))

    def test_prepare_request_raises_on_missing_required_payload(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request(ProviderOperationRequestDTO(operation='create_status'))

    def test_prepare_request_rejects_payload_on_no_payload_op(self) -> None:
        with self.assertRaises(ValueError):
            self._client().prepare_request(ProviderOperationRequestDTO(operation='list_threads', payload={'bad': 'field'}))

class InboxAppToolsTests(unittest.TestCase):

    def test_create_inboxapp_tools_returns_registerable_tuple(self) -> None:
        creds = InboxAppCredentials(api_key='testkey')
        tools = create_inboxapp_tools(credentials=creds)
        self.assertEqual(len(tools), 1)
        ToolRegistry(tools)

    def test_tool_definition_key_is_inboxapp_request(self) -> None:
        creds = InboxAppCredentials(api_key='testkey')
        tools = create_inboxapp_tools(credentials=creds)
        self.assertEqual(tools[0].definition.key, INBOXAPP_REQUEST)

    def test_tool_handler_executes_list_threads(self) -> None:
        captured: list[dict[str, object]] = []

        def fake(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured.append({'method': method, 'url': url})
            return {'data': []}
        creds = InboxAppCredentials(api_key='testkey')
        client = InboxAppClient(credentials=creds, request_executor=fake)
        tools = create_inboxapp_tools(client=client)
        registry = ToolRegistry(tools)
        result = registry.execute(INBOXAPP_REQUEST, {'operation': 'list_threads'})
        self.assertEqual(result.output['operation'], 'list_threads')
        self.assertEqual(len(captured), 1)

    def test_create_inboxapp_tools_raises_without_credentials_or_client(self) -> None:
        with self.assertRaises(ValueError):
            create_inboxapp_tools()

    def test_allowed_operations_subset(self) -> None:
        creds = InboxAppCredentials(api_key='testkey')
        tools = create_inboxapp_tools(credentials=creds, allowed_operations=['list_threads', 'get_thread'])
        enum_vals = tools[0].definition.input_schema['properties']['operation']['enum']
        self.assertEqual(set(enum_vals), {'list_threads', 'get_thread'})
if __name__ == '__main__':
    unittest.main()
