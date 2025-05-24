import os
import json
from datetime import datetime

# Attempt to import local modules
# These imports will be checked for viability in check_env_and_config()
nlu_processor_module = None
ga4_client_module = None
response_generator_module = None

try:
    from nlu_processor import parse_query
    nlu_processor_module = True
except ImportError:
    print("ERROR: Failed to import 'nlu_processor'. Ensure it's in src/ and no import errors within it.")
    # No exit(1) here, check_env_and_config will handle it.

try:
    from ga4_client import get_basic_report, GA4_PROPERTY_ID as DEFAULT_GA4_PROPERTY_ID
    ga4_client_module = True
except ImportError:
    print("ERROR: Failed to import 'ga4_client'. Ensure it's in src/ and no import errors within it.")

try:
    from response_generator import generate_response, format_ga4_response_for_prompt
    response_generator_module = True
except ImportError:
    print("ERROR: Failed to import 'response_generator'. Ensure it's in src/ and no import errors within it.")


# --- Configuration and Environment Check ---
def check_env_and_config():
    """
    Checks for necessary environment variables, module imports, and configurations.
    Returns True if setup is okay, False otherwise.
    """
    # Check if all modules were imported successfully
    if not all([nlu_processor_module, ga4_client_module, response_generator_module]):
        print("One or more core modules failed to import. Please check the errors above.")
        print("Exiting application.")
        return False, None # Return None for PROPERTY_ID

    print("\n--- Configuration & Setup Check ---")
    config_ok = True
    
    # 1. OpenAI API Key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("ERROR: OPENAI_API_KEY environment variable not found.")
        print("       This is required for understanding your queries and generating responses.")
        print("       Please set this environment variable.")
        config_ok = False
    else:
        print("OpenAI API Key: Found.")

    # 2. Google Application Credentials
    google_app_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not google_app_creds:
        print("ERROR: GOOGLE_APPLICATION_CREDENTIALS environment variable not found.")
        print("       This is required to authenticate with Google Analytics Data API.")
        print("       Please set this to the path of your service account JSON key file.")
        config_ok = False
    elif not os.path.isfile(google_app_creds):
        print(f"ERROR: GOOGLE_APPLICATION_CREDENTIALS file not found at: {google_app_creds}")
        print("       Please ensure the path is correct and the file exists.")
        config_ok = False
    else:
        print("Google Application Credentials: Found and file exists.")

    # 3. GA4 Property ID
    property_id_to_use = os.getenv("GA4_PROPERTY_ID")
    if not property_id_to_use:
        print("INFO: GA4_PROPERTY_ID environment variable not found.")
        if DEFAULT_GA4_PROPERTY_ID == "YOUR_GA4_PROPERTY_ID":
            print("ERROR: The default GA4_PROPERTY_ID in src/ga4_client.py is also not set.")
            print("       Please set the GA4_PROPERTY_ID environment variable or update the default in src/ga4_client.py.")
            config_ok = False
            property_id_to_use = None # Ensure it's None if unusable
        else:
            print(f"       Using default GA4_PROPERTY_ID from src/ga4_client.py: {DEFAULT_GA4_PROPERTY_ID}")
            property_id_to_use = DEFAULT_GA4_PROPERTY_ID
    else:
        print(f"GA4 Property ID: Found in environment variable ({property_id_to_use}).")

    if not config_ok:
        print("-------------------------------------")
        print("ERROR: Configuration issues found. Please address the errors above before running the application.")
        return False, None
        
    print("All critical configurations seem OK.")
    print("-------------------------------------\n")
    return True, property_id_to_use


