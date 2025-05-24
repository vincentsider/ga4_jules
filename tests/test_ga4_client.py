import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Ensure src directory is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from ga4_client import get_basic_report, GA4_PROPERTY_ID
from google.analytics.data_v1beta.types import RunReportResponse
from google.api_core.exceptions import (
    GoogleAPICallError,
    RetryError,
    InvalidArgument,
    PermissionDenied,
    ResourceExhausted,
    ServiceUnavailable,
    DeadlineExceeded,
)

class TestGA4Client(unittest.TestCase):

    def setUp(self):
        self.property_id = "123456789"
        self.dimensions = ["city"]
        self.metrics = ["activeUsers"]
        self.start_date = "2024-01-01"
        self.end_date = "2024-01-07"

    @patch('ga4_client.BetaAnalyticsDataClient')
    def test_get_basic_report_success(self, MockAnalyticsClient):
        mock_client_instance = MockAnalyticsClient.return_value
        mock_response = MagicMock(spec=RunReportResponse)
        mock_client_instance.run_report.return_value = mock_response

        response, error = get_basic_report(
            self.property_id, self.dimensions, self.metrics, self.start_date, self.end_date
        )

        self.assertEqual(response, mock_response)
        self.assertIsNone(error)
        mock_client_instance.run_report.assert_called_once()
        # Further assertions could check the request object passed to run_report

    @patch('ga4_client.BetaAnalyticsDataClient')
    def test_get_basic_report_invalid_argument(self, MockAnalyticsClient):
        mock_client_instance = MockAnalyticsClient.return_value
        mock_client_instance.run_report.side_effect = InvalidArgument("Test Invalid Argument")

        response, error = get_basic_report(
            self.property_id, self.dimensions, self.metrics, self.start_date, self.end_date
        )
        
        self.assertIsNone(response)
        self.assertIn("GA4 API Invalid Argument: Test Invalid Argument", error)

    @patch('ga4_client.BetaAnalyticsDataClient')
    def test_get_basic_report_permission_denied(self, MockAnalyticsClient):
        mock_client_instance = MockAnalyticsClient.return_value
        mock_client_instance.run_report.side_effect = PermissionDenied("Test Permission Denied")

        response, error = get_basic_report(
            self.property_id, self.dimensions, self.metrics, self.start_date, self.end_date
        )
        self.assertIsNone(response)
        self.assertIn("GA4 API Permission Denied: Test Permission Denied", error)

    @patch('ga4_client.BetaAnalyticsDataClient')
    def test_get_basic_report_resource_exhausted(self, MockAnalyticsClient):
        mock_client_instance = MockAnalyticsClient.return_value
        mock_client_instance.run_report.side_effect = ResourceExhausted("Test Resource Exhausted")

        response, error = get_basic_report(
            self.property_id, self.dimensions, self.metrics, self.start_date, self.end_date
        )
        self.assertIsNone(response)
        self.assertIn("GA4 API Resource Exhausted: Test Resource Exhausted", error)

    @patch('ga4_client.BetaAnalyticsDataClient')
    def test_get_basic_report_service_unavailable(self, MockAnalyticsClient):
        mock_client_instance = MockAnalyticsClient.return_value
        mock_client_instance.run_report.side_effect = ServiceUnavailable("Test Service Unavailable")

        response, error = get_basic_report(
            self.property_id, self.dimensions, self.metrics, self.start_date, self.end_date
        )
        self.assertIsNone(response)
        self.assertIn("GA4 API Service Unavailable or Timeout: Test Service Unavailable", error)

    @patch('ga4_client.BetaAnalyticsDataClient')
    def test_get_basic_report_deadline_exceeded(self, MockAnalyticsClient):
        mock_client_instance = MockAnalyticsClient.return_value
        mock_client_instance.run_report.side_effect = DeadlineExceeded("Test Deadline Exceeded")

        response, error = get_basic_report(
            self.property_id, self.dimensions, self.metrics, self.start_date, self.end_date
        )
        self.assertIsNone(response)
        self.assertIn("GA4 API Service Unavailable or Timeout: Test Deadline Exceeded", error)

    @patch('ga4_client.BetaAnalyticsDataClient')
    def test_get_basic_report_google_api_call_error(self, MockAnalyticsClient):
        mock_client_instance = MockAnalyticsClient.return_value
        mock_client_instance.run_report.side_effect = GoogleAPICallError("Test API Call Error")

        response, error = get_basic_report(
            self.property_id, self.dimensions, self.metrics, self.start_date, self.end_date
        )
        self.assertIsNone(response)
        self.assertIn("A Google API Call Error occurred: Test API Call Error", error)
        
    @patch('ga4_client.BetaAnalyticsDataClient')
    def test_get_basic_report_retry_error(self, MockAnalyticsClient):
        mock_client_instance = MockAnalyticsClient.return_value
        mock_client_instance.run_report.side_effect = RetryError("Test Retry Error", cause=None)

        response, error = get_basic_report(
            self.property_id, self.dimensions, self.metrics, self.start_date, self.end_date
        )
        self.assertIsNone(response)
        self.assertIn("A Retryable Error occurred: Test Retry Error", error)

    @patch('ga4_client.BetaAnalyticsDataClient')
    def test_get_basic_report_generic_exception(self, MockAnalyticsClient):
        mock_client_instance = MockAnalyticsClient.return_value
        mock_client_instance.run_report.side_effect = Exception("Test Generic Exception")

        response, error = get_basic_report(
            self.property_id, self.dimensions, self.metrics, self.start_date, self.end_date
        )
        self.assertIsNone(response)
        self.assertIn("An unexpected error occurred in ga4_client: Test Generic Exception", error)

    def test_get_basic_report_missing_parameters(self):
        # Test with missing property_id
        response, error = get_basic_report(
            None, self.dimensions, self.metrics, self.start_date, self.end_date
        )
        self.assertIsNone(response)
        self.assertIn("Missing required parameters", error)

        # Test with missing dimensions
        response, error = get_basic_report(
            self.property_id, [], self.metrics, self.start_date, self.end_date
        )
        self.assertIsNone(response)
        self.assertIn("Missing required parameters", error)
        
        # Test with missing metrics
        response, error = get_basic_report(
            self.property_id, self.dimensions, [], self.start_date, self.end_date
        )
        self.assertIsNone(response)
        self.assertIn("Missing required parameters", error)

