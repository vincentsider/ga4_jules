import os
import json
from openai import OpenAI, APIError, APIConnectionError, RateLimitError, AuthenticationError

# Initialize the OpenAI client
# The client automatically picks up the OPENAI_API_KEY from the environment variables.
# This initial check is more for early feedback; the actual error handling will be in generate_response.
try:
    if os.getenv("OPENAI_API_KEY"):
        client = OpenAI()
    else:
        client = None # Explicitly set to None if key is missing
        print("Warning: OPENAI_API_KEY environment variable not set. Response generation will fail.")
except Exception as e: # Catch other potential init errors
    print(f"Error initializing OpenAI client: {e}")
    client = None

def format_ga4_response_for_prompt(ga4_response_or_error_msg: any, nlu_data: dict) -> str:
    """
    Formats the GA4 RunReportResponse object into a string or simplified structure
    suitable for inclusion in an LLM prompt.
    Handles actual GA4 RunReportResponse objects, mock dictionary data, or error message strings.
    """
    if not ga4_response_or_error_msg: # Handles None or empty string
        return "No data or error message was provided from the Google Analytics step."

    # If ga4_response_or_error_msg is an error string from ga4_client.py or app.py
    if isinstance(ga4_response_or_error_msg, str):
        return f"An issue was encountered while fetching data: {ga4_response_or_error_msg}"

    # Attempt to handle actual RunReportResponse object (from google.analytics.data_v1beta.types)
    try:
        if hasattr(ga4_response_or_error_msg, 'rows'): # Check for a key attribute of RunReportResponse
            if not ga4_response_or_error_msg.rows:
                return "The report from Google Analytics contained no data rows for your query."

            headers = []
            if hasattr(ga4_response_or_error_msg, 'dimension_headers'):
                headers.extend([header.name for header in ga4_response_or_error_msg.dimension_headers])
            if hasattr(ga4_response_or_error_msg, 'metric_headers'):
                headers.extend([header.name for header in ga4_response_or_error_msg.metric_headers])

            output_lines = ["Data summary from Google Analytics:"]
            if headers:
                # Use headers from NLU data if available and more descriptive, otherwise use GA4's
                nlu_dims = nlu_data.get("dimensions", [])
                nlu_mets = nlu_data.get("metrics", [])
                if len(nlu_dims) + len(nlu_mets) == len(headers): # Basic check
                    prompt_headers = nlu_dims + nlu_mets
                    output_lines.append("Columns: " + ", ".join(prompt_headers))
                else:
                    output_lines.append("Columns: " + ", ".join(headers))


            for i, row in enumerate(ga4_response_or_error_msg.rows):
                if i >= 7: # Limit rows in prompt to keep it concise
                    output_lines.append(f"... and {len(ga4_response_or_error_msg.rows) - 7} more data rows.")
                    break
                row_values = []
                if hasattr(row, 'dimension_values'):
                    row_values.extend([dim_value.value for dim_value in row.dimension_values])
                if hasattr(row, 'metric_values'):
                    row_values.extend([met_value.value for met_value in row.metric_values])
                output_lines.append(" - " + ", ".join(row_values))
            return "\n".join(output_lines)
    except Exception as e:
        print(f"Error formatting actual GA4 RunReportResponse object: {e}")
        # Fallback if GA4 object processing fails unexpectedly
        return "There was an issue trying to format the data received from Google Analytics."


    # If it's a dictionary (e.g. mock data for testing)
    if isinstance(ga4_response_or_error_msg, dict) and "rows" in ga4_response_or_error_msg:
        rows = ga4_response_or_error_msg.get("rows", [])
        if not rows:
            return "The report from Google Analytics (mock data) contained no data rows."

        dimension_headers = nlu_data.get("dimensions", ["Dimension"])
        metric_headers = nlu_data.get("metrics", ["Metric"])
        
        formatted_rows = ["Data summary (from mock data):"]
        for i, row in enumerate(rows):
            if i >= 7: # Limit rows
                formatted_rows.append(f"... and {len(rows) - 7} more rows.")
                break
            dim_values = [dv.get("value", "N/A") for dv in row.get("dimension_values", [])]
            met_values = [mv.get("value", "N/A") for mv in row.get("metric_values", [])]
            
            row_str_parts = []
            for d_idx, d_val in enumerate(dim_values):
                header = dimension_headers[d_idx] if d_idx < len(dimension_headers) else f"Dimension {d_idx+1}"
                row_str_parts.append(f"{header}: {d_val}")
            for m_idx, m_val in enumerate(met_values):
                header = metric_headers[m_idx] if m_idx < len(metric_headers) else f"Metric {m_idx+1}"
                row_str_parts.append(f"{header}: {m_val}")
            formatted_rows.append(" - " + ", ".join(row_str_parts))
        return "\n".join(formatted_rows)

    # Fallback for unhandled types or structures
    return "Could not format the GA4 response. It might be empty or in an unexpected format."


