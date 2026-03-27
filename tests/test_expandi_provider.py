"""Unit tests for the Expandi provider."""
from __future__ import annotations
import unittest
from harnessiq.providers.expandi.api import DEFAULT_BASE_URL, build_headers
from harnessiq.providers.expandi.client import ExpandiClient, ExpandiCredentials
from harnessiq.providers.expandi.operations import build_expandi_operation_catalog, build_expandi_request_tool_definition, create_expandi_tools, get_expandi_operation
from harnessiq.shared.dtos import ProviderOperationRequestDTO

def _mock_executor(response: object):

    def executor(method, url, *, headers, json_body, timeout_seconds):
        return response
    return executor

class ExpandiCredentialsTests(unittest.TestCase):

    def test_valid_credentials(self):
        creds = ExpandiCredentials(api_key='key-abc', api_secret='secret-xyz')
        self.assertEqual(creds.api_key, 'key-abc')
        self.assertEqual(creds.api_secret, 'secret-xyz')
        self.assertEqual(creds.base_url, DEFAULT_BASE_URL)

    def test_blank_api_key_raises(self):
        with self.assertRaises(ValueError):
            ExpandiCredentials(api_key='', api_secret='secret')

    def test_blank_api_secret_raises(self):
        with self.assertRaises(ValueError):
            ExpandiCredentials(api_key='key', api_secret='')

    def test_whitespace_api_key_raises(self):
        with self.assertRaises(ValueError):
            ExpandiCredentials(api_key='   ', api_secret='secret')

    def test_whitespace_api_secret_raises(self):
        with self.assertRaises(ValueError):
            ExpandiCredentials(api_key='key', api_secret='   ')

    def test_blank_base_url_raises(self):
        with self.assertRaises(ValueError):
            ExpandiCredentials(api_key='k', api_secret='s', base_url='')

    def test_zero_timeout_raises(self):
        with self.assertRaises(ValueError):
            ExpandiCredentials(api_key='k', api_secret='s', timeout_seconds=0)

    def test_masked_api_key_hides_secret(self):
        creds = ExpandiCredentials(api_key='abcdefghijklmno', api_secret='s')
        masked = creds.masked_api_key()
        self.assertNotIn('abcdefghijklmno', masked)

    def test_masked_api_secret_hides_secret(self):
        creds = ExpandiCredentials(api_key='k', api_secret='xyzabcdefghijkl')
        masked = creds.masked_api_secret()
        self.assertNotIn('xyzabcdefghijkl', masked)

    def test_as_redacted_dict_no_raw_credentials(self):
        creds = ExpandiCredentials(api_key='my-api-key-value', api_secret='my-api-secret-value')
        d = creds.as_redacted_dict()
        self.assertNotIn('my-api-key-value', str(d))
        self.assertNotIn('my-api-secret-value', str(d))
        self.assertIn('api_key_masked', d)
        self.assertIn('api_secret_masked', d)

class ExpandiApiTests(unittest.TestCase):

    def test_build_headers_no_auth(self):
        headers = build_headers()
        self.assertNotIn('key', headers)
        self.assertNotIn('secret', headers)
        self.assertNotIn('Authorization', headers)
        self.assertEqual(headers['Content-Type'], 'application/json')

class ExpandiOperationCatalogTests(unittest.TestCase):

    def test_catalog_count(self):
        catalog = build_expandi_operation_catalog()
        self.assertEqual(len(catalog), 22)

    def test_expected_operations_present(self):
        names = {op.name for op in build_expandi_operation_catalog()}
        self.assertIn('list_campaigns', names)
        self.assertIn('add_prospect_to_campaign', names)
        self.assertIn('add_multiple_prospects_to_campaign', names)
        self.assertIn('pause_campaign_contact', names)
        self.assertIn('resume_campaign_contact', names)
        self.assertIn('create_campaign_contact_v2', names)
        self.assertIn('update_campaign_contact_v2', names)
        self.assertIn('delete_campaign_contact_v2', names)
        self.assertIn('list_linkedin_accounts', names)
        self.assertIn('list_linkedin_accounts_v2', names)
        self.assertIn('send_connection_request', names)
        self.assertIn('send_message', names)
        self.assertIn('send_email', names)
        self.assertIn('check_action_status', names)
        self.assertIn('fetch_messages', names)
        self.assertIn('enable_messaging_webhook', names)
        self.assertIn('disable_messaging_webhook', names)
        self.assertIn('add_to_blacklist', names)

    def test_get_invalid_operation_raises(self):
        with self.assertRaises(ValueError) as ctx:
            get_expandi_operation('nonexistent_op')
        self.assertIn('nonexistent_op', str(ctx.exception))

    def test_add_prospect_requires_campaign_id(self):
        op = get_expandi_operation('add_prospect_to_campaign')
        self.assertIn('campaign_id', op.required_path_params)

    def test_pause_contact_requires_contact_id(self):
        op = get_expandi_operation('pause_campaign_contact')
        self.assertIn('contact_id', op.required_path_params)

    def test_send_connection_requires_account_id(self):
        op = get_expandi_operation('send_connection_request')
        self.assertIn('account_id', op.required_path_params)

