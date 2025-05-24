import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import json
from datetime import datetime, timedelta

# Ensure src directory is in Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Import functions/classes to be tested
from nlu_processor import parse_query, get_date_range_for_relative_query
# Import OpenAI error classes that might be raised and caught
from openai import APIError, RateLimitError, APIConnectionError, AuthenticationError, OpenAIError

# Mock for openai.Client().chat.completions.create
# This needs to be a class that can be instantiated, and its create method can be mocked.
class MockChatCompletionChoice:
    def __init__(self, content):
        self.message = MagicMock()
        self.message.content = content

class MockChatCompletion:
    def __init__(self, content_or_exception):
        if isinstance(content_or_exception, OpenAIError):
            self.choices = [] # Or None, depending on how OpenAI client behaves on error before choices
            self.message = None # Ensure it doesn't try to access message.content
            self.side_effect_exception = content_or_exception
        else:
            self.choices = [MockChatCompletionChoice(content_or_exception)]
            self.side_effect_exception = None

    def __call__(self, *args, **kwargs): # To make the instance itself callable for side_effect
        if self.side_effect_exception:
            raise self.side_effect_exception
        return self # Return self, so attributes like choices can be accessed


class TestNLUProcessor(unittest.TestCase):

    def setUp(self):
        self.user_query = "show me active users yesterday"
        self.today = datetime.today()
        self.yesterday_str = (self.today - timedelta(days=1)).strftime("%Y-%m-%d")
        self.default_error_keys = [
            "error", "original_query", "metrics", "dimensions", 
            "date_ranges", "filters", "query_type", "limit", "raw_openai_response"
        ]

    @patch('nlu_processor.client') # Patch the client instance in nlu_processor
    def test_parse_query_success_simple(self, MockOpenAIClient):
        expected_json_str = json.dumps({
            "metrics": ["activeUsers"],
            "dimensions": ["date"],
            "date_ranges": [{"start_date": self.yesterday_str, "end_date": self.yesterday_str}],
            "original_query": self.user_query,
            "query_type": "metric_by_date" 
            # other keys will be set by setdefault in parse_query
        })
        
        # Configure the mock client's chat.completions.create method
        MockOpenAIClient.chat.completions.create = MagicMock(return_value=MockChatCompletion(expected_json_str))

        result = parse_query(self.user_query)

        MockOpenAIClient.chat.completions.create.assert_called_once()
        self.assertEqual(result["metrics"], ["activeUsers"])
        self.assertEqual(result["date_ranges"][0]["start_date"], self.yesterday_str)
        self.assertIsNone(result.get("error")) # No error key or error is None

    def test_get_date_range_for_relative_query(self):
        # Yesterday
        start, end = get_date_range_for_relative_query("yesterday")
        self.assertEqual(start, (self.today - timedelta(days=1)).strftime("%Y-%m-%d"))
        self.assertEqual(end, (self.today - timedelta(days=1)).strftime("%Y-%m-%d"))

        # Last 7 days
        start, end = get_date_range_for_relative_query("last 7 days")
        self.assertEqual(start, (self.today - timedelta(days=7)).strftime("%Y-%m-%d"))
        self.assertEqual(end, self.today.strftime("%Y-%m-%d"))
        
        # Today
        start, end = get_date_range_for_relative_query("today")
        self.assertEqual(start, self.today.strftime("%Y-%m-%d"))
        self.assertEqual(end, self.today.strftime("%Y-%m-%d"))

        # Last week (Mon-Sun)
        last_day_of_last_week = self.today - timedelta(days=self.today.weekday() + 1)
        first_day_of_last_week = last_day_of_last_week - timedelta(days=6)
        start, end = get_date_range_for_relative_query("last week")
        self.assertEqual(start, first_day_of_last_week.strftime("%Y-%m-%d"))
        self.assertEqual(end, last_day_of_last_week.strftime("%Y-%m-%d"))

        # Last month
        first_day_current_month = self.today.replace(day=1)
        last_day_last_month = first_day_current_month - timedelta(days=1)
        first_day_last_month = last_day_last_month.replace(day=1)
        start, end = get_date_range_for_relative_query("last month")
        self.assertEqual(start, first_day_last_month.strftime("%Y-%m-%d"))
        self.assertEqual(end, last_day_last_month.strftime("%Y-%m-%d"))
        
        # Non-relative
        self.assertIsNone(get_date_range_for_relative_query("June 5th"))


    @patch('nlu_processor.client')
    def test_parse_query_openai_rate_limit_error(self, MockOpenAIClient):
        MockOpenAIClient.chat.completions.create = MagicMock(side_effect=RateLimitError("Rate limit exceeded", response=MagicMock(), body=None))
        
        result = parse_query(self.user_query)
        
        self.assertIsNotNone(result.get("error"))
        self.assertIn("OpenAI Rate Limit Error", result["error"])
        for key in self.default_error_keys:
            self.assertIn(key, result)

    @patch('nlu_processor.client')
    def test_parse_query_openai_authentication_error(self, MockOpenAIClient):
        MockOpenAIClient.chat.completions.create = MagicMock(side_effect=AuthenticationError("Auth error", response=MagicMock(), body=None))
        
        result = parse_query(self.user_query)
        
        self.assertIsNotNone(result.get("error"))
        self.assertIn("OpenAI Authentication Error", result["error"])

    @patch('nlu_processor.client')
    def test_parse_query_openai_api_error(self, MockOpenAIClient):
        # For APIError, ensure the mock response has a status_code if your error message uses it
        mock_response = MagicMock()
        mock_response.status_code = 400 # Example status code
        MockOpenAIClient.chat.completions.create = MagicMock(side_effect=APIError("Generic API error", response=mock_response, body=None))
        
        result = parse_query(self.user_query)
        
        self.assertIsNotNone(result.get("error"))
        self.assertIn("OpenAI API Error", result["error"])
        self.assertIn("(Status code: 400", result["error"]) # Check if status code is in the message

    @patch('nlu_processor.client')
    def test_parse_query_json_decode_error(self, MockOpenAIClient):
        malformed_json_str = '{"metrics": ["activeUsers"], "date_ranges": [{"start_date": "2024-01-01"}' # Missing closing brace and original_query
        MockOpenAIClient.chat.completions.create = MagicMock(return_value=MockChatCompletion(malformed_json_str))
        
        result = parse_query(self.user_query)
        
        self.assertIsNotNone(result.get("error"))
        self.assertIn("Failed to parse JSON response from OpenAI", result["error"])
        self.assertEqual(result["raw_openai_response"], malformed_json_str)

    @patch('nlu_processor.os.getenv') # Patch os.getenv specifically for OPENAI_API_KEY
    @patch('nlu_processor.OpenAI') # Patch the OpenAI class constructor
    def test_parse_query_missing_openai_key(self, MockOpenAIClass, MockGetenv):
        MockGetenv.return_value = None # Simulate OPENAI_API_KEY not being set
        
        # Temporarily modify nlu_processor.client for this test case
        # This simulates the client variable being None due to failed initialization
        original_client = sys.modules['nlu_processor'].client
        sys.modules['nlu_processor'].client = None
        
        try:
            result = parse_query(self.user_query)
            self.assertIsNotNone(result.get("error"))
            self.assertIn("OpenAI client not initialized. Is OPENAI_API_KEY set?", result["error"])
        finally:
            # Restore the original client to avoid affecting other tests
            sys.modules['nlu_processor'].client = original_client
            # Reset mocks if necessary, though patching os.getenv locally should be fine
            MockGetenv.assert_any_call("OPENAI_API_KEY") # Ensure it was checked

    @patch('nlu_processor.client')
    def test_parse_query_empty_response_content(self, MockOpenAIClient):
        MockOpenAIClient.chat.completions.create = MagicMock(return_value=MockChatCompletion("")) # Empty string content
        
        result = parse_query(self.user_query)
        
        self.assertIsNotNone(result.get("error"))
        self.assertIn("Empty response content from OpenAI", result["error"])

if __name__ == '__main__':
    unittest.main()
