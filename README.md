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

## Running the Application

Once all the prerequisites and environment variables (`GOOGLE_APPLICATION_CREDENTIALS`, `OPENAI_API_KEY`, and `GA4_PROPERTY_ID`) are set:

1.  Navigate to the root directory of the project in your terminal.
2.  Run the application using Python:

    ```bash
    python src/app.py
    ```

3.  The application will start, and you can begin asking questions about your GA4 data in the terminal. Type "exit" or "quit" to close the application.

## Security and Privacy Best Practices

It is crucial to handle API keys, sensitive data, and user privacy responsibly when using this application.

### 1. API Key Security

*   **Use Environment Variables:** Always use environment variables to manage your `OPENAI_API_KEY`, `GA4_PROPERTY_ID`, and the file path for `GOOGLE_APPLICATION_CREDENTIALS`. This application is designed to read these from your environment.
*   **Never Hardcode Keys:** **Do NOT hardcode your API keys or property ID directly into the source code.** Hardcoding sensitive credentials is a significant security risk.
*   **Do Not Commit Keys to Version Control:**
    *   Ensure that your actual API key values and your Google service account JSON key file (e.g., `your-service-account-credentials.json`) are **NEVER** committed to Git or any other version control system.
    *   The `.gitignore` file in this project is configured to ignore common patterns for these sensitive files (e.g., `*.json`, `*.env`, `credentials.json`). However, you are still responsible for ensuring these files remain local and secure. Double-check that your specific key file names are covered or add them to your local or global `.gitignore` if they are not.
    *   If you accidentally commit a key, you should revoke it immediately and rotate to a new key.

### 2. Data Handling

*   **In-Memory Processing:** This application processes your Google Analytics 4 data and your natural language queries primarily in memory. By default, it does not store this information persistently (e.g., in databases or local files).
*   **Third-Party Services:**
    *   When you ask a query, parts of your query and potentially the summarized GA4 data are sent to the **OpenAI API** to generate natural language responses or parse your query.
    *   Your interactions with **Google Analytics Data API** are governed by Google's terms.
    *   You should review the privacy policies and terms of service for both OpenAI and Google Cloud / Google Analytics to understand how they handle data sent to their services.
    *   **OpenAI Data Usage:** By default, data sent to the OpenAI API may be used to train future models unless you have a specific agreement with OpenAI (e.g., through an enterprise plan or by opting out via their defined processes, if available). For sensitive data, explore options like Azure OpenAI Service which may offer different data privacy commitments, or check current OpenAI policies for business users. The client library itself does not typically offer a `store=false` parameter for individual API calls to control OpenAI's data retention for training; this is usually managed at the account level or through specific API versions/endpoints if offered by OpenAI.

### 3. Compliance

*   **Adhere to Regulations:** You are responsible for ensuring that your use of this tool, your Google Analytics 4 data, and your interactions with the OpenAI API comply with all relevant data protection regulations in your jurisdiction (e.g., GDPR, CCPA, HIPAA if applicable).
*   **User Consent:** If you are using this tool in a context where you are processing data on behalf of others or for users of your services, ensure you have appropriate consents and provide necessary disclosures.

By using this application, you acknowledge your responsibility for securing your API keys and adhering to privacy and compliance requirements.

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