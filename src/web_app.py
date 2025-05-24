from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort, flash
import os
import json # For credentials to_json/from_json
from dotenv import load_dotenv
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import google.auth.transport.requests # For token refresh
import requests # For userinfo endpoint

# Import application modules
from ga4_client import get_report_with_user_creds, GA4_PROPERTY_ID_SERVICE_ACCOUNT # Use service account ID as a fallback if user doesn't specify one
from nlu_processor import parse_query
from response_generator import generate_response, format_ga4_response_for_prompt


# Load environment variables from .env file if it exists
load_dotenv()

app = Flask(__name__)

# --- Configuration ---
app.secret_key = os.getenv("FLASK_SECRET_KEY")
if not app.secret_key:
    print("ERROR: FLASK_SECRET_KEY environment variable not set. Application will not run securely.")
    # For development, you might provide a default, but it's bad practice for production.
    # For this project, we will rely on it being set.
    # exit(1) # Or raise an error

GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")

if not GOOGLE_OAUTH_CLIENT_ID or not GOOGLE_OAUTH_CLIENT_SECRET:
    print("ERROR: GOOGLE_OAUTH_CLIENT_ID or GOOGLE_OAUTH_CLIENT_SECRET environment variables not set.")
    print("       OAuth functionality will be disabled.")
    # Potentially disable login routes or show an error on the login page.

# OAuth 2.0 Scopes
# Ensure these are the same as configured in your Google Cloud Console for the OAuth client ID
SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly", # GA4 data
    "openid", # Standard OpenID scope
    "https://www.googleapis.com/auth/userinfo.email", # Get user's email
    "https://www.googleapis.com/auth/userinfo.profile"  # Get user's name and profile picture
]
# This must match the "Authorized redirect URIs" in your Google Cloud Console
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5000/auth/callback")

# Path to client_secret.json (alternative to setting client_id/secret via env vars directly for Flow)
# For this setup, we'll prefer direct env vars for client_id/secret, but if you had a
# client_secret.json file, you could use:
# flow = Flow.from_client_secrets_file('path/to/your/client_secret.json', scopes=SCOPES, redirect_uri=REDIRECT_URI)
# However, google_auth_oauthlib.flow.Flow can also take client_id and client_secret directly if 
# the client_config dictionary is constructed properly.
# Simpler: construct client_config for Flow directly
CLIENT_CONFIG = {
    "web": {
        "client_id": GOOGLE_OAUTH_CLIENT_ID,
        "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        # "redirect_uris" : [REDIRECT_URI] # Not strictly needed here if redirect_uri is passed to Flow
    }
}


@app.route('/')
def index():
    if 'credentials_json' in session:
        return redirect(url_for('chat_interface'))
    return render_template('login.html') # Or a more dedicated home page

@app.route('/login', methods=['GET'])
def login_page():
    if 'credentials_json' in session: # If already logged in
        return redirect(url_for('chat_interface'))
    return render_template('login.html')

