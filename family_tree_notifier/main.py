#!/usr/bin/env python3
"""
main.py  "".  GEDCOM downloader + Hebrew-date checker + GitHub-issue creator
New features compared to original:
  - builds a family-tree graph (NetworkX)
  - computes distance/path from PERSONID env-var to every person with upcoming
    birthday / yahrtzeit / anniversary
  - if distance > DISTANCE_THRESHOLD the path is printed in the GitHub issue
"""

import os
import logging
import argparse
from datetime import date, timedelta

from .constants import (
    GOOGLE_DRIVE_FILE_ID, INPUT_GEDCOM_FILE, FIXED_GEDCOM_FILE, OUTPUT_CSV_FILE,
    DISTANCE_THRESHOLD
)
from .google_drive_utils import download_gedcom_from_drive
from .gedcom_utils import fix_gedcom_format, process_gedcom_file
from .hebcal_api import get_hebrew_date_range_api, find_relevant_hebrew_dates, get_parasha_for_week
from gedcom.parser import Parser
from .gedcom_graph import build_graph, distance_and_path
from .localization import get_translation
from .issue_generator import build_issue_body


# ------------------------------------------------------------------ main
def main():
    """
    Main function to orchestrate the entire family tree event notification process.

    This script executes the following steps:
    1.  Downloads the GEDCOM file from Google Drive.
    2.  Fixes and cleans the GEDCOM file format.
    3.  Processes the GEDCOM to extract individuals, families, and Hebrew date events.
    4.  Fetches the upcoming week's Hebrew dates from the Hebcal API.
    5.  Identifies relevant events that fall within the upcoming week.
    6.  Builds a family tree graph to calculate genealogical distances.
    7.  Enriches the event data with distance and path information.
    8.  Constructs a title and body for a GitHub issue.
    9.  Writes the issue content to the `GITHUB_OUTPUT` file for use in a
        GitHub Actions workflow.
    """
    parser = argparse.ArgumentParser(description="Generate GitHub issues for upcoming Hebrew calendar events.")
    parser.add_argument("--lang", default="he", choices=["he", "en"], help="Language for the issue (he for Hebrew, en for English).")
    args = parser.parse_args()
    lang = args.lang

    # ------------------------------------------------------------------ logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.FileHandler("app.log"), logging.StreamHandler()]
    )
    logging.getLogger().setLevel(logging.INFO)

    logging.info("Step 1: Downloading GEDCOM from Google Drive …")
    if not download_gedcom_from_drive(GOOGLE_DRIVE_FILE_ID, INPUT_GEDCOM_FILE):
        logging.error("Failed to download GEDCOM. Exiting.")
        return

    logging.info("Step 2: Fixing GEDCOM format …")
    fix_gedcom_format(INPUT_GEDCOM_FILE, FIXED_GEDCOM_FILE)

    logging.debug(f"Content of {FIXED_GEDCOM_FILE}:")
    with open(FIXED_GEDCOM_FILE, 'r', encoding='utf-8') as f:
        logging.debug(f.read())

    logging.info("Step 3: Processing GEDCOM …")
    person_id = os.environ.get('PERSONID')
    distance_threshold = os.environ.get('DISTANCE_THRESHOLD')
    processed_rows, individual_details, family_details = process_gedcom_file(FIXED_GEDCOM_FILE, OUTPUT_CSV_FILE)
    logging.debug(f"Processed rows from GEDCOM: {processed_rows}")

    if not processed_rows:
        logging.info("No events found in GEDCOM.")
        return

    today_gregorian = date.today()
    hebrew_week_dates_map = get_hebrew_date_range_api(today_gregorian, 7)

    relevant_upcoming_dates = find_relevant_hebrew_dates(processed_rows, hebrew_week_dates_map, has_id_column=True)

    gedcom_parser = Parser()
    gedcom_parser.parse_file(FIXED_GEDCOM_FILE)
    G, id2name = build_graph(FIXED_GEDCOM_FILE)
    PERSONID = os.getenv("PERSONID")
    try:
        distance_threshold = int(os.getenv("DISTANCE_THRESHOLD", DISTANCE_THRESHOLD))
    except (ValueError, TypeError):
        distance_threshold = DISTANCE_THRESHOLD

    enriched = []
    for item in relevant_upcoming_dates:
        gregorian_date, original_date_str_parsed, name, event_type, gedcom_id = item

        dist = 999
        path = []

        if PERSONID and gedcom_id:
            # Handle marriage events with two IDs
            if "," in gedcom_id:
                husband_id, wife_id = gedcom_id.split(',')

                dist1, path1 = distance_and_path(G, PERSONID, husband_id)
                dist2, path2 = distance_and_path(G, PERSONID, wife_id)

                # Choose the shorter path
                if dist1 is not None and (dist2 is None or dist1 <= dist2):
                    dist, path = dist1, path1
                elif dist2 is not None:
                    dist, path = dist2, path2

            # Handle individual events
            else:
                dist_single, path_single = distance_and_path(G, PERSONID, gedcom_id)
                if dist_single is not None:
                    dist, path = dist_single, path_single

        enriched.append((dist, path, gregorian_date, original_date_str_parsed, name, event_type))

    parasha = get_parasha_for_week(today_gregorian, lang)
    issue_title_base = get_translation(lang, "issue_title")
    issue_title = f"{issue_title_base} {parasha}" if parasha else f"{issue_title_base}: {today_gregorian.strftime('%Y-%m-%d')}"
    issue_body = build_issue_body(enriched, id2name, today_gregorian, distance_threshold, person_id, gedcom_parser, individual_details, family_details, lang)

    github_output_path = os.getenv("GITHUB_OUTPUT")
    if github_output_path:
        with open(github_output_path, "a", encoding="utf-8") as fh:
            fh.write(f"issue_title={issue_title}\n")
            fh.write("issue_body<<EOF\n")
            fh.write(issue_body)
            fh.write("\nEOF\n")
            fh.write("has_relevant_dates=true\n")
    else:
        logging.warning("GITHUB_OUTPUT not set. skipping workflow outputs.")

    logging.info("Script finished.")    
# ------------------------------------------------------------------ entrypoint
if __name__ == "__main__":
    main()
