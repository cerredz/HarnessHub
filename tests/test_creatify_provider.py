"""Tests for harnessiq.providers.creatify."""
from __future__ import annotations
import unittest
from harnessiq.providers.creatify import CreatifyClient, CreatifyCredentials, build_creatify_operation_catalog, get_creatify_operation
from harnessiq.shared.tools import CREATIFY_REQUEST
from harnessiq.tools.creatify import create_creatify_tools
from harnessiq.tools.registry import ToolRegistry
from harnessiq.shared.dtos import ProviderOperationRequestDTO

def _fake_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
    return {'method': method, 'url': url, 'kwargs': kwargs}

class CreatifyCredentialsTests(unittest.TestCase):

    def test_valid_credentials_accepted(self) -> None:
        c = CreatifyCredentials(api_id='my-id', api_key='my-key')
        self.assertEqual(c.api_id, 'my-id')

    def test_blank_api_id_raises(self) -> None:
        with self.assertRaises(ValueError):
            CreatifyCredentials(api_id='', api_key='key')

    def test_blank_api_key_raises(self) -> None:
        with self.assertRaises(ValueError):
            CreatifyCredentials(api_id='id', api_key='')

    def test_whitespace_api_id_raises(self) -> None:
        with self.assertRaises(ValueError):
            CreatifyCredentials(api_id='   ', api_key='key')

    def test_zero_timeout_raises(self) -> None:
        with self.assertRaises(ValueError):
            CreatifyCredentials(api_id='id', api_key='key', timeout_seconds=0)

    def test_masked_api_key_redacts_middle(self) -> None:
        c = CreatifyCredentials(api_id='id', api_key='abc12345678def')
        masked = c.masked_api_key()
        self.assertIn('*', masked)
        self.assertNotIn('12345678', masked)
        self.assertTrue(masked.endswith('def'[-4:]) or '*' in masked)

    def test_as_redacted_dict_excludes_raw_key(self) -> None:
        c = CreatifyCredentials(api_id='myid', api_key='supersecret')
        summary = c.as_redacted_dict()
        self.assertNotIn('supersecret', str(summary))
        self.assertIn('api_key_masked', summary)
        self.assertEqual(summary['api_id'], 'myid')