class ExpandiClientTests(unittest.TestCase):

    def _make_client(self, response=None):
        creds = ExpandiCredentials(api_key='test-key', api_secret='test-secret')
        return ExpandiClient(credentials=creds, request_executor=_mock_executor(response or []))

    def test_auth_key_in_url_query_params(self):
        client = self._make_client()
        prepared = client.prepare_request(ProviderOperationRequestDTO(operation='list_campaigns'))
        self.assertIn('key=test-key', prepared.url)

    def test_auth_secret_in_url_query_params(self):
        client = self._make_client()
        prepared = client.prepare_request(ProviderOperationRequestDTO(operation='list_campaigns'))
        self.assertIn('secret=test-secret', prepared.url)

    def test_auth_not_in_headers(self):
        client = self._make_client()
        prepared = client.prepare_request(ProviderOperationRequestDTO(operation='list_campaigns'))
        self.assertNotIn('key', prepared.headers)
        self.assertNotIn('secret', prepared.headers)

    def test_missing_campaign_id_raises(self):
        client = self._make_client()
        with self.assertRaises(ValueError) as ctx:
            client.prepare_request(ProviderOperationRequestDTO(operation='add_prospect_to_campaign', payload={'profile_link': 'https://linkedin.com/in/test'}))
        self.assertIn('campaign_id', str(ctx.exception))

    def test_missing_payload_for_required_op_raises(self):
        client = self._make_client()
        with self.assertRaises(ValueError):
            client.prepare_request(ProviderOperationRequestDTO(operation='add_prospect_to_campaign', path_params={'campaign_id': '123'}))

    def test_path_param_substituted_in_url(self):
        client = self._make_client()
        prepared = client.prepare_request(ProviderOperationRequestDTO(operation='pause_campaign_contact', path_params={'contact_id': 'cont-456'}))
        self.assertIn('cont-456', prepared.url)

    def test_execute_returns_response(self):
        response = [{'id': 'c1', 'name': 'Campaign 1'}]
        client = self._make_client(response=response)
        result = client.execute_operation(ProviderOperationRequestDTO(operation='list_campaigns')).response
        self.assertEqual(result, response)

class ExpandiToolTests(unittest.TestCase):

    def _make_creds(self):
        return ExpandiCredentials(api_key='tool-key', api_secret='tool-secret')

    def test_create_tools_returns_one_tool(self):
        tools = create_expandi_tools(credentials=self._make_creds())
        self.assertEqual(len(tools), 1)

    def test_tool_key(self):
        tools = create_expandi_tools(credentials=self._make_creds())
        self.assertEqual(tools[0].key, 'expandi.request')

    def test_tool_name(self):
        tools = create_expandi_tools(credentials=self._make_creds())
        self.assertEqual(tools[0].definition.name, 'expandi_request')

    def test_no_credentials_raises(self):
        with self.assertRaises(ValueError):
            create_expandi_tools()

    def test_handler_returns_expected_shape(self):
        response = [{'id': 'c1'}]
        creds = self._make_creds()
        client = ExpandiClient(credentials=creds, request_executor=_mock_executor(response))
        tools = create_expandi_tools(client=client)
        result = tools[0].handler({'operation': 'list_campaigns'})
        self.assertIn('operation', result)
        self.assertIn('response', result)
        self.assertEqual(result['response'], response)

    def test_tool_definition_required_operation(self):
        defn = build_expandi_request_tool_definition()
        self.assertIn('operation', defn.input_schema['required'])
if __name__ == '__main__':
    unittest.main()
