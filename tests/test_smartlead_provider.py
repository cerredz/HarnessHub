"""Unit tests for the Smartlead provider."""
from __future__ import annotations
import unittest
from harnessiq.providers.smartlead.api import DEFAULT_BASE_URL, build_headers
from harnessiq.providers.smartlead.client import SmartleadClient, SmartleadCredentials
from harnessiq.providers.smartlead.operations import build_smartlead_operation_catalog, build_smartlead_request_tool_definition, create_smartlead_tools, get_smartlead_operation
from harnessiq.shared.dtos import ProviderOperationRequestDTO

def _mock_executor(response: object):

    def executor(method, url, *, headers, json_body, timeout_seconds):
        return response
    return executor

class SmartleadCredentialsTests(unittest.TestCase):

    def test_valid_credentials(self):
        creds = SmartleadCredentials(api_key='sl-key-abc')
        self.assertEqual(creds.api_key, 'sl-key-abc')
        self.assertEqual(creds.base_url, DEFAULT_BASE_URL)
        self.assertEqual(creds.timeout_seconds, 60.0)

    def test_blank_api_key_raises(self):
        with self.assertRaises(ValueError):
            SmartleadCredentials(api_key='')

    def test_whitespace_api_key_raises(self):
        with self.assertRaises(ValueError):
            SmartleadCredentials(api_key='   ')

    def test_blank_base_url_raises(self):
        with self.assertRaises(ValueError):
            SmartleadCredentials(api_key='k', base_url='')

    def test_zero_timeout_raises(self):
        with self.assertRaises(ValueError):
            SmartleadCredentials(api_key='k', timeout_seconds=0)

    def test_masked_api_key_hides_secret(self):
        creds = SmartleadCredentials(api_key='abcdefghijklmnop')
        masked = creds.masked_api_key()
        self.assertNotIn('abcdefghijklmnop', masked)

    def test_as_redacted_dict_no_raw_key(self):
        creds = SmartleadCredentials(api_key='super-secret-sl')
        d = creds.as_redacted_dict()
        self.assertNotIn('super-secret-sl', str(d))
        self.assertIn('api_key_masked', d)

class SmartleadApiTests(unittest.TestCase):

    def test_build_headers_no_auth(self):
        headers = build_headers()
        self.assertNotIn('api_key', headers)
        self.assertNotIn('Authorization', headers)
        self.assertEqual(headers['Content-Type'], 'application/json')

class SmartleadOperationCatalogTests(unittest.TestCase):

    def test_catalog_count(self):
        catalog = build_smartlead_operation_catalog()
        self.assertEqual(len(catalog), 48)

    def test_campaign_operations_present(self):
        names = {op.name for op in build_smartlead_operation_catalog()}
        self.assertIn('list_campaigns', names)
        self.assertIn('get_campaign', names)
        self.assertIn('create_campaign', names)
        self.assertIn('update_campaign_status', names)
        self.assertIn('update_campaign_schedule', names)
        self.assertIn('update_campaign_settings', names)
        self.assertIn('delete_campaign', names)

    def test_email_account_operations_present(self):
        names = {op.name for op in build_smartlead_operation_catalog()}
        self.assertIn('list_email_accounts', names)
        self.assertIn('save_email_account', names)
        self.assertIn('update_email_account_warmup', names)
        self.assertIn('get_email_account_warmup_stats', names)
        self.assertIn('add_email_account_to_campaign', names)
        self.assertIn('remove_email_account_from_campaign', names)

    def test_lead_operations_present(self):
        names = {op.name for op in build_smartlead_operation_catalog()}
        self.assertIn('add_leads_to_campaign', names)
        self.assertIn('fetch_lead_by_email', names)
        self.assertIn('fetch_global_leads', names)
        self.assertIn('pause_lead', names)
        self.assertIn('resume_lead', names)
        self.assertIn('delete_lead', names)
        self.assertIn('unsubscribe_lead_from_campaign', names)
        self.assertIn('unsubscribe_lead_globally', names)

    def test_analytics_operations_present(self):
        names = {op.name for op in build_smartlead_operation_catalog()}
        self.assertIn('get_campaign_analytics', names)
        self.assertIn('get_campaign_analytics_by_date', names)
        self.assertIn('get_account_analytics', names)

    def test_webhook_operations_present(self):
        names = {op.name for op in build_smartlead_operation_catalog()}
        self.assertIn('list_campaign_webhooks', names)
        self.assertIn('save_campaign_webhook', names)
        self.assertIn('delete_campaign_webhook', names)

    def test_client_management_operations_present(self):
        names = {op.name for op in build_smartlead_operation_catalog()}
        self.assertIn('list_clients', names)
        self.assertIn('save_client', names)
        self.assertIn('create_client_api_key', names)
        self.assertIn('delete_client_api_key', names)
        self.assertIn('reset_client_api_key', names)

    def test_get_invalid_operation_raises(self):
        with self.assertRaises(ValueError) as ctx:
            get_smartlead_operation('nonexistent_op')
        self.assertIn('nonexistent_op', str(ctx.exception))

    def test_campaign_id_required_for_campaign_ops(self):
        for name in ['get_campaign', 'update_campaign_status', 'delete_campaign']:
            op = get_smartlead_operation(name)
            self.assertIn('campaign_id', op.required_path_params, f'{name} missing campaign_id')

    def test_lead_id_required_for_lead_ops(self):
        for name in ['pause_lead', 'resume_lead', 'delete_lead']:
            op = get_smartlead_operation(name)
            self.assertIn('campaign_id', op.required_path_params)
            self.assertIn('lead_id', op.required_path_params)

