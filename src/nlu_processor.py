import os
import json
from openai import OpenAI, APIError, APIConnectionError, RateLimitError, AuthenticationError
from datetime import datetime, timedelta

# Initialize the OpenAI client
# The client automatically picks up the OPENAI_API_KEY from the environment variables.
# This initial check is more for early feedback; the actual error handling will be in parse_query.
try:
    if os.getenv("OPENAI_API_KEY"):
        client = OpenAI()
    else:
        client = None # Explicitly set to None if key is missing
        print("Warning: OPENAI_API_KEY environment variable not set. NLU processing will fail.")
except Exception as e: # Catch other potential init errors
    print(f"Error initializing OpenAI client: {e}")
    client = None

def get_date_range_for_relative_query(query_part: str) -> tuple[str, str] | None:
    """
    Calculates start and end dates for relative date queries like
    "yesterday", "last 7 days", "last week", "last month".
    Assumes "today" is the current date.
    "last week" is defined as Monday to Sunday of the previous week.
    "last month" is defined as the entirety of the previous calendar month.
    """
    today = datetime.today()
    query_part = query_part.lower()

    if "yesterday" in query_part:
        start_date = today - timedelta(days=1)
        return start_date.strftime("%Y-%m-%d"), start_date.strftime("%Y-%m-%d")
    elif "last 7 days" in query_part:
        start_date = today - timedelta(days=7)
        return start_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    elif "last week" in query_part: # Monday to Sunday of the previous week
        last_day_of_last_week = today - timedelta(days=today.weekday() + 1)
        first_day_of_last_week = last_day_of_last_week - timedelta(days=6)
        return first_day_of_last_week.strftime("%Y-%m-%d"), last_day_of_last_week.strftime("%Y-%m-%d")
    elif "last month" in query_part:
        first_day_of_current_month = today.replace(day=1)
        last_day_of_last_month = first_day_of_current_month - timedelta(days=1)
        first_day_of_last_month = last_day_of_last_month.replace(day=1)
        return first_day_of_last_month.strftime("%Y-%m-%d"), last_day_of_last_month.strftime("%Y-%m-%d")
    elif "today" in query_part:
        return today.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    # Add more relative date parsing if needed
    return None


