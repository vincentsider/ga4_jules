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