class CreatifyOperationCatalogTests(unittest.TestCase):

    def test_catalog_covers_all_categories(self) -> None:
        catalog = build_creatify_operation_catalog()
        categories = {op.category for op in catalog}
        expected_categories = {'Link to Video', 'Aurora Avatar', 'AI Avatar v1', 'AI Avatar v2', 'AI Shorts', 'AI Scripts', 'AI Editing', 'Ad Clone', 'Asset Generator', 'Custom Templates', 'IAB Images', 'Inspiration', 'Product to Video', 'Links', 'Music', 'Custom Avatars', 'Text-to-Speech', 'Voices', 'Workspace'}
        self.assertEqual(categories, expected_categories)

    def test_catalog_has_expected_operation_count(self) -> None:
        catalog = build_creatify_operation_catalog()
        self.assertGreaterEqual(len(catalog), 50)

    def test_get_operation_returns_correct_op(self) -> None:
        op = get_creatify_operation('create_link_to_video')
        self.assertEqual(op.method, 'POST')
        self.assertIn('link_to_videos', op.path_hint)

    def test_get_operation_raises_for_unknown(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            get_creatify_operation('nonexistent_op')
        self.assertIn('nonexistent_op', str(ctx.exception))

    def test_get_lipsync_requires_id_path_param(self) -> None:
        op = get_creatify_operation('get_lipsync')
        self.assertIn('id', op.required_path_params)

    def test_get_remaining_credits_is_get_with_no_payload(self) -> None:
        op = get_creatify_operation('get_remaining_credits')
        self.assertEqual(op.method, 'GET')
        self.assertEqual(op.payload_kind, 'none')

class CreatifyClientTests(unittest.TestCase):

    def _client(self) -> CreatifyClient:
        creds = CreatifyCredentials(api_id='test-id', api_key='test-key')
        return CreatifyClient(credentials=creds, request_executor=_fake_executor)

    def test_prepare_request_builds_correct_url_for_list(self) -> None:
        client = self._client()
        prepared = client.prepare_request(ProviderOperationRequestDTO(operation='list_links'))
        self.assertEqual(prepared.method, 'GET')
        self.assertIn('/api/links/', prepared.url)

    def test_prepare_request_interpolates_path_param(self) -> None:
        client = self._client()
        prepared = client.prepare_request(ProviderOperationRequestDTO(operation='get_lipsync', path_params={'id': 'abc-123'}))
        self.assertIn('abc-123', prepared.url)

    def test_prepare_request_sets_auth_headers(self) -> None:
        client = self._client()
        prepared = client.prepare_request(ProviderOperationRequestDTO(operation='get_remaining_credits'))
        self.assertEqual(prepared.headers['X-API-ID'], 'test-id')
        self.assertEqual(prepared.headers['X-API-KEY'], 'test-key')

    def test_prepare_request_raises_on_missing_required_path_param(self) -> None:
        client = self._client()
        with self.assertRaises(ValueError):
            client.prepare_request(ProviderOperationRequestDTO(operation='get_lipsync'))

    def test_prepare_request_raises_on_unexpected_payload(self) -> None:
        client = self._client()
        with self.assertRaises(ValueError):
            client.prepare_request(ProviderOperationRequestDTO(operation='get_remaining_credits', payload={'bad': True}))

    def test_prepare_request_raises_on_missing_required_payload(self) -> None:
        client = self._client()
        with self.assertRaises(ValueError):
            client.prepare_request(ProviderOperationRequestDTO(operation='create_link_to_video'))

    def test_execute_operation_calls_executor_with_correct_args(self) -> None:
        captured: dict[str, object] = {}

        def recording_executor(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured['method'] = method
            captured['url'] = url
            captured['headers'] = kwargs.get('headers')
            return {'status': 'ok'}
        creds = CreatifyCredentials(api_id='id', api_key='key')
        client = CreatifyClient(credentials=creds, request_executor=recording_executor)
        result = client.execute_operation(ProviderOperationRequestDTO(operation='get_remaining_credits')).response
        self.assertEqual(captured['method'], 'GET')
        self.assertIn('remaining-credits', str(captured['url']))
        self.assertEqual(result, {'status': 'ok'})

class CreatifyToolsTests(unittest.TestCase):

    def test_create_creatify_tools_returns_registerable_tuple(self) -> None:
        creds = CreatifyCredentials(api_id='id', api_key='key')
        tools = create_creatify_tools(credentials=creds)
        self.assertEqual(len(tools), 1)
        registry = ToolRegistry(tools)
        self.assertIn(CREATIFY_REQUEST, {t.definition.key for t in tools})

    def test_tool_handler_executes_operation(self) -> None:
        captured: list[dict[str, object]] = []

        def fake(method: str, url: str, **kwargs: object) -> dict[str, object]:
            captured.append({'method': method, 'url': url})
            return {'credits': 100}
        creds = CreatifyCredentials(api_id='id', api_key='key')
        client = CreatifyClient(credentials=creds, request_executor=fake)
        tools = create_creatify_tools(client=client)
        registry = ToolRegistry(tools)
        result = registry.execute(CREATIFY_REQUEST, {'operation': 'get_remaining_credits'})
        self.assertEqual(result.output['operation'], 'get_remaining_credits')
        self.assertEqual(result.output['response'], {'credits': 100})
        self.assertEqual(len(captured), 1)

    def test_create_creatify_tools_raises_without_credentials_or_client(self) -> None:
        with self.assertRaises(ValueError):
            create_creatify_tools()

    def test_allowed_operations_subset_filters_tool_enum(self) -> None:
        creds = CreatifyCredentials(api_id='id', api_key='key')
        tools = create_creatify_tools(credentials=creds, allowed_operations=['get_remaining_credits', 'list_voices'])
        schema = tools[0].definition.input_schema
        allowed_ops = schema['properties']['operation']['enum']
        self.assertEqual(sorted(allowed_ops), sorted(['get_remaining_credits', 'list_voices']))
if __name__ == '__main__':
    unittest.main()
