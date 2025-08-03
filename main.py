#!/usr/bin/env python3
"""
main.py  –  GEDCOM downloader + Hebrew-date checker + GitHub-issue creator
New features compared to original:
  - builds a family-tree graph (NetworkX)
  - computes distance/path from PERSONID env-var to every person with upcoming
    birthday / yahrtzeit / anniversary
  - if distance > 8 the path is printed in the GitHub issue
"""

import os
import json
import logging
from datetime import date, timedelta

from constants import (
    GOOGLE_DRIVE_FILE_ID, INPUT_GEDCOM_FILE, FIXED_GEDCOM_FILE, OUTPUT_CSV_FILE,
    HEBREW_WEEKDAYS, HEBREW_EVENT_NAMES
)
from google_drive_utils import download_gedcom_from_drive
from gedcom_utils import fix_gedcom_format, process_gedcom_file
from hebcal_api import get_hebrew_date_range_api, find_relevant_hebrew_dates, get_parasha_for_week
from gedcom_graph import build_graph, distance_and_path

# ------------------------------------------------------------------ logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()]
)

# ------------------------------------------------------------------ helpers
def build_issue_body(enriched_list, id2name, today_gregorian):
    """
    enriched_list: list of tuples (distance, path, gregorian_date, heb_date_str, name, event_type)
    id2name      : dict mapping GEDCOM pointer -> display name
    """
    issue_body = (
        f"## תאריכים עבריים קרובים "
        f"({today_gregorian.strftime('%Y-%m-%d')} עד "
        f"{(today_gregorian + timedelta(days=7)).strftime('%Y-%m-%d')})\n\n"
    )

    # sort by date (closest first), then by distance
    enriched_list.sort(key=lambda t: (t[2], t[0]))

    for dist, path, gregorian_date, original_date_str_parsed, name, event_type in enriched_list:
        hebrew_weekday = HEBREW_WEEKDAYS.get(gregorian_date.strftime('%A'), gregorian_date.strftime('%A'))
        event_name = HEBREW_EVENT_NAMES.get(event_type, event_type)

        issue_body += f"#### **{hebrew_weekday}, {original_date_str_parsed}**\n"
        issue_body += f"* **אירוע**: `{event_name}`\n"
        issue_body += f"* **אדם/משפחה**: `{name}`\n"

        # include distance & path only if PERSONID was supplied and distance > 8
        PERSONID = os.getenv("PERSONID")
        if PERSONID and dist is not None and dist > 8:
            readable_path = " → ".join(id2name.get(p, p) for p in path)
            issue_body += f"* **מרחק**: `{dist}`\n"
            issue_body += f"* **נתיב**: `{readable_path}`\n"
        issue_body += "\n"

    return issue_body

# ------------------------------------------------------------------ main
def main():
    logging.info("Step 1: Downloading GEDCOM from Google Drive …")
    if not download_gedcom_from_drive(GOOGLE_DRIVE_FILE_ID, INPUT_GEDCOM_FILE):
        logging.error("Failed to download GEDCOM. Exiting.")
        return

    logging.info("Step 2: Fixing GEDCOM format …")
    fix_gedcom_format(INPUT_GEDCOM_FILE, FIXED_GEDCOM_FILE)

    logging.info("Step 3: Processing GEDCOM …")
    processed_rows = process_gedcom_file(FIXED_GEDCOM_FILE, OUTPUT_CSV_FILE)
    if not processed_rows:
        logging.info("No events found in GEDCOM.")
        return

    today_gregorian = date.today()
    hebrew_week_dates_map = get_hebrew_date_range_api(today_gregorian, 7)

    relevant_upcoming_dates = find_relevant_hebrew_dates(processed_rows, hebrew_week_dates_map)
    if not relevant_upcoming_dates:
        logging.info("No relevant upcoming Hebrew dates in the next 7 days.")
        return

    # ---------- build graph for distance / path ----------
    G, id2name = build_graph(FIXED_GEDCOM_FILE)
    PERSONID = os.getenv("PERSONID")

    enriched = []
    for gregorian_date, original_date_str_parsed, name, event_type in relevant_upcoming_dates:
        node = None
        for k, v in id2name.items():
            if v == name:
                node = k
                break
        if PERSONID and node:
            dist, path = distance_and_path(G, PERSONID, node)
            enriched.append((dist if dist is not None else 999, path,
                             gregorian_date, original_date_str_parsed, name, event_type))
        else:
            enriched.append((999, [], gregorian_date,
                             original_date_str_parsed, name, event_type))

    # ---------- build GitHub issue ----------
    parasha = get_parasha_for_week(today_gregorian)
    issue_title = f"{parasha} - תאריכים עבריים קרובים: {today_gregorian.strftime('%Y-%m-%d')}"
    issue_body = build_issue_body(enriched, id2name, today_gregorian)

    github_output_path = os.getenv("GITHUB_OUTPUT")
    if github_output_path:
        with open(github_output_path, "a", encoding="utf-8") as fh:
            print(f"issue_title={json.dumps(issue_title)}", file=fh)
            print(f"issue_body={json.dumps(issue_body)}", file=fh)
            print("has_relevant_dates=true", file=fh)
    else:
        logging.warning("GITHUB_OUTPUT not set – skipping workflow outputs.")

    logging.info("Script finished.")

# ------------------------------------------------------------------ entrypoint
if __name__ == "__main__":
    main()
