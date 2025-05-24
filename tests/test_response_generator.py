import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import json

# Ensure src directory is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from response_generator import generate_response, format_ga4_response_for_prompt
from openai import APIError, RateLimitError, APIConnectionError, AuthenticationError

# Mock the RunReportResponse class structure that format_ga4_response_for_prompt expects
class MockRunReportResponse:
    def __init__(self, dimension_headers=None, metric_headers=None, rows=None):
        self.dimension_headers = dimension_headers if dimension_headers else []
        self.metric_headers = metric_headers if metric_headers else []
        self.rows = rows if rows else []

class MockDimensionHeader:
    def __init__(self, name):
        self.name = name

class MockMetricHeader:
    def __init__(self, name):
        self.name = name

class MockRow:
    def __init__(self, dimension_values=None, metric_values=None):
        self.dimension_values = [MockDimensionValue(v) for v in dimension_values] if dimension_values else []
        self.metric_values = [MockMetricValue(v) for v in metric_values] if metric_values else []

class MockDimensionValue:
    def __init__(self, value):
        self.value = value

class MockMetricValue:
    def __init__(self, value):
        self.value = value

# Re-using the mock classes from nlu_processor for OpenAI responses
class MockChatCompletionChoice:
    def __init__(self, content):
        self.message = MagicMock()
        self.message.content = content

class MockChatCompletion:
    def __init__(self, content_or_exception):
        if isinstance(content_or_exception, APIError): # Using APIError as a general stand-in for OpenAIError
            self.choices = [] 
            self.message = None 
            self.side_effect_exception = content_or_exception
        else:
            self.choices = [MockChatCompletionChoice(content_or_exception)]
            self.side_effect_exception = None

    def __call__(self, *args, **kwargs): 
        if self.side_effect_exception:
            raise self.side_effect_exception
        return self


