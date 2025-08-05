# Family Tree Event Notifier

## Automating Hebrew Calendar Event Tracking and GitHub Issue Generation

This project provides an automated solution for tracking significant Hebrew calendar events (birthdays, yahrtzeits, and anniversaries) within your family tree. By processing a GEDCOM file, it identifies upcoming events, calculates genealogical distances from a central `PERSONID`, and generates informative GitHub issues. This helps you stay connected with your family's important dates, even for distant relatives.

## ✨ Features

*   **GEDCOM File Processing**: Automatically downloads and parses your GEDCOM file from Google Drive, extracting individual and family event data.
*   **Intelligent Hebrew Date Conversion**: Converts Gregorian dates from your GEDCOM file into their corresponding Hebrew dates, accurately identifying upcoming events.
*   **Dynamic Family Graph & Distance Calculation**: Constructs a comprehensive family graph using the `networkx` library. It then calculates the shortest genealogical distance between a specified `PERSONID` and every individual with an upcoming event.
*   **Visual Path Tracking (RTL Support)**: For events where the individual's distance from the `PERSONID` exceeds a configurable threshold, the genealogical path is clearly displayed in the GitHub issue. The path is presented with right-to-left (RTL) arrows (`←`) to align with Hebrew text flow.
*   **Contextual Emojis**: Enhances readability and quick identification of event types with relevant emojis:
    *   🎂 for birthdays of living individuals.
    *   🪦 for yahrtzeits (death anniversaries).
    *   💑 for marriage anniversaries.
*   **Automated GitHub Issue Generation**: Creates detailed GitHub issues for upcoming events, including:
    *   Event type and Hebrew date.
    *   Individual(s) involved.
    *   Genealogical distance from the `PERSONID`.
    *   The full genealogical path (if applicable).
*   **Flexible Workflow Configuration**: Allows you to easily set the central `PERSONID` and the `DISTANCE_THRESHOLD` directly through the GitHub Actions workflow dispatch interface, providing greater control over your notifications.

## 🚀 Setup

### Prerequisites

Before you begin, ensure you have the following:

*   **Python 3.8+**: The project is built with Python.
*   **Google Drive Account**: To host your GEDCOM file. The file must be shared with the service account email.
*   **GitHub Repository**: To host this project and for the automated issue creation.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/familytree.git
    cd familytree
    ```
    *(Remember to replace `your-username` with your actual GitHub username or the organization name.)*

2.  **Install Python dependencies:**
    It's highly recommended to use a virtual environment.
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```
    If `requirements.txt` is missing, create it with the following content:
    ```
    google-api-python-client
    google-auth-httplib2
    google-auth-oauthlib
    google-auth
    python-gedcom
    requests
    networkx
    hebcal
    ```

### Configuration

1.  **Google Drive API Credentials:**
    *   **Enable Google Drive API**: Go to the [Google Cloud Console](https://console.cloud.google.com/) and enable the Google Drive API for your project.
    *   **Create a Service Account**: Create a new service account. Generate a JSON key file for this service account.
    *   **GitHub Secret**: Add the entire content of this JSON key file as a GitHub Secret in your repository settings. Name the secret `GOOGLE_CREDENTIALS_JSON`.
    *   **Share GEDCOM File**: Share your GEDCOM file on Google Drive with the email address of the newly created service account.
    *   **Update `GOOGLE_DRIVE_FILE_ID`**: In `constants.py`, update the `GOOGLE_DRIVE_FILE_ID` variable with the ID of your GEDCOM file. Alternatively, you can set this as an environment variable in your GitHub Actions workflow.

2.  **GitHub Token:**
    *   The workflow automatically uses `GITHUB_TOKEN` provided by GitHub Actions for creating issues. No manual setup is required for this token.

## 💡 Usage

### Local Execution (for Development/Testing)

To run the script on your local machine:

```bash
export PERSONID="@I1@" # Replace with the GEDCOM ID of your central person
export DISTANCE_THRESHOLD=5 # Optional: Set a custom distance threshold (default is 8)
python main.py
```

Upon execution, the script will generate `fixed_tree.ged` (a cleaned version of your GEDCOM) and `dates.csv` (processed event data). Log messages will be printed to your console.

### GitHub Actions Workflow

This project is designed to run automatically via GitHub Actions. The workflow is defined in `.github/workflows/main.yml`.

*   **Scheduled Runs**: The workflow is pre-configured to run automatically every Sunday at 10:00 Israel time (07:00 UTC).

*   **Manual Trigger (Workflow Dispatch)**:
    You can manually trigger the workflow directly from the GitHub UI:
    1.  Navigate to your repository on GitHub.
    2.  Click on the **`Actions`** tab.
    3.  In the left sidebar, select the workflow named **`Check Google Drive GEDCOM File for Updates and Process`**.
    4.  On the right side, click the **`Run workflow`** dropdown button.
    5.  A dialog box will appear where you can optionally provide inputs:
        *   **`person_id`**: Enter the GEDCOM ID of the person from whom distances should be calculated (e.g., `@I1@`). If left empty, it will attempt to use a `PERSONID` from your GitHub Secrets.
        *   **`distance_threshold`**: Enter a numerical value for the distance threshold. Paths will only be shown for individuals whose genealogical distance from `person_id` exceeds this value. The default is `8`.
    6.  Click **`Run workflow`** to start the execution.

Upon successful completion of the workflow, a new GitHub Issue will be created in your repository, detailing the upcoming Hebrew calendar events.

## 🤝 Contributing

Contributions are highly welcome! If you have ideas for new features, bug fixes, or improvements, please feel free to:

*   Open an [issue](https://github.com/your-username/familytree/issues) to discuss your ideas or report bugs.
*   Submit a [pull request](https://github.com/your-username/familytree/pulls) with your proposed changes.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for full details.