def main_conversation_loop(property_id: str):
    """
    Main loop for the conversational GA4 data application.
    """
    print("\nWelcome to the GA4 Conversational Interface!")
    print("You can ask questions about your Google Analytics 4 data.")
    print("Type 'exit' or 'quit' to end the conversation.")

    while True:
        user_input = input("\nAsk me about your GA4 data: ").strip()

        if user_input.lower() in ["exit", "quit"]:
            print("Exiting application. Goodbye!")
            break

        if not user_input:
            continue

        # 1. NLU Step
        print("\n--- Step 1: Understanding your query (NLU) ---")
        nlu_result = parse_query(user_input) # parse_query now returns a dict with an 'error' key on failure.
        
        if "error" in nlu_result and nlu_result["error"] is not None:
            print(f"Jules (NLU Error): I had trouble understanding your request: {nlu_result['error']}")
            if nlu_result.get("raw_openai_response"): # For debugging NLU issues
                print(f"       (Raw NLU provider response for debugging: {nlu_result['raw_openai_response']})")
            print("       Could you please try rephrasing your query?")
            continue # Ask for new input
        
        # Debug: Print NLU output
        # print("NLU Output (for debugging):")
        # print(json.dumps(nlu_result, indent=2))

        # Check for essential parameters from NLU
        metrics = nlu_result.get("metrics", [])
        dimensions = nlu_result.get("dimensions", [])
        date_ranges = nlu_result.get("date_ranges", [])

        if not metrics or not dimensions:
            # If metrics or dimensions are empty lists (as per nlu_processor's default error response)
            # or if they were explicitly set to empty by the LLM for a query that needs them.
            print("Jules: I understood your query as: \"", nlu_result.get("query_type", user_input), "\".")
            print("       However, I couldn't clearly identify the specific metrics or dimensions (like 'users', 'city', 'page views', 'landing page') needed to get the data.")
            print("       Could you please be more specific or rephrase your request to include these details?")
            continue

        if not date_ranges or not all(dr.get("start_date") and dr.get("end_date") for dr in date_ranges):
            # nlu_processor should always provide a default, but as a safeguard:
            print(f"Jules: I couldn't determine a clear date range for your query. I'll use the last 7 days by default.")
            start_date = "7daysAgo" # Default
            end_date = "today"      # Default
        else:
            # Assuming the first date range is the one to use for this basic client
            start_date = date_ranges[0]["start_date"]
            end_date = date_ranges[0]["end_date"]

        # 2. GA4 Data Retrieval Step
        print(f"\n--- Step 2: Fetching data from Google Analytics (Dim: {dimensions}, Met: {metrics}, Range: {start_date} to {end_date}) ---")
        
        ga4_response_data, ga4_error_message = get_basic_report( # ga4_client now returns (data, error_msg)
            property_id=property_id,
            dimensions=dimensions,
            metrics=metrics,
            start_date=start_date,
            end_date=end_date
        )

        ga4_input_for_formatter = None
        if ga4_error_message:
            print(f"Jules (GA4 Client Error): Sorry, I couldn't retrieve the data from Google Analytics.")
            print(f"       Reason: {ga4_error_message}")
            # Pass the error message itself to the formatter, so the LLM can explain it if needed
            ga4_input_for_formatter = ga4_error_message 
            # No 'continue' here; let the response generator try to explain the GA4 error.
        elif ga4_response_data is None and not ga4_error_message:
             # This case should be rare if ga4_client always returns an error string on failure
            print(f"Jules (GA4 Client Error): Failed to retrieve report for an unknown reason from ga4_client.")
            ga4_input_for_formatter = "An unknown error occurred while fetching data from Google Analytics."
        else:
            # Successful data retrieval (or data might be empty but no API error)
            # print("GA4 Response (Snippet for debugging):") # Uncomment for debugging
            # if hasattr(ga4_response_data, 'rows') and ga4_response_data.rows:
            #     print(f"  Received {len(ga4_response_data.rows)} rows of data.")
            # elif hasattr(ga4_response_data, 'rows'):
            #      print("  GA4 query returned successfully but with no data rows.")
            ga4_input_for_formatter = ga4_response_data # This is the actual RunReportResponse object

        # Format GA4 response (or error) for the LLM prompt
        # nlu_result is passed to help format_ga4_response_for_prompt use correct headers
        ga4_data_summary_for_llm = format_ga4_response_for_prompt(ga4_input_for_formatter, nlu_result)
        # print("\nFormatted GA4 data/error for LLM prompt (for debugging):")
        # print(ga4_data_summary_for_llm)

        # 3. Response Generation Step
        print("\n--- Step 3: Generating your answer ---")
        # generate_response now also handles OpenAI client errors internally
        ai_response = generate_response(
            nlu_data=nlu_result, # Pass the full NLU result for context
            ga4_data_summary=ga4_data_summary_for_llm # This can be data or an error string
        )

        # generate_response returns a user-facing error message string if it fails
        # Check if the response indicates an internal error from the generator itself
        if "I'm sorry, I encountered an issue" in ai_response or \
           "OpenAI client not initialized" in ai_response:
            print(f"Jules (Response Error): {ai_response}")
        else:
            print("\nJules says:")
            print(ai_response)

if __name__ == "__main__":
    is_config_ok, current_property_id = check_env_and_config()
    if is_config_ok:
        main_conversation_loop(current_property_id)
    else:
        print("\nApplication cannot start due to configuration errors.")
        print("Please review the messages above and ensure your environment is set up correctly.")