class TestResponseGenerator(unittest.TestCase):

    def setUp(self):
        self.nlu_data_simple = {
            "original_query": "Active users yesterday?",
            "query_type": "metric_by_date",
            "metrics": ["activeUsers"],
            "dimensions": ["date"],
            "date_ranges": [{"start_date": "2024-03-10", "end_date": "2024-03-10"}],
        }
        self.nlu_data_complex = {
            "original_query": "Top 3 cities for page views last week?",
            "query_type": "top_cities_by_pageviews",
            "metrics": ["screenPageViews"],
            "dimensions": ["city"],
            "date_ranges": [{"start_date": "2024-03-04", "end_date": "2024-03-10"}],
            "limit": 3
        }
        self.default_error_message_generate = "I'm sorry, I encountered an issue while trying to generate a response."


    # --- Tests for format_ga4_response_for_prompt ---

    def test_format_ga4_response_actual_object_success(self):
        mock_ga4_response = MockRunReportResponse(
            dimension_headers=[MockDimensionHeader("city"), MockDimensionHeader("date")],
            metric_headers=[MockMetricHeader("activeUsers")],
            rows=[
                MockRow(dimension_values=["London", "20240310"], metric_values=["1000"]),
                MockRow(dimension_values=["Paris", "20240310"], metric_values=["800"]),
            ]
        )
        formatted_string = format_ga4_response_for_prompt(mock_ga4_response, self.nlu_data_simple)
        self.assertIn("Data summary from Google Analytics:", formatted_string)
        # NLU data has 'date' as dimension, but GA4 returns 'city', 'date'.
        # The formatter prioritizes GA4 headers if mismatch, which is fine.
        self.assertIn("Columns: city, date, activeUsers", formatted_string)
        self.assertIn("London, 20240310, 1000", formatted_string)
        self.assertIn("Paris, 20240310, 800", formatted_string)

    def test_format_ga4_response_actual_object_nlu_headers_match(self):
        nlu_data_matching = {
            "metrics": ["activeUsers"], "dimensions": ["city", "customEvent:customDimension"]
        }
        mock_ga4_response = MockRunReportResponse(
            dimension_headers=[MockDimensionHeader("city"), MockDimensionHeader("customEvent:customDimension")],
            metric_headers=[MockMetricHeader("activeUsers")],
            rows=[MockRow(dimension_values=["London", "ValueA"], metric_values=["1000"])]
        )
        # Here, nlu_data headers should be preferred as they match GA4 headers in count
        formatted_string = format_ga4_response_for_prompt(mock_ga4_response, nlu_data_matching)
        self.assertIn("Columns: city, customEvent:customDimension, activeUsers", formatted_string)


    def test_format_ga4_response_actual_object_no_rows(self):
        mock_ga4_response = MockRunReportResponse(
            dimension_headers=[MockDimensionHeader("city")],
            metric_headers=[MockMetricHeader("activeUsers")],
            rows=[] # No rows
        )
        formatted_string = format_ga4_response_for_prompt(mock_ga4_response, self.nlu_data_simple)
        self.assertEqual(formatted_string, "The report from Google Analytics contained no data rows for your query.")

    def test_format_ga4_response_error_string_input(self):
        error_msg_from_ga4_client = "GA4 API Permission Denied: Test Permission Denied"
        formatted_string = format_ga4_response_for_prompt(error_msg_from_ga4_client, self.nlu_data_simple)
        self.assertEqual(formatted_string, f"An issue was encountered while fetching data: {error_msg_from_ga4_client}")

    def test_format_ga4_response_none_input(self):
        formatted_string = format_ga4_response_for_prompt(None, self.nlu_data_simple)
        self.assertEqual(formatted_string, "No data or error message was provided from the Google Analytics step.")

    def test_format_ga4_response_mock_dict_data(self):
        mock_dict_response = {
            "rows": [
                {"dimension_values": [{"value": "New York"}], "metric_values": [{"value": "1200"}]},
            ]
        }
        formatted_string = format_ga4_response_for_prompt(mock_dict_response, self.nlu_data_simple)
        self.assertIn("Data summary (from mock data):", formatted_string)
        self.assertIn("date: New York", formatted_string) # NLU dimension is "date", mock data implies "city"
        self.assertIn("activeUsers: 1200", formatted_string)

    def test_format_ga4_response_unhandled_type(self):
        formatted_string = format_ga4_response_for_prompt(12345, self.nlu_data_simple) # Pass an integer
        self.assertEqual(formatted_string, "Could not format the GA4 response. It might be empty or in an unexpected format.")


    # --- Tests for generate_response ---
    @patch('response_generator.client')
    def test_generate_response_success(self, MockOpenAIClient):
        expected_ai_response = "Yesterday, there were 1000 active users."
        MockOpenAIClient.chat.completions.create = MagicMock(return_value=MockChatCompletion(expected_ai_response))
        
        ga4_summary = "Data summary: date: 20240310, activeUsers: 1000"
        ai_response = generate_response(self.nlu_data_simple, ga4_summary)

        self.assertEqual(ai_response, expected_ai_response)
        MockOpenAIClient.chat.completions.create.assert_called_once()
        # We could inspect the prompt passed to create if needed

    @patch('response_generator.client')
    def test_generate_response_ga4_no_data(self, MockOpenAIClient):
        expected_ai_response = "It seems there was no data for active users yesterday."
        MockOpenAIClient.chat.completions.create = MagicMock(return_value=MockChatCompletion(expected_ai_response))
        
        ga4_summary = "The report from Google Analytics contained no data rows for your query."
        ai_response = generate_response(self.nlu_data_simple, ga4_summary)

        self.assertEqual(ai_response, expected_ai_response)
        # Check that the system prompt reflects the "no data" situation
        system_prompt_arg = MockOpenAIClient.chat.completions.create.call_args[1]['messages'][0]['content']
        self.assertIn(ga4_summary, system_prompt_arg)


    @patch('response_generator.client')
    def test_generate_response_openai_api_error(self, MockOpenAIClient):
        MockOpenAIClient.chat.completions.create = MagicMock(
            side_effect=APIError("Test API Error", response=MagicMock(status_code=500), body=None)
        )
        ai_response = generate_response(self.nlu_data_simple, "Some GA4 data")
        self.assertTrue(ai_response.startswith(self.default_error_message_generate))
        self.assertIn("(API issue: 500)", ai_response)

    @patch('response_generator.client')
    def test_generate_response_openai_authentication_error(self, MockOpenAIClient):
        MockOpenAIClient.chat.completions.create = MagicMock(
            side_effect=AuthenticationError("Auth error", response=MagicMock(), body=None)
        )
        ai_response = generate_response(self.nlu_data_simple, "Some GA4 data")
        self.assertTrue(ai_response.startswith(self.default_error_message_generate))
        self.assertIn("(Authentication failed)", ai_response)


    @patch('response_generator.os.getenv')
    @patch('response_generator.OpenAI')
    def test_generate_response_missing_openai_key(self, MockOpenAIClass, MockGetenv):
        MockGetenv.return_value = None
        original_client = sys.modules['response_generator'].client
        sys.modules['response_generator'].client = None # Simulate client not initialized

        try:
            ai_response = generate_response(self.nlu_data_simple, "Some GA4 data")
            self.assertEqual(ai_response, "OpenAI client not initialized. Cannot generate response. Is OPENAI_API_KEY set?")
        finally:
            sys.modules['response_generator'].client = original_client
            MockGetenv.assert_any_call("OPENAI_API_KEY")


    @patch('response_generator.client')
    def test_generate_response_empty_llm_content(self, MockOpenAIClient):
        MockOpenAIClient.chat.completions.create = MagicMock(return_value=MockChatCompletion(""))
        ai_response = generate_response(self.nlu_data_simple, "Some GA4 data")
        self.assertTrue(ai_response.startswith(self.default_error_message_generate))
        self.assertIn("(The AI returned an empty response.)", ai_response)

    def test_generate_response_missing_nlu_data(self):
        ai_response = generate_response(None, "Some GA4 data")
        self.assertTrue(ai_response.startswith(self.default_error_message_generate))
        self.assertIn("(Missing NLU data for context)", ai_response)

        ai_response = generate_response({}, "Some GA4 data") # Empty NLU data
        self.assertTrue(ai_response.startswith(self.default_error_message_generate))
        self.assertIn("(Missing NLU data for context)", ai_response)


if __name__ == '__main__':
    unittest.main()
