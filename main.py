import os
from datetime import date, timedelta
import json
import logging

from constants import GOOGLE_DRIVE_FILE_ID, INPUT_GEDCOM_FILE, FIXED_GEDCOM_FILE, OUTPUT_CSV_FILE, HEBREW_WEEKDAYS, HEBREW_EVENT_NAMES, HEBREW_MONTHS_MAP
from google_drive_utils import download_gedcom_from_drive
from gedcom_utils import fix_gedcom_format, process_gedcom_file
from hebcal_api import get_hebrew_date_range_api, find_relevant_hebrew_dates, get_parasha_for_week

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

# --- Main Execution ---
if __name__ == "__main__":
    logging.info(f"Step 1: Downloading GEDCOM file from Google Drive (ID: {GOOGLE_DRIVE_FILE_ID})...")
    if not download_gedcom_from_drive(GOOGLE_DRIVE_FILE_ID, INPUT_GEDCOM_FILE):
        logging.error("Failed to download GEDCOM file. Exiting script.")
        exit(1)

    logging.info(f"\nStep 2: Fixing GEDCOM format: {INPUT_GEDCOM_FILE} -> {FIXED_GEDCOM_FILE}")
    fix_gedcom_format(INPUT_GEDCOM_FILE, FIXED_GEDCOM_FILE)
    logging.info("GEDCOM format fixing complete.")

    logging.info(f"\nStep 3: Processing GEDCOM file: {FIXED_GEDCOM_FILE} and saving to {OUTPUT_CSV_FILE}")
    processed_data_rows = process_gedcom_file(FIXED_GEDCOM_FILE, OUTPUT_CSV_FILE)

    if processed_data_rows:
        today_gregorian = date.today()
        hebrew_week_dates_map = get_hebrew_date_range_api(today_gregorian, 30)

        relevant_upcoming_dates = find_relevant_hebrew_dates(
            processed_data_rows, hebrew_week_dates_map
        )

        github_output_path = os.environ.get('GITHUB_OUTPUT')
        if github_output_path:
            with open(github_output_path, 'a') as fh:
                if relevant_upcoming_dates:
                    parasha = get_parasha_for_week(today_gregorian)
                    issue_title = f"{parasha} - תאריכים עבריים קרובים: {today_gregorian.strftime('%Y-%m-%d')}"

                    issue_body = f"## תאריכים עבריים קרובים ({today_gregorian.strftime('%Y-%m-%d')} עד {(today_gregorian + timedelta(days=7)).strftime('%Y-%m-%d')})\n\n"
                    issue_body += "### אירועים לשבוע העברי הקרוב:\n\n"

                    # Sort relevant dates for consistent issue output
                    relevant_upcoming_dates.sort(key=lambda x: x[0]) # Sort by Gregorian date

                    for gregorian_date, original_date_str_parsed, name, event_type in relevant_upcoming_dates:
                        hebrew_weekday = HEBREW_WEEKDAYS.get(gregorian_date.strftime('%A'), gregorian_date.strftime('%A'))
                        event_name = HEBREW_EVENT_NAMES.get(event_type, event_type)
                        # Improved formatting for each event
                        issue_body += f"#### **{hebrew_weekday}, {original_date_str_parsed}**\n"
                        issue_body += f"* **אירוע**: `{event_name}`\n"
                        issue_body += f"* **אדם/משפחה**: `{name}`\n\n"

                    print(f'issue_title={json.dumps(issue_title)}', file=fh)
                    print(f'issue_body={json.dumps(issue_body)}', file=fh)
                    print(f'has_relevant_dates=true', file=fh)
                else:
                    print(f'issue_title=""', file=fh)
                    print(f'issue_body=""', file=fh)
                    print(f'has_relevant_dates=false', file=fh)
        else:
            logging.warning("GITHUB_OUTPUT environment variable not set. Cannot set workflow outputs.")

        if not relevant_upcoming_dates:
            logging.info("No relevant upcoming dates found for the next week.")

    else:
        logging.info("\nNo data processed or extracted.")

    logging.info("\nScript finished.")
