# Developer Guide

## Introduction

Welcome to the Family Tree Event Notifier project! This guide provides developers with a comprehensive overview of the project's architecture, data flow, and development practices. The goal of this project is to automate the tracking of Hebrew calendar events from a GEDCOM file and generate informative GitHub issues.

## Architecture Overview

The application follows a modular architecture, with each module responsible for a specific part of the workflow. The high-level process is as follows:

1.  **Download**: The GEDCOM file is downloaded from a specified Google Drive location.
2.  **Clean & Parse**: The downloaded file is cleaned to ensure it conforms to the standard GEDCOM format, and then it is parsed to extract all individuals, families, and events.
3.  **Date Filtering**: The application fetches the upcoming week's Hebrew dates from the Hebcal API and identifies the events from the GEDCOM file that fall within this date range.
4.  **Graph Construction**: A family tree is constructed as a graph using the `networkx` library to represent relationships between individuals.
5.  **Distance Calculation**: For each upcoming event, the genealogical distance and path are calculated from a designated root person (`PERSONID`).
6.  **Issue Generation**: A GitHub issue is formatted with the details of all upcoming events, including names, dates, ages, and genealogical paths (if applicable), and is prepared for creation by a GitHub Actions workflow.

## Module Responsibilities

All core logic resides within the `family_tree_notifier/` package:

-   `family_tree_notifier/main.py`: This is the main entry point and orchestrator of the application. It calls the other modules in sequence to execute the workflow.
-   `family_tree_notifier/google_drive_utils.py`: Handles all interactions with the Google Drive API, including authentication and file downloading.
-   `family_tree_notifier/gedcom_utils.py`: Responsible for cleaning the raw GEDCOM file, parsing it to extract events, and handling the complexities of Hebrew date formats.
-   `family_tree_notifier/gedcom_graph.py`: Builds the `networkx` graph representation of the family tree and provides functions for calculating the shortest path between individuals.
-   `family_tree_notifier/hebcal_api.py`: Contains functions for interacting with the Hebcal API to fetch Hebrew date information and the weekly Torah portion (parasha).
-   `family_tree_notifier/constants.py`: A centralized module for storing application-wide constants, such as file paths, API endpoints, and mappings for Hebrew months and events.

## Data Flow

1.  **Input**: The primary input is a GEDCOM file (`tree.ged`), typically stored on Google Drive.
2.  **Cleaning**: `gedcom_utils.fix_gedcom_format()` (in `family_tree_notifier/gedcom_utils.py`) reads the input file and produces a cleaned version, `fixed_tree.ged`.
3.  **Parsing**: `gedcom_utils.process_gedcom_file()` parses `fixed_tree.ged` and generates `dates.csv`, which contains a list of all Hebrew date events found in the file.
4.  **Enrichment**: In `family_tree_notifier/main.py`, the data from `dates.csv` is filtered against the upcoming week's dates from the Hebcal API. This filtered list is then enriched with genealogical distance and path information.
5.  **Output**: The final enriched data is formatted into a Markdown string, which is then passed to the `GITHUB_OUTPUT` file in the GitHub Actions environment to be used as the body of the GitHub issue.

## Key Data Structures

-   **`enriched_list`**: This is a key data structure in `main.py`. It is a list of tuples, where each tuple represents an upcoming event and has the following structure:
    ```python
    (distance, path, gregorian_date, hebrew_date_str, name, event_type)
    ```
-   **`individual_details`**: A dictionary that stores the birth and death years for each individual, used for age calculations. The structure is:
    ```python
    {'Full Name': {'birth_year': 1950, 'death_year': 2020}}
    ```
-   **NetworkX Graph (`G`)**: The family tree is represented as a `networkx.Graph` object, where nodes are individual IDs (e.g., `'@I1@'`) and edges represent direct relationships (spouse-spouse, parent-child).

## Development Setup

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-username/familytree.git
    cd familytree
    ```
2.  **Create a virtual environment**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```
3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Local GEDCOM File**: For local development, you can bypass the Google Drive download by placing a GEDCOM file named `tree.ged` in the root of the repository.
5.  **Running the Script**: To run the script locally, use:
    ```bash
    python3 -m family_tree_notifier.main --lang en
    ```
6.  **Environment Variables**: The application is configured via environment variables. For local testing, you can set them in your shell:
    ```bash
    export PERSONID="@I1@"  # The root person for distance calculations
    export DISTANCE_THRESHOLD=8  # The threshold for displaying paths
    ```

## Running Tests

The project uses Python's built-in `unittest` framework. To run the tests, use the following command from the root of the repository:

```bash
python3 -m unittest discover tests
```

## Contributing

Contributions are welcome! Please follow these steps:

1.  Open an issue to discuss the proposed change or bug.
2.  Fork the repository and create a new branch for your feature or bug fix.
3.  Write your code, including tests to cover your changes.
4.  Ensure all existing and new tests pass.
5.  Submit a pull request with a clear description of your changes.