def generate_response(nlu_data: dict, ga4_data_summary: str) -> str:
    """
    Generates a human-readable response using OpenAI based on NLU data and GA4 results.

    Args:
        nlu_data: The dictionary output from the NLU processor.
        ga4_data_summary: A string summary of the data retrieved from GA4.

    Returns:
        A string containing the AI-generated response, or an error message.
    """
    default_error_message = "I'm sorry, I encountered an issue while trying to generate a response."

    if not client:
        return "OpenAI client not initialized. Cannot generate response. Is OPENAI_API_KEY set?"

    original_query = nlu_data.get("original_query", "the user's request")
    query_type = nlu_data.get("query_type", "data analysis")

    # Ensure nlu_data is not None and contains original_query
    if not nlu_data or not original_query:
        return f"{default_error_message} (Missing NLU data for context)."

    system_prompt = f"""
You are a friendly and highly intelligent AI assistant specializing in Google Analytics 4 data interpretation.
Your goal is to provide a concise, clear, and helpful answer to the user's query based on the data provided.

User's original query: "{original_query}"
Identified query type/goal: "{query_type}"

Analytics Data Summary:
---
{ga4_data_summary}
---

Please analyze the data summary above and generate a response that directly answers the user's query.
Key instructions:
1.  **Direct Answer:** Focus on answering the user's specific question as stated in their "original query".
2.  **Clarity and Conciseness:** Make your response easy to understand. Avoid jargon where possible, or explain it briefly.
3.  **Summarize:** If there are many data points, summarize the key findings (e.g., top 3-5 results). Don't just list all data rows unless the query implies it (e.g., "list all...").
4.  **User-Friendly Language:** Present data in a natural way. For example, instead of "city: London, activeUsers: 1000", say "London had 1,000 active users."
5.  **Handle No Data:** If the data summary indicates "No data was returned" or "contained no data rows," clearly and politely state that no information was found for their request. Don't try to invent data.
6.  **Conversational Tone:** Be helpful and approachable.
7.  **Acknowledge Limitations:** If the data seems incomplete to fully answer the query, you can mention that.
8.  **Do not output JSON or raw data lists.** Your response should be a natural language paragraph or a short, formatted list if appropriate for readability.

Example of a good response:
"For your query about active users in the United States yesterday, New York City had the most, with 1,200 active users, followed by Los Angeles with 950, and Chicago with 700. It looks like these three cities account for the majority of activity."

Example of handling no data:
"I looked into the active users for the specified period, but it seems there was no data returned from Google Analytics for your request."
"""

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                }
            ],
            model="gpt-3.5-turbo",
        )
        
        if chat_completion.choices and chat_completion.choices[0].message:
            response_content = chat_completion.choices[0].message.content
            if response_content and response_content.strip():
                return response_content.strip()
            else:
                print("OpenAI response content was empty.")
                return f"{default_error_message} (The AI returned an empty response.)"
        else:
            print("OpenAI response structure was unexpected (missing choices or message).")
            return f"{default_error_message} (The AI response was not in the expected format.)"

    except AuthenticationError as e:
        error_msg = f"OpenAI Authentication Error during response generation: {e}. Check your API key."
        print(error_msg)
        return f"{default_error_message} (Authentication failed)"
    except RateLimitError as e:
        error_msg = f"OpenAI Rate Limit Error during response generation: {e}."
        print(error_msg)
        return f"{default_error_message} (Rate limit exceeded)"
    except APIConnectionError as e:
        error_msg = f"OpenAI API Connection Error during response generation: {e}."
        print(error_msg)
        return f"{default_error_message} (Network connection issue)"
    except APIError as e: # Catch-all for other OpenAI specific API errors
        error_msg = f"OpenAI API Error during response generation: {e} (Status code: {e.status_code}, Type: {e.type})"
        print(error_msg)
        return f"{default_error_message} (API issue: {e.status_code})"
    except Exception as e: # General catch-all for unexpected errors
        error_msg = f"An unexpected error occurred during response generation: {e}"
        print(error_msg)
        return f"{default_error_message} (Unexpected error: {type(e).__name__})"

