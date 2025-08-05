# Family Tree Event Notifier

This project automates the process of tracking and notifying about upcoming Hebrew calendar events (birthdays, yahrtzeits, anniversaries) within a family tree, based on a GEDCOM file. It calculates the genealogical distance from a specified `PERSONID` to relevant individuals and generates GitHub issues with event details and, optionally, the path to the person if their distance exceeds a configurable threshold.

## Features

*   **GEDCOM Processing**: Downloads and processes GEDCOM files, extracting individual and family event data.
*   **Hebrew Date Conversion**: Converts Gregorian dates from the GEDCOM file to Hebrew dates and identifies upcoming events.
*   **Family Graph & Distance Calculation**: Builds a family graph using NetworkX to compute the shortest genealogical distance between individuals and the specified `PERSONID`.
*   **Path Tracking**: For individuals whose distance from the `PERSONID` exceeds a defined threshold, the genealogical path is included in the notification.
*   **GitHub Issue Generation**: Automatically creates GitHub issues with details of upcoming events, including names, event types, Hebrew dates, distances, and paths.
*   **Configurable Workflow**: Allows setting the `PERSONID` and `DISTANCE_THRESHOLD` directly from the GitHub Actions workflow dispatch interface.

## Setup

### Prerequisites

*   Python 3.8+
*   A Google Drive account with a shared GEDCOM file.
*   A GitHub repository to host the project and create issues.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/familytree.git
    cd familytree
    ```
2.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: A `requirements.txt` file should be created if not already present, containing `google-api-python-client`, `google-auth-httplib2`, `google-auth-oauthlib`, `google-auth`, `python-gedcom`, `requests`, `networkx`, `hebcal`)*

### Configuration

1.  **Google Drive API Credentials:**
    *   Follow the Google Cloud documentation to set up a service account and enable the Google Drive API.
    *   Download the service account's JSON key file.
    *   Add the content of this JSON file as a GitHub Secret named `GOOGLE_CREDENTIALS_JSON` in your repository settings.
    *   Share your GEDCOM file on Google Drive with the service account's email address.
    *   Update the `GOOGLE_DRIVE_FILE_ID` in `constants.py` (or set it as an environment variable) with the ID of your GEDCOM file.

2.  **GitHub Token:**
    *   The workflow uses `GITHUB_TOKEN` which is automatically provided by GitHub Actions for creating issues. No manual setup is required for this.

3.  **Environment Variables (Optional for local runs):**
    *   `PERSONID`: The GEDCOM ID of the person from whom distances will be calculated (e.g., `@I1@`).
    *   `DISTANCE_THRESHOLD`: The maximum distance for which a path will be displayed in the issue (default: 8).

## Usage

### Local Execution

To run the script locally (for testing or development):

```bash
export PERSONID="@I1@" # Replace with your desired GEDCOM ID
export DISTANCE_THRESHOLD=5 # Optional: Set a custom distance threshold
python main.py
```
The script will generate `fixed_tree.ged` and `dates.csv` files, and print log messages to the console.

### GitHub Actions Workflow

The project includes a GitHub Actions workflow (`.github/workflows/main.yml`) that automates the process.

*   **Scheduled Run**: The workflow is configured to run every Sunday at 10:00 Israel time (07:00 UTC).
*   **Manual Trigger**: You can manually trigger the workflow from the GitHub UI:
    1.  Go to your repository on GitHub.
    2.  Click on the "Actions" tab.
    3.  Select the "Check Google Drive GEDCOM File for Updates and Process" workflow from the left sidebar.
    4.  Click on "Run workflow" button on the right.
    5.  You can optionally provide `person_id` and `distance_threshold` inputs in the dialog box.

Upon successful execution, a new GitHub Issue will be created in your repository with the upcoming Hebrew calendar events.

## Contributing

Contributions are welcome! Please feel free to open issues or submit pull requests.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