def parse_query(user_query: str) -> dict:
    """
    Parses a natural language query using OpenAI API to extract parameters for GA4.

    Args:
        user_query: The natural language query from the user.

    Returns:
        A dictionary containing extracted parameters like metrics, dimensions, date_ranges, etc.
    """
    default_error_response = {
        "error": "An unspecified error occurred during NLU processing.",
        "original_query": user_query,
        "metrics": [],
        "dimensions": [],
        "date_ranges": [{"start_date": "7daysAgo", "end_date": "today"}], # Sensible default
        "filters": None,
        "query_type": "unknown_query_type",
        "limit": None,
        "raw_openai_response": None # For debugging
    }

    if not client:
        return {**default_error_response, "error": "OpenAI client not initialized. Is OPENAI_API_KEY set?"}

    # Attempt to pre-calculate relative dates to help the model
    # This is a simplified approach; the LLM will also be instructed to handle dates.
    # A more robust solution would involve more sophisticated NLP for date extraction first.
    current_year = datetime.today().year
    prompt_current_date_info = f"Assume the current date is {datetime.today().strftime('%Y-%m-%d')}."

    # Heuristic to identify if a known relative date phrase is in the query
    # to pass to our helper, otherwise let LLM handle it.
    # This can be made more sophisticated.
    pre_calculated_date_range = None
    known_relative_phrases = ["yesterday", "last 7 days", "last week", "last month", "today"]
    for phrase in known_relative_phrases:
        if phrase in user_query.lower():
            pre_calculated_date_range = get_date_range_for_relative_query(phrase)
            if pre_calculated_date_range:
                prompt_current_date_info += (
                    f" The phrase '{phrase}' could correspond to the date range: "
                    f"start_date: {pre_calculated_date_range[0]}, end_date: {pre_calculated_date_range[1]}."
                )
                break
    
    system_prompt = f"""
You are an expert in Google Analytics 4 (GA4) and a helpful assistant.
Your task is to extract specific parameters from a user's query.
{prompt_current_date_info}
Provide the output exclusively in JSON format. Do not add any explanatory text before or after the JSON object.

The JSON object should have the following structure:
{{
  "metrics": ["metricId1", "metricId2"],  // e.g., ["activeUsers", "screenPageViews", "sessions"]
  "dimensions": ["dimensionId1", "dimensionId2"], // e.g., ["landingPage", "country", "city", "date"]
  "date_ranges": [ {{ "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD" }} ], // Convert relative dates (e.g., "yesterday", "last 7 days", "last week", "last month", "this month") to absolute YYYY-MM-DD.
                                                                            // "last week" should be the previous Monday to Sunday.
                                                                            // "last month" should be the entire previous calendar month.
                                                                            // If a specific year is not mentioned for a month (e.g. "show me data for May"), assume the current year ({current_year}).
                                                                            // If a range like "May to June" is given without a year, assume current year.
  "filters": {{ // Optional: only include if filters are clearly specified.
    "dimension_name": "ga4DimensionName", // e.g., "country", "eventName"
    "operator": "OPERATOR_STRING", // e.g., "EQUALS", "CONTAINS", "BEGINS_WITH", "GREATER_THAN" (for numeric metrics if filtering on them)
    "value": "filterValue" // e.g., "France", "page_view"
  }},
  "query_type": "description_of_query_goal", // e.g., "top_pages_summary", "user_activity_by_country", "sessions_trend_over_time", "event_count_for_date_range"
  "limit": null, // Optional: an integer if the user specifies a limit (e.g., "top 5", "top 10")
  "original_query": "The original user query"
}}

Common GA4 Metrics: activeUsers, newUsers, totalUsers, sessions, engagedSessions, screenPageViews, eventCount, conversions.
Common GA4 Dimensions: city, country, date, deviceCategory, landingPage, pagePath, medium, source, eventName, sessionMedium, sessionSource.

Focus on identifying the user's intent for metrics, dimensions, and date ranges.
If a date range is relative (e.g., "last week"), calculate the absolute YYYY-MM-DD dates.
If the user asks for "top X" items, include a "limit": X in the JSON.
For filters, try to map user phrasing to GA4 filter structure. If not clear, omit the "filters" key or set to null.
The "query_type" should be a concise summary of what the user wants.

Example query: "Show me the number of active users and page views from Canada for the last 7 days"
Expected JSON:
{{
  "metrics": ["activeUsers", "screenPageViews"],
  "dimensions": ["country"],
  "date_ranges": [ {{ "start_date": "{ (datetime.today() - timedelta(days=7)).strftime('%Y-%m-%d') }", "end_date": "{ datetime.today().strftime('%Y-%m-%d') }" }} ],
  "filters": {{
    "dimension_name": "country",
    "operator": "EXACTLY_MATCHES", // or "EQUALS"
    "value": "Canada"
  }},
  "query_type": "user_activity_by_country_for_period",
  "limit": null,
  "original_query": "Show me the number of active users and page views from Canada for the last 7 days"
}}

If the query is vague or information is missing, make reasonable assumptions or leave fields as empty lists/null where appropriate, but always return the JSON structure.
"""

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_query,
                }
            ],
            model="gpt-3.5-turbo-0125", # Using a specific sub-version for potentially more consistent JSON output
            response_format={ "type": "json_object" }, # Request JSON output
        )
        
        response_content = chat_completion.choices[0].message.content
        
        if response_content:
            parsed_response = json.loads(response_content)
            # Ensure original_query is always present and other keys have defaults
            parsed_response.setdefault("original_query", user_query)
            parsed_response.setdefault("metrics", [])
            parsed_response.setdefault("dimensions", [])
            parsed_response.setdefault("date_ranges", [{"start_date": "7daysAgo", "end_date": "today"}])
            parsed_response.setdefault("filters", None)
            parsed_response.setdefault("query_type", "unknown_query_type")
            parsed_response.setdefault("limit", None)
            return parsed_response
        else: # Should not happen with JSON mode if API call succeeded, but as a safeguard
            return {**default_error_response, "error": "Empty response content from OpenAI."}

    except AuthenticationError as e:
        error_msg = f"OpenAI Authentication Error: {e}. Check your API key."
        print(error_msg)
        return {**default_error_response, "error": error_msg}
    except RateLimitError as e:
        error_msg = f"OpenAI Rate Limit Error: {e}. Please wait and try again or check your plan."
        print(error_msg)
        return {**default_error_response, "error": error_msg}
    except APIConnectionError as e:
        error_msg = f"OpenAI API Connection Error: {e}. Check your network connection."
        print(error_msg)
        return {**default_error_response, "error": error_msg}
    except APIError as e: # Catch-all for other OpenAI specific API errors
        error_msg = f"OpenAI API Error: {e} (Status code: {e.status_code}, Type: {e.type})"
        print(error_msg)
        return {**default_error_response, "error": error_msg, "raw_openai_response": str(e.response) if hasattr(e, 'response') else None}
    except json.JSONDecodeError as e:
        error_msg = f"Failed to parse JSON response from OpenAI: {e}"
        print(error_msg)
        print(f"Raw response from OpenAI that caused JSON error: {response_content if 'response_content' in locals() else 'N/A'}")
        return {**default_error_response, "error": error_msg, "raw_openai_response": response_content if 'response_content' in locals() else None}
    except Exception as e: # General catch-all for unexpected errors
        error_msg = f"An unexpected error occurred during NLU processing: {e}"
        print(error_msg)
        return {**default_error_response, "error": error_msg}

if __name__ == "__main__":
    # Test client initialization
    if not client and os.getenv("OPENAI_API_KEY"):
        # Attempt re-initialization for the test if key is present but client is None
        # This might happen if the script is imported and then key is set.
        try:
            client = OpenAI()
            print("OpenAI client re-initialized for __main__ test.")
        except Exception as e:
            print(f"Failed to re-initialize OpenAI client for test: {e}")

    if not client:
        print("OpenAI client failed to initialize. Ensure OPENAI_API_KEY is set.")
    else:
        print("OpenAI client initialized.")
        # Test cases
        queries = [
            "What were my top 5 landing pages last week?",
            "Show me active users and total sessions for yesterday from United States.",
            "How many users visited from India and Japan last month?",
            "Number of page views for the page /home today.",
            "What are the total users for the last 30 days?",
            "Show me event counts for 'purchase' events during June 2023"
        ]

        for query in queries:
            print(f"\nProcessing query: '{query}'")
            parsed_result = parse_query(query)
            print(json.dumps(parsed_result, indent=2))

            # Example of using the pre-calculated date logic (for testing the helper)
            print("--- Internal Date Helper Test ---")
            if "last week" in query.lower() :
                 print(f"Relative 'last week' -> {get_date_range_for_relative_query('last week')}")
            if "yesterday" in query.lower():
                 print(f"Relative 'yesterday' -> {get_date_range_for_relative_query('yesterday')}")
            if "last month" in query.lower():
                 print(f"Relative 'last month' -> {get_date_range_for_relative_query('last month')}")
            print("--- End Internal Date Helper Test ---")