if __name__ == "__main__":
    # Test client initialization
    if not client and os.getenv("OPENAI_API_KEY"):
        try:
            client = OpenAI()
            print("OpenAI client re-initialized for __main__ test.")
        except Exception as e:
            print(f"Failed to re-initialize OpenAI client for test: {e}")
            
    if not client:
        print("OpenAI client failed to initialize. Ensure OPENAI_API_KEY is set for the example.")
    else:
        print("OpenAI client initialized for example usage.")

        # 1. Mock NLU Data
        mock_nlu_data = {
            "original_query": "What were my top 3 cities by active users last week?",
            "query_type": "top_cities_by_users",
            "metrics": ["activeUsers"],
            "dimensions": ["city"],
            "date_ranges": [{"start_date": "2024-03-04", "end_date": "2024-03-10"}], # Example dates
            "limit": 3
        }

        # 2. Mock GA4 Response Data (simplified dictionary)
        mock_ga4_response_data_success = {
            "rows": [
                {"dimension_values": [{"value": "London"}], "metric_values": [{"value": "1250"}]},
                {"dimension_values": [{"value": "New York"}], "metric_values": [{"value": "980"}]},
                {"dimension_values": [{"value": "Paris"}], "metric_values": [{"value": "750"}]},
                {"dimension_values": [{"value": "Tokyo"}], "metric_values": [{"value": "600"}]},
                {"dimension_values": [{"value": "Berlin"}], "metric_values": [{"value": "550"}]},
            ]
        }
        
        mock_ga4_response_no_data = {
            "rows": []
        }

        mock_ga4_response_error_string = "An error occurred while fetching data from Google Analytics: API Quota Exceeded."

        # Format the GA4 data for the prompt
        formatted_ga4_summary_success = format_ga4_response_for_prompt(mock_ga4_response_data_success, mock_nlu_data)
        formatted_ga4_summary_no_data = format_ga4_response_for_prompt(mock_ga4_response_no_data, mock_nlu_data)
        formatted_ga4_summary_error = format_ga4_response_for_prompt(mock_ga4_response_error_string, mock_nlu_data)

        print("\n--- Example 1: Successful Data Retrieval ---")
        print(f"NLU Data: {json.dumps(mock_nlu_data, indent=2)}")
        print(f"Formatted GA4 Summary:\n{formatted_ga4_summary_success}")
        ai_response_success = generate_response(mock_nlu_data, formatted_ga4_summary_success)
        print(f"\nAI Generated Response:\n{ai_response_success}")

        print("\n--- Example 2: No Data Returned ---")
        mock_nlu_no_data_query = {**mock_nlu_data, "original_query": "Page views for non-existent page?"}
        print(f"NLU Data: {json.dumps(mock_nlu_no_data_query, indent=2)}")
        print(f"Formatted GA4 Summary:\n{formatted_ga4_summary_no_data}")
        ai_response_no_data = generate_response(mock_nlu_no_data_query, formatted_ga4_summary_no_data)
        print(f"\nAI Generated Response:\n{ai_response_no_data}")

        print("\n--- Example 3: GA4 Error String ---")
        mock_nlu_error_query = {**mock_nlu_data, "original_query": "What happened with my report?"}
        print(f"NLU Data: {json.dumps(mock_nlu_error_query, indent=2)}")
        print(f"Formatted GA4 Summary:\n{formatted_ga4_summary_error}")
        ai_response_error = generate_response(mock_nlu_error_query, formatted_ga4_summary_error)
        print(f"\nAI Generated Response:\n{ai_response_error}")

        # Example with a slightly different query and data structure
        mock_nlu_data_landing = {
            "original_query": "What were my top landing pages by sessions yesterday?",
            "query_type": "top_landing_pages_by_sessions",
            "metrics": ["sessions"],
            "dimensions": ["landingPage"],
            "date_ranges": [{"start_date": "2024-03-10", "end_date": "2024-03-10"}],
            "limit": 2
        }
        mock_ga4_response_landing = {
            "rows": [
                {"dimension_values": [{"value": "/home"}], "metric_values": [{"value": "500"}]},
                {"dimension_values": [{"value": "/product/cool-widget"}], "metric_values": [{"value": "350"}]},
                {"dimension_values": [{"value": "/contact-us"}], "metric_values": [{"value": "120"}]},
            ]
        }
        formatted_ga4_summary_landing = format_ga4_response_for_prompt(mock_ga4_response_landing, mock_nlu_data_landing)
        print("\n--- Example 4: Top Landing Pages ---")
        print(f"NLU Data: {json.dumps(mock_nlu_data_landing, indent=2)}")
        print(f"Formatted GA4 Summary:\n{formatted_ga4_summary_landing}")
        ai_response_landing = generate_response(mock_nlu_data_landing, formatted_ga4_summary_landing)
        print(f"\nAI Generated Response:\n{ai_response_landing}")
