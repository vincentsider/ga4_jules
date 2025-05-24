# ga4_jules

This project aims to integrate with Google Analytics 4 (GA4) to retrieve and process data.

## Prerequisites and Setup

Before running this application, you need to set up your Google Cloud Project and Google Analytics 4 property.

### 1. Google Cloud Project Setup

1.  **Create or Select a Google Cloud Project:**
    *   Go to the [Google Cloud Console](https://console.cloud.google.com/).
    *   Create a new project or select an existing one.

2.  **Enable the Google Analytics Data API:**
    *   In your Google Cloud Project, navigate to "APIs & Services" > "Library".
    *   Search for "Google Analytics Data API".
    *   Enable the API for your project.

3.  **Create a Service Account:**
    *   Navigate to "IAM & Admin" > "Service Accounts".
    *   Click "Create Service Account".
    *   Fill in the service account details (name, ID, description).
    *   Grant any necessary roles (e.g., "Project Viewer" is often sufficient for basic API access, but you might not need to grant any roles at this stage if the service account is only used for this specific API). Click "Done".

4.  **Download Service Account JSON Key:**
    *   After creating the service account, find it in the list.
    *   Click on the service account email.
    *   Go to the "Keys" tab.
    *   Click "Add Key" > "Create new key".
    *   Select "JSON" as the key type and click "Create".
    *   A JSON file will be downloaded. **Store this file securely**, as it contains credentials to access your Google Cloud resources.

### 2. Google Analytics 4 Property Setup

1.  **Grant Service Account Permissions in GA4:**
    *   Open your Google Analytics 4 Property.
    *   Go to "Admin" (usually a gear icon in the bottom left).
    *   In the "Property" column, click on "Property Access Management".
    *   Click the "+" icon to add a new user.
    *   Enter the email address of the service account you created in the Google Cloud Project (e.g., `your-service-account-name@your-project-id.iam.gserviceaccount.com`).
    *   Assign the "Viewer" role. You might need more permissive roles (e.g., "Analyst") depending on the data you need to access, but "Viewer" is a good starting point for reading reports.
    *   Click "Add".

### 3. Environment Setup

1.  **Set `GOOGLE_APPLICATION_CREDENTIALS` Environment Variable:**
    *   You need to tell the Google client libraries where to find your downloaded service account JSON key file.
    *   Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable in your development environment to the absolute path of the JSON key file.
    *   **Example (Linux/macOS):**
        ```bash
        export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/downloaded-key-file.json"
        ```
    *   **Example (Windows - Command Prompt):**
        ```cmd
        set GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\your\downloaded-key-file.json"
        ```
    *   **Example (Windows - PowerShell):**
        ```powershell
        $env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\your\downloaded-key-file.json"
        ```
    *   You might want to add this line to your shell's profile file (e.g., `.bashrc`, `.zshrc`) for a persistent setting. For production environments, manage this variable securely (e.g., using secrets management tools).

Once these steps are completed, the application should be able to authenticate with the Google Analytics Data API.

### 4. OpenAI API Key Setup (for Natural Language Processing)

This project uses the OpenAI API to understand natural language queries and translate them into parameters for the Google Analytics Data API.

1.  **Obtain an OpenAI API Key:**
    *   Go to the [OpenAI Platform](https://platform.openai.com/).
    *   Sign up or log in to your account.
    *   Navigate to the "API keys" section (usually under your account settings or organization settings).
    *   Create a new secret key. Copy this key immediately and store it securely. You will not be able to see it again.

2.  **Set `OPENAI_API_KEY` Environment Variable:**
    *   You need to make your OpenAI API key available to the application.
    *   Set the `OPENAI_API_KEY` environment variable in your development environment to the key you just obtained.
    *   **Example (Linux/macOS):**
        ```bash
        export OPENAI_API_KEY="your-openai-api-key"
        ```
    *   **Example (Windows - Command Prompt):**
        ```cmd
        set OPENAI_API_KEY="your-openai-api-key"
        ```
    *   **Example (Windows - PowerShell):**
        ```powershell
        $env:OPENAI_API_KEY="your-openai-api-key"
        ```
    *   Add this line to your shell's profile file (e.g., `.bashrc`, `.zshrc`) for a persistent setting. For production environments, manage this variable securely.

### 5. Set GA4 Property ID

The application needs to know which Google Analytics 4 Property to query.

*   **Set `GA4_PROPERTY_ID` Environment Variable (Recommended):**
    This is the preferred method. Set the `GA4_PROPERTY_ID` environment variable to your actual GA4 Property ID (the numeric string, e.g., "123456789").
    *   **Example (Linux/macOS):**
        ```bash
        export GA4_PROPERTY_ID="your-ga4-property-id"
        ```
    *   **Example (Windows - Command Prompt):**
        ```cmd
        set GA4_PROPERTY_ID="your-ga4-property-id"
        ```
    *   **Example (Windows - PowerShell):**
        ```powershell
        $env:GA4_PROPERTY_ID="your-ga4-property-id"
        ```
*   **Alternatively, update `src/ga4_client.py`:**
    If you do not set the environment variable, the application will try to use the `GA4_PROPERTY_ID` placeholder value defined in `src/ga4_client.py`. You would need to manually edit this file, which is less ideal for configuration.

## Running the Application (Command-Line Interface)

The command-line version of the application can be run as described below. For the web interface, see "Web Application Setup" and "Running the Web Application".

Once all the prerequisites and environment variables (`GOOGLE_APPLICATION_CREDENTIALS`, `OPENAI_API_KEY`, and `GA4_PROPERTY_ID`) are set:

1.  Navigate to the root directory of the project in your terminal.
2.  Ensure all dependencies are installed (see `requirements.txt`):
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the command-line application using Python:

    ```bash
    python src/app.py
    ```

4.  The application will start, and you can begin asking questions about your GA4 data in the terminal. Type "exit" or "quit" to close the application.

## Web Application Setup

This project also includes a Flask-based web interface. To set it up, you'll need to configure Google OAuth 2.0 credentials.

**1. Install Web Dependencies:**
   If you haven't already, install all dependencies, including Flask:
   ```bash
   pip install -r requirements.txt
   ```

**2. Configure Google OAuth 2.0 Credentials:**

*   **Go to Google Cloud Console:** Navigate to [APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials).
*   **Create OAuth 2.0 Client ID:**
    *   Click on "+ CREATE CREDENTIALS" and select "OAuth client ID".
    *   For "Application type", choose "Web application".
    *   Give it a name (e.g., "Jules GA4 Web App").
    *   **Authorized JavaScript origins (Optional but good for security):** You can add `http://localhost:5000`.
    *   **Authorized redirect URIs:** This is crucial. Click "+ ADD URI" and add:
        *   `http://localhost:5000/auth/callback` (This exact URI is used by the application).
        *   If deploying to a different domain or port, you'll need to add those corresponding redirect URIs here as well.
    *   Click "CREATE".
*   **Note Your Client ID and Client Secret:** After creation, a dialog will show your "Client ID" and "Client Secret". Copy these values. You will need them for environment variables.
*   **Scopes Used:** The application requests the following OAuth scopes during authentication:
    *   `https://www.googleapis.com/auth/analytics.readonly` (to read GA4 data on behalf of the user)
    *   `openid` (standard OpenID Connect scope)
    *   `https://www.googleapis.com/auth/userinfo.email` (to get the user's email address)
    *   `https://www.googleapis.com/auth/userinfo.profile` (to get the user's name and profile picture)

**3. Set Environment Variables for Web App:**

   The web application uses user-specific authentication via Google OAuth. The service account (`GOOGLE_APPLICATION_CREDENTIALS`) is primarily for the command-line version of the app or could be a fallback if user OAuth is not desired for some operations (though the current web app is geared towards user OAuth for GA4 data access).

   You need to set the following environment variables for the web application:

   *   `GOOGLE_OAUTH_CLIENT_ID`: Your OAuth 2.0 Client ID obtained above.
        ```bash
        # Example (Linux/macOS)
        export GOOGLE_OAUTH_CLIENT_ID="your-google-oauth-client-id.apps.googleusercontent.com"
        # Example (Windows - Command Prompt)
        set GOOGLE_OAUTH_CLIENT_ID="your-google-oauth-client-id.apps.googleusercontent.com"
        ```
   *   `GOOGLE_OAUTH_CLIENT_SECRET`: Your OAuth 2.0 Client Secret obtained above.
        ```bash
        # Example (Linux/macOS)
        export GOOGLE_OAUTH_CLIENT_SECRET="YOUR_CLIENT_SECRET_HERE"
        # Example (Windows - Command Prompt)
        set GOOGLE_OAUTH_CLIENT_SECRET="YOUR_CLIENT_SECRET_HERE"
        ```
   *   `FLASK_SECRET_KEY`: A strong, random string used by Flask to sign session cookies. This is crucial for security. You can generate one using Python:
        ```python
        import os
        os.urandom(24).hex()
        ```
        Then set it as an environment variable:
        ```bash
        # Example (Linux/macOS)
        export FLASK_SECRET_KEY="your_generated_secret_key"
        # Example (Windows - Command Prompt)
        set FLASK_SECRET_KEY="your_generated_secret_key"
        ```
   *   **(Optional but Recommended) `.env` file:** For easier local development, you can create a `.env` file in the project root directory and store your environment variables there. The `src/web_app.py` is set up to load this file using `python-dotenv`.
        Example `.env` file content:
        ```
        OPENAI_API_KEY="your-openai-api-key"
        GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
        GA4_PROPERTY_ID="your-ga4-property-id"
        GOOGLE_OAUTH_CLIENT_ID="your-google-oauth-client-id.apps.googleusercontent.com"
        GOOGLE_OAUTH_CLIENT_SECRET="YOUR_CLIENT_SECRET_HERE"
        FLASK_SECRET_KEY="your_generated_secret_key"
        # Optional: If you want to override the default redirect URI
        # GOOGLE_REDIRECT_URI="http://localhost:5000/auth/callback" 
        ```
        **Ensure `.env` is listed in your `.gitignore` file and never committed to version control.**

**4. OAuth Flow Overview:**
   * User clicks "Sign in with Google".
   * They are redirected to Google's OAuth consent screen where they approve the requested scopes.
   * Google redirects back to the application's `/auth/callback` URI with an authorization code.
   * The application exchanges this code for an access token and a refresh token.
   * User's credentials (including the refresh token for offline access) and profile information are stored in the Flask session (server-side cookie).
   * The `ga4_client.py` module's `get_report_with_user_creds` function uses these stored credentials to make API calls. It can also refresh the access token if it expires, using the refresh token.

## Running the Web Application

Once the prerequisites, general environment variables, and web-specific environment variables are set:

1.  Navigate to the root directory of the project.
2.  Run the Flask web application:
    ```bash
    python src/web_app.py
    ```
3.  Open your web browser and go to `http://localhost:5000`. You should see the login page.

## Security and Privacy Best Practices

It is crucial to handle API keys, user credentials, sensitive data, and user privacy responsibly when using this application, especially with the introduction of the web interface and Google OAuth 2.0.

### 1. Credentials and Configuration Security

*   **Environment Variables are Key:**
    *   **OpenAI API Key (`OPENAI_API_KEY`):** Used for NLU and response generation. Keep this confidential.
    *   **Google Service Account (for CLI - `GOOGLE_APPLICATION_CREDENTIALS`, `GA4_PROPERTY_ID`):** The JSON key file for the service account (if using the CLI version primarily) must be kept secure. The `GA4_PROPERTY_ID` specifies which property this service account accesses.
    *   **Google OAuth 2.0 Client Credentials (for Web App - `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`):** These are used by the Flask web application to authenticate users with their Google accounts. They must be kept confidential. **Never commit them directly to version control.**
    *   **Flask Secret Key (`FLASK_SECRET_KEY`):** This is critical for securing Flask sessions, which store user authentication information. Use a long, random, and unique string.
*   **Never Hardcode Credentials:** Do NOT hardcode any of these sensitive values directly into the source code.
*   **`.gitignore`:** The project's `.gitignore` file is configured to ignore common sensitive file names (like `*.json`, `*.env`). Always double-check that your specific credential files (especially service account JSON files and `.env` files) are not committed to version control. If you accidentally commit sensitive credentials, revoke them immediately and generate new ones.
*   **Redirect URIs (for Web App):**
    *   In the Google Cloud Console, the "Authorized redirect URIs" for your OAuth 2.0 Client ID must be configured precisely. For local development, this is typically `http://localhost:5000/auth/callback`.
    *   **For production, always use HTTPS for your redirect URIs.** This is essential for security.
*   **OAuth Scopes (for Web App):** The application requests the following scopes during user authentication:
    *   `https://www.googleapis.com/auth/analytics.readonly`: To read Google Analytics 4 data on behalf of the authenticated user.
    *   `openid`: Standard OpenID Connect scope, used for authentication.
    *   `https://www.googleapis.com/auth/userinfo.email`: To retrieve the user's email address for identification and display.
    *   `https://www.googleapis.com/auth/userinfo.profile`: To retrieve the user's name and profile picture for a personalized experience.
    Users will be asked to consent to these scopes when they first log in.

### 2. Session Management (for Web App)

*   **Flask Sessions:** The web application uses Flask's session mechanism to store user authentication state and Google OAuth tokens (access and refresh tokens). These sessions are typically cookie-based by default.
*   **`FLASK_SECRET_KEY`:** A strong, randomly generated `FLASK_SECRET_KEY` is essential for securing these sessions. If this key is compromised, attackers could potentially tamper with session data.
*   **Production Considerations:** While Flask's default cookie-based sessions are convenient for development, for production environments handling sensitive tokens (like refresh tokens which can be long-lived), consider using server-side sessions (e.g., with Flask-Session and a backend like Redis or a database). This can mitigate risks if the `FLASK_SECRET_KEY` is ever compromised, as the tokens themselves are not directly stored in the client-side cookie.

### 3. User Token Handling (for Web App)

*   **Storage:** User access tokens and refresh tokens obtained via Google OAuth 2.0 are stored in the Flask session.
*   **Purpose:**
    *   **Access Tokens:** Short-lived tokens used by the server-side application (`web_app.py`) to make authorized API calls to the Google Analytics Data API on behalf of the logged-in user.
    *   **Refresh Tokens:** Longer-lived tokens used to obtain new access tokens when the current access token expires, allowing the user to stay logged in without re-authenticating frequently. The `ga4_client.py` module handles this refresh logic.
*   **Security:** These tokens are sensitive. The security of the Flask session (and thus the `FLASK_SECRET_KEY`) is paramount to protect them.

### 4. CSRF (Cross-Site Request Forgery) Protection

*   **OAuth Flow:** The Google OAuth 2.0 flow implemented uses a `state` parameter for validation during the authentication redirect process. This is a standard mechanism to protect against CSRF attacks during login.
*   **AJAX Endpoints (`/chat`):**
    *   Standard browser Same-Origin Policies provide a baseline level of protection for AJAX requests like the one made by the chat interface.
    *   For enhanced security in a production environment, especially if the application were to handle more sensitive operations via POST requests, implementing specific anti-CSRF token mechanisms (e.g., using Flask-WTF or custom tokens) for AJAX requests would be a good practice. For the current scope (reading GA4 data based on user queries), the existing setup provides a reasonable level of protection.

### 5. Data Handling (Reiteration and Web Context)

*   **In-Memory Processing:** The application (both CLI and web versions) processes Google Analytics 4 data and user queries primarily in memory for the duration of a request.
*   **User-Specific Data (Web App):** In the web application, GA4 data is fetched by the server using the authenticated user's own OAuth tokens. This means the application only accesses GA4 properties that the logged-in user has permission to view.
*   **Third-Party Services (OpenAI):**
    *   User queries (and potentially summarized GA4 data included in prompts) are sent to the **OpenAI API** for natural language understanding and response generation.
    *   Review OpenAI's data usage and privacy policies to understand how they handle data sent to their services. Consider any implications for data residency and model training opt-outs if relevant.
*   **Google Analytics Data API:** Interactions with this API are governed by Google's terms and privacy policies.

### 6. General Security Advice

*   **HTTPS in Production:** Always run the web application over HTTPS in a production environment to protect all traffic, including OAuth tokens and user data, in transit.
*   **Keep Dependencies Updated:** Regularly update all project dependencies (Flask, Google client libraries, OpenAI library, etc.) to their latest stable versions to incorporate security patches and improvements. Use tools like `pip list --outdated` and consider automated dependency scanning.
*   **Principle of Least Privilege:** Ensure that the OAuth scopes requested are strictly necessary for the application's functionality. The current scopes (`analytics.readonly`, `openid`, `email`, `profile`) are appropriate for the described features.

By using this application, you acknowledge your responsibility for securing your credentials, managing user data appropriately, and adhering to all relevant privacy and compliance requirements.

## Running Tests

This project uses Python's built-in `unittest` framework for testing. Tests are located in the `tests/` directory.

To run the test suite:

1.  **Navigate to the root directory** of the project in your terminal.
2.  **Ensure all dependencies are installed**, including those for the application itself and any specific testing libraries (though this project primarily uses `unittest` and `unittest.mock`, which are standard).
3.  **Set necessary environment variables** if any tests rely on them (though most unit tests should mock these out). For example, some tests might check the behavior when `OPENAI_API_KEY` is present or absent. For tests that mock external services (like the ones in this suite), the actual keys are not strictly needed to run the tests themselves as the services are mocked.
4.  **Execute the tests** using one of the following commands:

    *   To discover and run all tests verbosely:
        ```bash
        python -m unittest discover -s tests -v
        ```
    *   To run a specific test file:
        ```bash
        python -m unittest tests.test_nlu_processor -v
        ```
    *   To run a specific test class within a file:
        ```bash
        python -m unittest tests.test_nlu_processor.TestNLUProcessor -v
        ```
    *   To run a specific test method within a class:
        ```bash
        python -m unittest tests.test_nlu_processor.TestNLUProcessor.test_parse_query_success_simple -v
        ```

All tests should pass if the application is functioning correctly and the test environment is set up as expected. The tests are designed to mock external API calls, so they can be run without live internet access or actual API credentials once dependencies are installed.