if __name__ == '__main__':
    unittest.main()


# --- Tests for get_report_with_user_creds ---
class TestGA4ClientWithUserCreds(unittest.TestCase):

    def setUp(self):
        self.user_credentials_dict = {
            'token': 'mock_access_token',
            'refresh_token': 'mock_refresh_token',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': 'mock_client_id.apps.googleusercontent.com',
            'client_secret': 'mock_client_secret',
            'scopes': ['https://www.googleapis.com/auth/analytics.readonly', 'openid'],
            # 'expiry': '2024-01-01T00:00:00Z' # Example, though not directly used by from_authorized_user_info
        }
        self.property_id = "987654321"
        self.dimensions = ["country"]
        self.metrics = ["sessions"]
        self.start_date = "2024-02-01"
        self.end_date = "2024-02-28"

    @patch('ga4_client.BetaAnalyticsDataClient')
    @patch('ga4_client.Credentials.from_authorized_user_info')
    def test_get_report_with_user_creds_success(self, MockCredentials, MockAnalyticsClient):
        mock_creds_instance = MockCredentials.return_value
        mock_creds_instance.expired = False # Token is not expired

        mock_client_instance = MockAnalyticsClient.return_value
        mock_ga4_response = MagicMock(spec=RunReportResponse)
        mock_client_instance.run_report.return_value = mock_ga4_response

        response, error = get_report_with_user_creds(
            self.user_credentials_dict, self.property_id, self.dimensions, self.metrics,
            self.start_date, self.end_date
        )

        MockCredentials.assert_called_once_with(self.user_credentials_dict)
        MockAnalyticsClient.assert_called_once_with(credentials=mock_creds_instance)
        mock_client_instance.run_report.assert_called_once()
        self.assertEqual(response, mock_ga4_response)
        self.assertIsNone(error)

    @patch('ga4_client.BetaAnalyticsDataClient')
    @patch('ga4_client.Credentials.from_authorized_user_info')
    @patch('ga4_client.google.auth.transport.requests.Request') # Mock the Request object for refresh
    def test_get_report_with_user_creds_token_refresh_success(
        self, MockAuthRequest, MockCredentials, MockAnalyticsClient
    ):
        mock_creds_instance = MockCredentials.return_value
        mock_creds_instance.expired = True # Simulate expired token
        mock_creds_instance.refresh_token = "valid_refresh_token" # Ensure refresh token is present
        mock_creds_instance.refresh = MagicMock() # Mock the refresh method
        mock_creds_instance.to_json = MagicMock(return_value='{"refreshed_token": "new_access_token"}')


        mock_client_instance = MockAnalyticsClient.return_value
        mock_ga4_response = MagicMock(spec=RunReportResponse)
        mock_client_instance.run_report.return_value = mock_ga4_response
        
        mock_session_update_callback = MagicMock()

        response, error = get_report_with_user_creds(
            self.user_credentials_dict, self.property_id, self.dimensions, self.metrics,
            self.start_date, self.end_date, session_update_callback=mock_session_update_callback
        )

        MockCredentials.assert_called_once_with(self.user_credentials_dict)
        mock_creds_instance.refresh.assert_called_once_with(MockAuthRequest.return_value)
        mock_session_update_callback.assert_called_once_with('{"refreshed_token": "new_access_token"}')
        MockAnalyticsClient.assert_called_once_with(credentials=mock_creds_instance)
        self.assertEqual(response, mock_ga4_response)
        self.assertIsNone(error)

    @patch('ga4_client.Credentials.from_authorized_user_info')
    @patch('ga4_client.google.auth.transport.requests.Request')
    def test_get_report_with_user_creds_token_refresh_failure(
        self, MockAuthRequest, MockCredentials
    ):
        mock_creds_instance = MockCredentials.return_value
        mock_creds_instance.expired = True
        mock_creds_instance.refresh_token = "valid_refresh_token"
        # Simulate refresh failure
        from google.auth.exceptions import RefreshError 
        mock_creds_instance.refresh = MagicMock(side_effect=RefreshError("Refresh failed"))
        
        mock_session_update_callback = MagicMock()

        response, error = get_report_with_user_creds(
            self.user_credentials_dict, self.property_id, self.dimensions, self.metrics,
            self.start_date, self.end_date, session_update_callback=mock_session_update_callback
        )
        
        self.assertIsNone(response)
        self.assertIsNotNone(error)
        self.assertIn("Failed to refresh user token: Refresh failed", error)
        self.assertIn("(re-login required)", error)
        mock_session_update_callback.assert_not_called()


    @patch('ga4_client.BetaAnalyticsDataClient')
    @patch('ga4_client.Credentials.from_authorized_user_info')
    def test_get_report_with_user_creds_unauthenticated_error(
        self, MockCredentials, MockAnalyticsClient
    ):
        mock_creds_instance = MockCredentials.return_value
        mock_creds_instance.expired = False
        
        mock_client_instance = MockAnalyticsClient.return_value
        from google.api_core.exceptions import Unauthenticated as APICoreUnauthenticated
        mock_client_instance.run_report.side_effect = APICoreUnauthenticated("User token is invalid")

        response, error = get_report_with_user_creds(
            self.user_credentials_dict, self.property_id, self.dimensions, self.metrics,
            self.start_date, self.end_date
        )

        self.assertIsNone(response)
        self.assertIsNotNone(error)
        self.assertIn("GA4 API User Unauthenticated: User token is invalid", error)
        self.assertIn("(re-login required)", error)

    def test_get_report_with_user_creds_missing_params(self):
        response, error = get_report_with_user_creds(
            self.user_credentials_dict, None, self.dimensions, self.metrics, # Missing property_id
            self.start_date, self.end_date
        )
        self.assertIsNone(response)
        self.assertIn("User report: Missing required parameters", error)

if __name__ == '__main__':
    unittest.main()