class SmartleadClientTests(unittest.TestCase):

    def _make_client(self, response=None):
        creds = SmartleadCredentials(api_key='sl-test-key')
        return SmartleadClient(credentials=creds, request_executor=_mock_executor(response or []))

    def test_api_key_in_url_as_query_param(self):
        client = self._make_client()
        prepared = client.prepare_request(ProviderOperationRequestDTO(operation='list_campaigns'))
        self.assertIn('api_key=sl-test-key', prepared.url)

    def test_api_key_not_in_headers(self):
        client = self._make_client()
        prepared = client.prepare_request(ProviderOperationRequestDTO(operation='list_campaigns'))
        self.assertNotIn('api_key', prepared.headers)

    def test_base_url_is_smartlead(self):
        client = self._make_client()
        prepared = client.prepare_request(ProviderOperationRequestDTO(operation='list_campaigns'))
        self.assertIn('smartlead.ai', prepared.url)

    def test_missing_campaign_id_raises(self):
        client = self._make_client()
        with self.assertRaises(ValueError) as ctx:
            client.prepare_request(ProviderOperationRequestDTO(operation='get_campaign'))
        self.assertIn('campaign_id', str(ctx.exception))

    def test_missing_payload_raises(self):
        client = self._make_client()
        with self.assertRaises(ValueError):
            client.prepare_request(ProviderOperationRequestDTO(operation='create_campaign'))

    def test_path_params_substituted(self):
        client = self._make_client()
        prepared = client.prepare_request(ProviderOperationRequestDTO(operation='get_campaign', path_params={'campaign_id': 'camp-789'}))
        self.assertIn('camp-789', prepared.url)
        self.assertNotIn('{campaign_id}', prepared.url)

    def test_double_path_params(self):
        client = self._make_client()
        prepared = client.prepare_request(ProviderOperationRequestDTO(operation='pause_lead', path_params={'campaign_id': 'c1', 'lead_id': 'l1'}))
        self.assertIn('c1', prepared.url)
        self.assertIn('l1', prepared.url)

    def test_execute_returns_response(self):
        response = [{'id': 1, 'name': 'My Campaign'}]
        client = self._make_client(response=response)
        result = client.execute_operation(ProviderOperationRequestDTO(operation='list_campaigns')).response
        self.assertEqual(result, response)

class SmartleadToolTests(unittest.TestCase):

    def _make_creds(self):
        return SmartleadCredentials(api_key='sl-tool-key')

    def test_create_tools_returns_one_tool(self):
        tools = create_smartlead_tools(credentials=self._make_creds())
        self.assertEqual(len(tools), 1)

    def test_tool_key(self):
        tools = create_smartlead_tools(credentials=self._make_creds())
        self.assertEqual(tools[0].key, 'smartlead.request')

    def test_tool_name(self):
        tools = create_smartlead_tools(credentials=self._make_creds())
        self.assertEqual(tools[0].definition.name, 'smartlead_request')

    def test_no_credentials_raises(self):
        with self.assertRaises(ValueError):
            create_smartlead_tools()

    def test_handler_returns_expected_shape(self):
        response = [{'id': 1}]
        creds = self._make_creds()
        client = SmartleadClient(credentials=creds, request_executor=_mock_executor(response))
        tools = create_smartlead_tools(client=client)
        result = tools[0].handler({'operation': 'list_campaigns'})
        self.assertIn('operation', result)
        self.assertIn('response', result)
        self.assertEqual(result['response'], response)

    def test_tool_definition_required_operation(self):
        defn = build_smartlead_request_tool_definition()
        self.assertIn('operation', defn.input_schema['required'])
if __name__ == '__main__':
    unittest.main()
