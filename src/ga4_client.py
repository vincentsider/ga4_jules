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
)

# TODO: Replace with your actual GA4 Property ID
GA4_PROPERTY_ID = "YOUR_GA4_PROPERTY_ID"


def get_basic_report(
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
        error_message = f"An unexpected error occurred in ga4_client: {e}"
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
    # Replace GA4_PROPERTY_ID with your actual property ID or set it via other means.

    if GA4_PROPERTY_ID == "YOUR_GA4_PROPERTY_ID":
        print(
            "Please update the GA4_PROPERTY_ID variable in this script with your actual GA4 Property ID."
        )
    else:
        print(f"Fetching report for GA4 Property ID: {GA4_PROPERTY_ID}")
        # Example: Active users by city in the last 7 days
        report_dimensions = ["city"]
        report_metrics = ["activeUsers"]
        report_start_date = "7daysAgo"
        report_end_date = "today"

        report_response, error = get_basic_report(
            GA4_PROPERTY_ID,
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
