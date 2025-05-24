import unittest
from unittest.mock import patch, MagicMock, call
import os
import sys
import io

# Ensure src directory is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Import the functions/classes to be tested or that are part of the flow
# We will be mocking most of these, but importing helps with structure
# and potentially for type hinting if used.
try:
    from app import main_conversation_loop, check_env_and_config
except ImportError as e:
    print(f"Failed to import from app: {e}")
    # This can happen if app.py itself has import issues or if path is wrong.
    # For testing, we might proceed with caution or ensure app.py is importable.
    main_conversation_loop = None # Will be assigned if app.py is importable
    check_env_and_config = None # Will be assigned


# Mock for GA4 RunReportResponse object for tests
class MockAppRunReportResponse:
    def __init__(self, rows_data=None):
        self.rows = rows_data if rows_data is not None else []
        # Add dimension_headers and metric_headers if your app.py or its callees use them directly from this object
        self.dimension_headers = []
        self.metric_headers = []


class TestApp(unittest.TestCase):

    @patch('app.os.getenv')
    def test_check_env_and_config_success(self, mock_getenv):
        # Simulate all environment variables being set correctly
        def getenv_side_effect(key, default=None):
            if key == "OPENAI_API_KEY": return "fake_openai_key"
            if key == "GOOGLE_APPLICATION_CREDENTIALS": return "fake_creds.json" # Will be patched by isfile
            if key == "GA4_PROPERTY_ID": return "fake_ga4_id"
            return default
        mock_getenv.side_effect = getenv_side_effect
        
        with patch('app.os.path.isfile', return_value=True):
             # Patch the DEFAULT_GA4_PROPERTY_ID in the app's context if it's used
            with patch('app.DEFAULT_GA4_PROPERTY_ID', "YOUR_GA4_PROPERTY_ID"): # or some other default
                is_ok, prop_id = check_env_and_config()
        
        self.assertTrue(is_ok)
        self.assertEqual(prop_id, "fake_ga4_id")

    @patch('app.os.getenv')
    @patch('builtins.print') # To suppress print statements during this test
    def test_check_env_and_config_failure_missing_openai_key(self, mock_print, mock_getenv):
        def getenv_side_effect(key, default=None):
            if key == "OPENAI_API_KEY": return None # Missing
            if key == "GOOGLE_APPLICATION_CREDENTIALS": return "fake_creds.json"
            if key == "GA4_PROPERTY_ID": return "fake_ga4_id"
            return default
        mock_getenv.side_effect = getenv_side_effect
        
        with patch('app.os.path.isfile', return_value=True):
            with patch('app.DEFAULT_GA4_PROPERTY_ID', "YOUR_GA4_PROPERTY_ID"):
                 is_ok, _ = check_env_and_config()
        
        self.assertFalse(is_ok)
        # Check if print was called with an error message related to OpenAI key
        # This requires inspecting mock_print.call_args_list
        # For simplicity, we'll assume it prints something and returns False

    @patch('app.os.getenv')
    @patch('builtins.print')
    def test_check_env_and_config_failure_missing_ga4_property_id_and_default(self, mock_print, mock_getenv):
        def getenv_side_effect(key, default=None):
            if key == "OPENAI_API_KEY": return "fake_openai_key"
            if key == "GOOGLE_APPLICATION_CREDENTIALS": return "fake_creds.json"
            if key == "GA4_PROPERTY_ID": return None # Missing
            return default
        mock_getenv.side_effect = getenv_side_effect
        
        with patch('app.os.path.isfile', return_value=True):
            # Simulate default in ga4_client also being the placeholder
            with patch('app.DEFAULT_GA4_PROPERTY_ID', "YOUR_GA4_PROPERTY_ID"):
                is_ok, prop_id = check_env_and_config()
        
        self.assertFalse(is_ok)
        self.assertIsNone(prop_id)


    @patch('builtins.input')
    @patch('app.parse_query')
    @patch('app.get_basic_report')
    @patch('app.format_ga4_response_for_prompt')
    @patch('app.generate_response')
    @patch('builtins.print') # Capture print output
    def test_main_conversation_loop_successful_flow(
        self, mock_print, mock_generate_response, mock_format_ga4, 
        mock_get_basic_report, mock_parse_query, mock_input
    ):
        # Simulate user input: first a query, then "exit"
        mock_input.side_effect = ["show me active users", "exit"]

        # Mock NLU response
        mock_parse_query.return_value = {
            "metrics": ["activeUsers"],
            "dimensions": ["date"],
            "date_ranges": [{"start_date": "yesterday", "end_date": "yesterday"}],
            "original_query": "show me active users",
            "query_type": "user_activity" 
            # No "error" key or "error": None
        }
        # Mock GA4 client response
        mock_ga4_data = MockAppRunReportResponse(rows_data=["some data"]) # Simplified
        mock_get_basic_report.return_value = (mock_ga4_data, None) # (data, error_message)

        # Mock GA4 formatter
        mock_format_ga4.return_value = "Formatted GA4 data: 100 active users on date X."

        # Mock Response generator
        mock_generate_response.return_value = "Jules says: There were 100 active users yesterday."

        # Run the loop (assuming property_id is passed or handled correctly)
        if main_conversation_loop: # Check if import was successful
            main_conversation_loop("test_property_id")

        # Assertions
        mock_parse_query.assert_called_with("show me active users")
        mock_get_basic_report.assert_called_once()
        mock_format_ga4.assert_called_with(mock_ga4_data, mock_parse_query.return_value)
        mock_generate_response.assert_called_with(
            nlu_data=mock_parse_query.return_value,
            ga4_data_summary="Formatted GA4 data: 100 active users on date X."
        )
        
        # Check that "Jules says: ..." was printed
        # This requires inspecting the calls to mock_print
        printed_output = ""
        for call_args in mock_print.call_args_list:
            args, _ = call_args
            if args: # Ensure args is not empty
                printed_output += str(args[0]) + "\n"
        
        self.assertIn("Jules says: There were 100 active users yesterday.", printed_output)
        self.assertIn("Exiting application. Goodbye!", printed_output)


    @patch('builtins.input')
    @patch('app.parse_query')
    @patch('app.get_basic_report') # Should not be called
    @patch('app.generate_response') # Should not be called
    @patch('builtins.print')
    def test_main_conversation_loop_nlu_failure(
        self, mock_print, mock_generate_response, mock_get_basic_report, 
        mock_parse_query, mock_input
    ):
        mock_input.side_effect = ["a very vague query", "exit"]
        mock_parse_query.return_value = {
            "error": "NLU failed to understand", 
            "original_query": "a very vague query",
            # ... other default error keys from nlu_processor
            "metrics": [], "dimensions": [], "date_ranges": [{"start_date": "7daysAgo", "end_date": "today"}],
            "filters": None, "query_type": "unknown_query_type", "limit": None, "raw_openai_response": None
        }

        if main_conversation_loop:
            main_conversation_loop("test_property_id")

        mock_parse_query.assert_called_with("a very vague query")
        mock_get_basic_report.assert_not_called()
        mock_generate_response.assert_not_called()
        
        printed_output = "".join(str(args[0]) for call_args in mock_print.call_args_list for args, _ in [call_args] if args)
        self.assertIn("Jules (NLU Error): I had trouble understanding your request: NLU failed to understand", printed_output)
        self.assertIn("Could you please try rephrasing your query?", printed_output)


    @patch('builtins.input')
    @patch('app.parse_query')
    @patch('app.get_basic_report')
    @patch('app.format_ga4_response_for_prompt')
    @patch('app.generate_response')
    @patch('builtins.print')
    def test_main_conversation_loop_ga4_failure(
        self, mock_print, mock_generate_response, mock_format_ga4,
        mock_get_basic_report, mock_parse_query, mock_input
    ):
        mock_input.side_effect = ["show active users", "exit"]
        mock_parse_query.return_value = {
            "metrics": ["activeUsers"], "dimensions": ["date"],
            "date_ranges": [{"start_date": "yesterday", "end_date": "yesterday"}],
            "original_query": "show active users"
        }
        ga4_error_msg = "GA4 API Permission Denied"
        mock_get_basic_report.return_value = (None, ga4_error_msg) # GA4 client returns error

        # format_ga4_response_for_prompt will receive the error string
        mock_format_ga4.return_value = f"An issue was encountered while fetching data: {ga4_error_msg}"
        
        # generate_response should try to explain the GA4 error
        mock_generate_response.return_value = "Jules says: I couldn't get the data because of a permission issue with Google Analytics."

        if main_conversation_loop:
            main_conversation_loop("test_property_id")

        mock_get_basic_report.assert_called_once()
        mock_format_ga4.assert_called_with(ga4_error_msg, mock_parse_query.return_value)
        mock_generate_response.assert_called_once() # generate_response is still called to explain the error
        
        printed_output = "".join(str(args[0]) for call_args in mock_print.call_args_list for args, _ in [call_args] if args)
        self.assertIn("Jules (GA4 Client Error): Sorry, I couldn't retrieve the data from Google Analytics.", printed_output)
        self.assertIn(f"Reason: {ga4_error_msg}", printed_output)
        self.assertIn("Jules says: I couldn't get the data because of a permission issue with Google Analytics.", printed_output)


    @patch('builtins.input', side_effect=['exit'])
    @patch('builtins.print')
    def test_main_conversation_loop_exit_command(self, mock_print, mock_input):
        if main_conversation_loop:
            main_conversation_loop("test_property_id")
        
        printed_output = "".join(str(args[0]) for call_args in mock_print.call_args_list for args, _ in [call_args] if args)
        self.assertIn("Exiting application. Goodbye!", printed_output)

if __name__ == '__main__':
    unittest.main()
