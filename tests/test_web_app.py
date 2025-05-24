import unittest
from unittest.mock import patch, MagicMock, call
import os
import sys
import json # For session data

# Ensure src directory is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Import the Flask app instance
from web_app import app as flask_app # Renamed to flask_app to avoid conflict

# Mock for GA4 RunReportResponse object for tests
class MockWebAppRunReportResponse: # Renamed to avoid conflict if other test files are imported
    def __init__(self, rows_data=None):
        self.rows = rows_data if rows_data is not None else []
        self.dimension_headers = []
        self.metric_headers = []


class TestWebApp(unittest.TestCase):

    def setUp(self):
        """Set up test client and other test variables."""
        flask_app.config['TESTING'] = True
        flask_app.config['SECRET_KEY'] = 'test_secret_key_for_web_app' # Consistent key
        flask_app.config['WTF_CSRF_ENABLED'] = False # Disable CSRF for easier testing of forms if any
        # Override OAuth client ID and Secret for testing if web_app.py checks for them at startup
        flask_app.config['GOOGLE_OAUTH_CLIENT_ID'] = "test_client_id.apps.googleusercontent.com"
        flask_app.config['GOOGLE_OAUTH_CLIENT_SECRET'] = "test_client_secret"
        os.environ['FLASK_SECRET_KEY'] = 'test_secret_key_for_web_app' # Ensure it's set for session
        os.environ['GOOGLE_OAUTH_CLIENT_ID'] = "test_client_id.apps.googleusercontent.com"
        os.environ['GOOGLE_OAUTH_CLIENT_SECRET'] = "test_client_secret"
        
        self.client = flask_app.test_client()

    def tearDown(self):
        # Clean up environment variables if set during a specific test
        pass

    # --- Test Basic Routes (Unauthenticated) ---
    def test_login_page_get(self):
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Sign in with Google", response.data)

    def test_index_route_unauthenticated(self):
        response = self.client.get('/')
        # Expects redirect to login page
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith('/login'))

    def test_chat_interface_route_unauthenticated(self):
        response = self.client.get('/chat-interface')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith('/login'))

    def test_chat_post_route_unauthenticated(self):
        response = self.client.post('/chat', json={'query': 'test'})
        self.assertEqual(response.status_code, 401) # Expecting JSON error for AJAX
        json_response = json.loads(response.data)
        self.assertIn("error", json_response)
        self.assertEqual(json_response["error"], "Unauthorized. Please log in.")

    # --- Test OAuth Flow ---
    @patch('web_app.Flow.from_client_config')
    def test_auth_google_redirects(self, mock_flow_from_config):
        mock_flow_instance = MagicMock()
        mock_flow_instance.authorization_url.return_value = ("https://mock_google_auth_url.com", "mock_state")
        mock_flow_from_config.return_value = mock_flow_instance

        response = self.client.get('/auth/google')
        
        self.assertEqual(response.status_code, 302) # Redirect
        self.assertEqual(response.location, "https://mock_google_auth_url.com")
        mock_flow_instance.authorization_url.assert_called_once_with(
            access_type='offline', include_granted_scopes='true'
        )
        with self.client.session_transaction() as sess:
            self.assertEqual(sess['state'], "mock_state")

    @patch('web_app.Flow.from_client_config')
    @patch('web_app.requests.get') # To mock the call to Google's userinfo endpoint
    def test_auth_callback_success(self, mock_requests_get, mock_flow_from_config):
        # Setup mock for Flow instance
        mock_flow_instance = MagicMock()
        mock_creds = MagicMock()
        mock_creds.to_json.return_value = '{"token": "fake_token", "refresh_token": "fake_refresh", "client_id": "test_client_id", "client_secret": "test_client_secret", "scopes": ["openid"]}'
        mock_creds.token = "fake_token_value" # For userinfo request
        mock_flow_instance.credentials = mock_creds
        mock_flow_from_config.return_value = mock_flow_instance

        # Mock the requests.get call for userinfo
        mock_userinfo_response = MagicMock()
        mock_userinfo_response.ok = True
        mock_userinfo_response.json.return_value = {
            "email": "test@example.com",
            "name": "Test User",
            "sub": "12345sub"
        }
        mock_requests_get.return_value = mock_userinfo_response

        # Simulate session state set by /auth/google
        with self.client.session_transaction() as sess:
            sess['state'] = "test_state_123"
        
        response = self.client.get('/auth/callback?state=test_state_123&code=fake_auth_code')

        mock_flow_instance.fetch_token.assert_called_once() # Check if token fetch was attempted
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith('/chat-interface'))
        with self.client.session_transaction() as sess:
            self.assertIn('credentials_json', sess)
            self.assertEqual(sess['user_email'], "test@example.com")
            self.assertEqual(sess['user_name'], "Test User")
            self.assertEqual(sess['user_id'], "12345sub")
            self.assertNotIn('state', sess) # State should be popped

    def test_auth_callback_state_mismatch(self):
        with self.client.session_transaction() as sess:
            sess['state'] = "original_state"
        
        response = self.client.get('/auth/callback?state=tampered_state&code=auth_code')
        self.assertEqual(response.status_code, 403) # Forbidden due to state mismatch

    @patch('web_app.Flow.from_client_config')
    def test_auth_callback_token_fetch_failure(self, mock_flow_from_config):
        mock_flow_instance = MagicMock()
        mock_flow_instance.fetch_token.side_effect = Exception("Token fetch failed")
        mock_flow_from_config.return_value = mock_flow_instance

        with self.client.session_transaction() as sess:
            sess['state'] = "test_state_for_fail"
        
        response = self.client.get('/auth/callback?state=test_state_for_fail&code=auth_code')
        self.assertEqual(response.status_code, 302) # Redirects to login
        self.assertTrue(response.location.endswith('/login'))
        # Check for flashed message
        with self.client.session_transaction() as sess:
            flashed_messages = sess.get('_flashes', [])
            self.assertTrue(any("Authentication failed: Token fetch failed" in msg[1] for msg in flashed_messages))


    def test_logout(self):
        # First, "log in" a user by setting session variables directly
        with self.client.session_transaction() as sess:
            sess['credentials_json'] = '{"token": "dummy"}'
            sess['user_email'] = "test@example.com"
            sess['user_name'] = "Test User"
            sess['user_id'] = "test_id_123"
            sess['state'] = "some_oauth_state" # Should also be cleared by logout

        response = self.client.get('/logout', follow_redirects=True)
        self.assertEqual(response.status_code, 200) # After redirect to index, which then redirects to login
        self.assertTrue(response.request.path.endswith('/login')) # Check final path after redirects
        
        with self.client.session_transaction() as sess:
            self.assertNotIn('credentials_json', sess)
            self.assertNotIn('user_email', sess)
            self.assertNotIn('user_name', sess)
            self.assertNotIn('user_id', sess)
            self.assertNotIn('state', sess)

    # --- Test Authenticated Routes ---
    def _login_user(self, client):
        """Helper function to simulate a user login by setting session variables."""
        with client.session_transaction() as sess:
            sess['credentials_json'] = json.dumps({
                'token': 'mock_access_token',
                'refresh_token': 'mock_refresh_token',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'client_id': 'test_client_id.apps.googleusercontent.com',
                'client_secret': 'test_client_secret',
                'scopes': ['openid', 'https://www.googleapis.com/auth/analytics.readonly']
            })
            sess['user_email'] = "test@example.com"
            sess['user_name'] = "Test User"
            sess['user_id'] = "test_user_sub_id"

    def test_chat_interface_authenticated(self):
        self._login_user(self.client)
        response = self.client.get('/chat-interface')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Chat with Jules", response.data)
        self.assertIn(b"Welcome, Test User!", response.data)

    @patch('web_app.parse_query')
    @patch('web_app.get_report_with_user_creds')
    @patch('web_app.generate_response')
    def test_chat_post_authenticated_success(
        self, mock_generate_response, mock_get_report_creds, mock_parse_query
    ):
        self._login_user(self.client)

        mock_parse_query.return_value = {
            "metrics": ["activeUsers"], "dimensions": ["date"],
            "date_ranges": [{"start_date": "2024-01-01", "end_date": "2024-01-01"}],
            "original_query": "active users yesterday"
        }
        mock_ga4_response = MockWebAppRunReportResponse(rows_data=["mock GA4 data"])
        mock_get_report_creds.return_value = (mock_ga4_response, None) # (data, error_message)
        mock_generate_response.return_value = "Here are your active users: 100."

        response = self.client.post('/chat', json={'query': 'active users yesterday'})
        
        self.assertEqual(response.status_code, 200)
        json_response = json.loads(response.data)
        self.assertEqual(json_response['ai_response'], "Here are your active users: 100.")
        mock_parse_query.assert_called_once_with('active users yesterday')
        mock_get_report_creds.assert_called_once()
        # We can add more specific assertions for args passed to get_report_with_user_creds
        self.assertEqual(mock_get_report_creds.call_args[1]['property_id'], os.getenv("GA4_PROPERTY_ID") or "YOUR_GA4_PROPERTY_ID") # Checks default logic
        mock_generate_response.assert_called_once()


    @patch('web_app.parse_query')
    def test_chat_post_authenticated_nlu_fails(self, mock_parse_query):
        self._login_user(self.client)
        mock_parse_query.return_value = {
            "error": "NLU parsing failed badly",
            "original_query": "gibberish query"
            # Other default keys from nlu_processor error response
        }
        response = self.client.post('/chat', json={'query': 'gibberish query'})
        self.assertEqual(response.status_code, 400)
        json_response = json.loads(response.data)
        self.assertIn("error", json_response)
        self.assertIn("I had trouble understanding your request: NLU parsing failed badly", json_response['error'])


    @patch('web_app.parse_query')
    @patch('web_app.get_report_with_user_creds')
    @patch('web_app.generate_response') # To see if it's called or not
    def test_chat_post_authenticated_ga4_fails_no_reauth(
        self, mock_generate_response, mock_get_report_creds, mock_parse_query
    ):
        self._login_user(self.client)
        mock_parse_query.return_value = {
            "metrics": ["sessions"], "dimensions": ["country"],
            "date_ranges": [{"start_date": "7daysAgo", "end_date": "today"}],
            "original_query": "sessions by country"
        }
        ga4_error_message = "GA4 API reported some specific error (e.g. invalid metric)"
        mock_get_report_creds.return_value = (None, ga4_error_message) # GA4 error, no re-auth needed
        
        # The response generator should still be called to formulate a user-friendly message
        # based on the error string passed via format_ga4_response_for_prompt
        mock_generate_response.return_value = f"Jules: I couldn't get that data due to an issue: {ga4_error_message}"

        response = self.client.post('/chat', json={'query': 'sessions by country'})
        self.assertEqual(response.status_code, 200) # The /chat endpoint itself didn't fail, it's passing GA4 error to LLM
        json_response = json.loads(response.data)
        self.assertIn(f"Jules: I couldn't get that data due to an issue: {ga4_error_message}", json_response['ai_response'])
        mock_get_report_creds.assert_called_once()
        mock_generate_response.assert_called_once()


    @patch('web_app.parse_query')
    @patch('web_app.get_report_with_user_creds')
    def test_chat_post_authenticated_ga4_fails_reauth_required(
        self, mock_get_report_creds, mock_parse_query
    ):
        self._login_user(self.client)
        mock_parse_query.return_value = {
            "metrics": ["sessions"], "dimensions": ["country"],
            "date_ranges": [{"start_date": "7daysAgo", "end_date": "today"}],
            "original_query": "sessions by country"
        }
        # Crucially, the error message from ga4_client must contain "(re-login required)"
        ga4_error_message = "Token expired or revoked (re-login required)" 
        mock_get_report_creds.return_value = (None, ga4_error_message)

        response = self.client.post('/chat', json={'query': 'sessions by country'})
        self.assertEqual(response.status_code, 401)
        json_response = json.loads(response.data)
        self.assertIn("error", json_response)
        self.assertTrue(json_response.get("re_auth_required", False))
        self.assertIn("GA4 Authentication Error", json_response['error'])
        self.assertIn(ga4_error_message, json_response['error'])


if __name__ == '__main__':
    unittest.main()
