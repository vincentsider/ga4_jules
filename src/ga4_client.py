from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
    RunReportResponse,
)
from google.api_core.exceptions import (
    GoogleAPICallError,
    RetryError,
    InvalidArgument,
    PermissionDenied,
    ResourceExhausted,
    ServiceUnavailable,
    DeadlineExceeded,
    Unauthenticated, # For user auth issues
)
from google.oauth2.credentials import Credentials
import google.auth.transport.requests # For token refresh, if needed manually
import os # For os.getenv


# --- Service Account Based Client (Original) ---
# This GA4_PROPERTY_ID is for the service account flow (e.g., CLI app)
GA4_PROPERTY_ID_SERVICE_ACCOUNT = os.getenv("GA4_PROPERTY_ID", "YOUR_GA4_PROPERTY_ID") # Keep existing env var for this


def get_basic_report_service_account( # Renamed to clarify it's for service account
    property_id: str,
    dimensions: list[str],
    metrics: list[str],
    start_date: str,
    end_date: str,
) -> tuple[RunReportResponse | None, str | None]:
    """
    Runs a basic report on a Google Analytics 4 property.

    Args:
        property_id: The GA4 property ID.
        dimensions: A list of dimension names.
        metrics: A list of metric names.
        start_date: The start date for the report (YYYY-MM-DD).
        end_date: The end date for the report (YYYY-MM-DD).

    Returns:
        A tuple containing:
            - A RunReportResponse object with the report data, or None if an error occurs.
            - An error message string if an error occurs, or None if successful.
    """
    try:
        client = BetaAnalyticsDataClient()

        # Basic input validation (can be expanded)
        if not property_id or not dimensions or not metrics or not start_date or not end_date:
            return None, "Missing required parameters (property_id, dimensions, metrics, start_date, or end_date)."

        request = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name=dim) for dim in dimensions],
            metrics=[Metric(name=metric) for metric in metrics],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        )
        response = client.run_report(request)
        return response, None
    except InvalidArgument as e:
        error_message = f"GA4 API Invalid Argument: {e}. This often means the dimensions or metrics are invalid or incompatible. Please check your query."
        print(error_message)
        return None, error_message
    except PermissionDenied as e:
        error_message = f"GA4 API Permission Denied: {e}. Ensure the service account has 'Viewer' permissions on the GA4 property and the Google Analytics Data API is enabled in your GCP project."
        print(error_message)
        return None, error_message
    except ResourceExhausted as e:
        error_message = f"GA4 API Resource Exhausted: {e}. This usually means you've hit a quota limit. Please check your Google Cloud Platform quotas for the Analytics API."
        print(error_message)
        return None, error_message
    except (ServiceUnavailable, DeadlineExceeded) as e:
        error_message = f"GA4 API Service Unavailable or Timeout: {e}. Google's servers might be busy or there could be a network issue. Please try again later."
        print(error_message)
        return None, error_message
    except GoogleAPICallError as e:
        error_message = f"A Google API Call Error occurred: {e}"
        print(error_message)
        return None, error_message
    except RetryError as e: # Should ideally be handled by the client library's retry mechanism, but can be caught.
        error_message = f"A Retryable Error occurred: {e}. The request may have failed after multiple retries."
        print(error_message)
        return None, error_message
    except Exception as e:
        error_message = f"An unexpected error occurred in ga4_client (service account): {e}"
        print(error_message)
        return None, error_message

# --- User OAuth Based Client ---