@app.route('/auth/google')
def auth_google():
    if not GOOGLE_OAUTH_CLIENT_ID or not GOOGLE_OAUTH_CLIENT_SECRET:
        return "OAuth is not configured on the server. Please contact the administrator.", 500

    try:
        flow = Flow.from_client_config(
            client_config=CLIENT_CONFIG, # Use the constructed dict
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
    except ValueError as e: # More specific error for bad client_config
        print(f"Error creating OAuth Flow due to client_config: {e}")
        # This usually means GOOGLE_OAUTH_CLIENT_ID or GOOGLE_OAUTH_CLIENT_SECRET are missing/malformed
        flash("Authentication setup error on the server. Please contact an administrator.", "error")
        return redirect(url_for('login_page'))
    except Exception as e:
        print(f"Error creating OAuth Flow: {e}")
        flash("Could not initiate authentication. Please try again later.", "error")
        return redirect(url_for('login_page'))

    # Generate the authorization URL
    authorization_url, state = flow.authorization_url(
        access_type='offline',  # Request a refresh token
        include_granted_scopes='true' # Useful if user has already granted some scopes
    )
    
    # Store the state in the session for later validation
    session['state'] = state
    
    return redirect(authorization_url)

@app.route('/auth/callback')
def auth_callback():
    # Verify the state to protect against CSRF attacks
    state = session.pop('state', None)
    if state is None or state != request.args.get('state'):
        print("CSRF Warning: State mismatch or missing state.")
        abort(403) # Forbidden

    if not GOOGLE_OAUTH_CLIENT_ID or not GOOGLE_OAUTH_CLIENT_SECRET:
        return "OAuth is not configured on the server. Cannot process callback.", 500

    try:
        flow = Flow.from_client_config(
            client_config=CLIENT_CONFIG,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        
        # Exchange the authorization code for an access token and refresh token
        flow.fetch_token(authorization_response=request.url)
        
        # Store the credentials in the session.
        # to_json() converts the Credentials object to a JSON string.
        session['credentials_json'] = flow.credentials.to_json()

        # Get user info
        credentials = flow.credentials
        # Use token to get user info from userinfo endpoint
        userinfo_response = requests.get(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            headers={'Authorization': f'Bearer {credentials.token}'}
        )
        if userinfo_response.ok:
            user_info = userinfo_response.json()
            session['user_email'] = user_info.get('email')
            session['user_name'] = user_info.get('name')
            session['user_id'] = user_info.get('sub') # 'sub' is the standard subject identifier
        else:
            session['user_name'] = "User" # Fallback
            print(f"Failed to fetch user info: {userinfo_response.text}")
            
        return redirect(url_for('chat_interface'))

    except Exception as e:
        print(f"Error during OAuth callback: {e}")
        flash(f"Authentication failed: {str(e)}. Please try again.", "error")
        return redirect(url_for('login_page'))


@app.route('/chat-interface')
def chat_interface():
    if 'credentials_json' not in session: # Check for credentials instead of just user_id
        return redirect(url_for('login_page'))
    user_name = session.get('user_name', 'User')
    return render_template('chat.html', user_name=user_name)


@app.route('/chat', methods=['POST'])
def chat_handler():
    if 'credentials_json' not in session:
        return jsonify({"error": "Unauthorized. Please log in."}), 401
    
    data = request.json
    user_query = data.get('query')
    ga4_property_id_for_query = data.get('ga4_property_id') # Optional: user might specify which property if they have access to many

    if not user_query:
        return jsonify({"error": "No query provided."}), 400

    # --- NLU Step ---
    print(f"Web App: Processing query: '{user_query}'")
    nlu_result = parse_query(user_query)
    try:
        # --- NLU Step ---
        print(f"Web App: Processing query: '{user_query}'")
        nlu_result = parse_query(user_query)
        if "error" in nlu_result and nlu_result["error"] is not None:
            error_msg = f"I had trouble understanding your request: {nlu_result['error']}. Could you try rephrasing?"
            print(f"Web App: NLU Error: {nlu_result['error']}")
            return jsonify({"error": error_msg, "debug_nlu": nlu_result}), 400

        metrics = nlu_result.get("metrics", [])
        dimensions = nlu_result.get("dimensions", [])
        date_ranges = nlu_result.get("date_ranges", [])

        if not metrics or not dimensions:
            error_msg = "I understood your query, but couldn't identify the specific metrics or dimensions needed. Please be more specific."
            return jsonify({"error": error_msg, "debug_nlu": nlu_result}), 400

        start_date = date_ranges[0].get("start_date", "7daysAgo")
        end_date = date_ranges[0].get("end_date", "today")
        
        query_ga4_id = ga4_property_id_for_query or os.getenv("GA4_PROPERTY_ID") or GA4_PROPERTY_ID_SERVICE_ACCOUNT
        if query_ga4_id == "YOUR_GA4_PROPERTY_ID" or not query_ga4_id:
            error_msg = "The GA4 Property ID is not configured on the server. Please contact the administrator."
            print("Web App: GA4 Property ID is not configured for querying.")
            return jsonify({"error": error_msg}), 500

        # --- GA4 Data Retrieval Step (with User Credentials) ---
        print(f"Web App: Requesting GA4 report (User: {session.get('user_email')}, Prop: {query_ga4_id})")
        user_creds_dict = json.loads(session['credentials_json'])

        def update_session_credentials(new_credentials_json_str):
            session['credentials_json'] = new_credentials_json_str
            print("Web App: User credentials in session were updated due to token refresh.")

        ga4_response_data, ga4_error_message = get_report_with_user_creds(
            user_credentials_dict=user_creds_dict,
            property_id=query_ga4_id, dimensions=dimensions, metrics=metrics,
            start_date=start_date, end_date=end_date,
            session_update_callback=update_session_credentials
        )

        if ga4_error_message:
            print(f"Web App: GA4 Client Error: {ga4_error_message}")
            if "(re-login required)" in ga4_error_message:
                return jsonify({"error": f"GA4 Authentication Error: {ga4_error_message}", "re_auth_required": True}), 401
            # For other GA4 errors, let the response generator try to explain it.
            # The format_ga4_response_for_prompt function is designed to handle error strings.
        
        ga4_input_for_formatter = ga4_error_message if ga4_error_message else ga4_response_data

        # --- Response Generation Step ---
        ga4_data_summary_for_llm = format_ga4_response_for_prompt(ga4_input_for_formatter, nlu_result)
        
        ai_final_response = generate_response(
            nlu_data=nlu_result,
            ga4_data_summary=ga4_data_summary_for_llm
        )
        
        # Check if generate_response itself indicated an error
        if "I'm sorry, I encountered an issue" in ai_final_response or \
           "OpenAI client not initialized" in ai_final_response:
            print(f"Web App: Response Generation Error: {ai_final_response}")
            return jsonify({"error": ai_final_response}), 500 # Internal server error from response gen

        return jsonify({
            "user_query": user_query,
            "ai_response": ai_final_response,
            "debug_nlu": nlu_result,
            "debug_ga4_summary": ga4_data_summary_for_llm[:500] if isinstance(ga4_data_summary_for_llm, str) else "Summary not string"
        })

    except Exception as e:
        print(f"Web App: Unhandled error in /chat endpoint: {e}")
        # Log the full exception for server-side debugging
        import traceback
        traceback.print_exc()
        return jsonify({"error": "An unexpected error occurred on the server. Please try again later."}), 500

@app.route('/logout')
def logout():
    session.pop('credentials_json', None)
    session.pop('user_email', None)
    session.pop('user_name', None)
    session.pop('user_id', None) # if you were setting it
    session.pop('state', None) # Clear any OAuth state
    # session.clear() # Use with caution, clears everything including flash messages etc.
    return redirect(url_for('index'))


# For production, consider using a more robust session management solution
# (e.g., server-side sessions with Flask-Session) if storing sensitive data like
# refresh tokens directly in the client-side cookie (Flask's default) is a concern.
# For this project's scope, default cookie-based session is acceptable for simplicity,
# but be aware of the security implications with long-lived refresh tokens.

if __name__ == '__main__':
    if not app.secret_key or app.secret_key == "your_default_secret_key_for_development_only":
        print("WARNING: FLASK_SECRET_KEY is not set or is set to a default insecure value.")
        print("         For production, please set a strong, random FLASK_SECRET_KEY environment variable.")
    if not GOOGLE_OAUTH_CLIENT_ID or not GOOGLE_OAUTH_CLIENT_SECRET:
         print("WARNING: OAuth Client ID or Secret is not configured. Login will not work.")
    
    # The host '0.0.0.0' makes the server accessible externally.
    # Ensure your redirect URI in Google Cloud Console matches (e.g., http://localhost:5000/auth/callback
    # or http://your-domain.com/auth/callback if deployed).
    app.run(host='0.0.0.0', port=5000, debug=True)