def get_report_with_user_creds(
    user_credentials_dict: dict, # From session['credentials_json'] then json.loads()
    property_id: str, # User might have access to different properties
    dimensions: list[str],
    metrics: list[str],
    start_date: str,
    end_date: str,
    session_update_callback=None # Optional: To update session if token refreshes
) -> tuple[RunReportResponse | None, str | None]:
    """
    Runs a report using user's OAuth 2.0 credentials.
    Handles potential token refresh and updates session via callback if provided.
    """
    try:
        # Ensure all required keys are present for Credentials.from_authorized_user_info
        required_keys = {'token', 'refresh_token', 'client_id', 'client_secret', 'scopes'}
        if not all(key in user_credentials_dict for key in required_keys):
            # Scopes might be missing if not explicitly added during to_json if only token and refresh_token were stored.
            # However, Credentials.from_authorized_user_info expects them.
            # If using flow.credentials.to_json(), 'scopes' should be there.
            # Add 'token_uri' and 'auth_uri' if they are not part of the stored JSON but needed by from_authorized_user_info
            # or if client library doesn't pick them up from a default discovery document.
            # Generally, to_json() from google.oauth2.credentials.Credentials includes enough.
            # Let's assume user_credentials_dict is complete from to_json().
             pass


        credentials = Credentials.from_authorized_user_info(user_credentials_dict)

        # Check for token expiry and attempt refresh if necessary
        if credentials.expired and credentials.refresh_token:
            print("User credentials expired. Attempting refresh.")
            try:
                # Create a request object for the refresh mechanism
                request_obj = google.auth.transport.requests.Request()
                credentials.refresh(request_obj)
                print("User credentials refreshed successfully.")
                if session_update_callback and callable(session_update_callback):
                    session_update_callback(credentials.to_json()) # Update session with new token info
            except Exception as refresh_error:
                error_message = f"Failed to refresh user token: {refresh_error}. Please try logging in again."
                print(error_message)
                return None, f"{error_message} (re-login required)"


        client = BetaAnalyticsDataClient(credentials=credentials)

        if not property_id or not dimensions or not metrics or not start_date or not end_date:
            return None, "User report: Missing required parameters (property_id, dimensions, metrics, start_date, or end_date)."

        report_request = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name=dim) for dim in dimensions],
            metrics=[Metric(name=metric) for metric in metrics],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        )
        response = client.run_report(report_request)
        return response, None
        
    except Unauthenticated as e: 
        error_message = f"GA4 API User Unauthenticated: {e}. The user's credentials may be invalid or revoked. Please try logging in again."
        print(error_message)
        return None, f"{error_message} (re-login required)"
    except InvalidArgument as e:
        error_message = f"GA4 API Invalid Argument (user creds): {e}."
        print(error_message)
        return None, error_message
    except PermissionDenied as e:
        error_message = f"GA4 API Permission Denied (user creds): {e}. Ensure the authenticated user has access to this GA4 property."
        print(error_message)
        return None, error_message
    except ResourceExhausted as e:
        error_message = f"GA4 API Resource Exhausted (user creds): {e}."
        print(error_message)
        return None, error_message
    except (ServiceUnavailable, DeadlineExceeded) as e:
        error_message = f"GA4 API Service Unavailable or Timeout (user creds): {e}."
        print(error_message)
        return None, error_message
    except GoogleAPICallError as e:
        error_message = f"A Google API Call Error occurred (user creds): {e}"
        print(error_message)
        return None, error_message
    except Exception as e:
        error_message = f"An unexpected error occurred in ga4_client (user creds): {e}"
        print(error_message)
        return None, error_message


def print_run_report_response(response: RunReportResponse):
    """Prints results from a RunReportResponse to console."""
    print("Report result:")
    for row in response.rows:
        print(f"{row.dimension_values[0].value}, {row.metric_values[0].value}")


if __name__ == "__main__":
    # Example usage: Get active users by city for a given date range.
    # Ensure that GOOGLE_APPLICATION_CREDENTIALS environment variable is set.
    # Replace GA4_PROPERTY_ID_SERVICE_ACCOUNT with your actual property ID or set it via other means.

    if GA4_PROPERTY_ID_SERVICE_ACCOUNT == "YOUR_GA4_PROPERTY_ID":
        print(
            "Please update the GA4_PROPERTY_ID_SERVICE_ACCOUNT variable in this script or set GA4_PROPERTY_ID env var."
        )
    else:
        print(f"Fetching report for GA4 Property ID (Service Account): {GA4_PROPERTY_ID_SERVICE_ACCOUNT}")
        # Example: Active users by city in the last 7 days
        report_dimensions = ["city"]
        report_metrics = ["activeUsers"]
        report_start_date = "7daysAgo"
        report_end_date = "today"

        # Using the service account based function for this example
        report_response, error = get_basic_report_service_account( 
            GA4_PROPERTY_ID_SERVICE_ACCOUNT,
            report_dimensions,
            report_metrics,
            report_start_date,
            report_end_date,
        )

        if error:
            print(f"Error retrieving report: {error}")
        elif report_response:
            print_run_report_response(report_response)
        else:
            # This case should ideally not be reached if error is always set on failure
            print("Failed to retrieve report for an unknown reason.")
