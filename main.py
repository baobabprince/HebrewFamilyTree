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
from datetime import date, timedelta

from constants import (
    GOOGLE_DRIVE_FILE_ID, INPUT_GEDCOM_FILE, FIXED_GEDCOM_FILE, OUTPUT_CSV_FILE,
    HEBREW_WEEKDAYS, HEBREW_EVENT_NAMES, DISTANCE_THRESHOLD
)
from google_drive_utils import download_gedcom_from_drive
from gedcom_utils import fix_gedcom_format, process_gedcom_file
from hebcal_api import get_hebrew_date_range_api, find_relevant_hebrew_dates, get_parasha_for_week
from gedcom.parser import Parser
from gedcom_graph import build_graph, distance_and_path
# ------------------------------------------------------------------ logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()]
)
logging.getLogger().setLevel(logging.INFO)

# ------------------------------------------------------------------ helpers
def get_relationship(p1_id, p2_id, parser):
    """
    Determines the direct relationship between two individuals in the family tree.

    This function checks for parent-child, child-parent, and spousal relationships
    by examining the family (`FAM`) records associated with each individual.

    Args:
        p1_id (str): The GEDCOM pointer ID of the first person.
        p2_id (str): The GEDCOM pointer ID of the second person.
        parser (Parser): The initialized GEDCOM parser instance containing the
                         parsed family tree.

    Returns:
        str: A string describing the relationship (e.g., "husband (of)",
             "father (of)", "son (of)", "relative"). Returns
             "unknown/non-individual" if one of the IDs is not a valid
             individual.
    """
    # Helper to find a specific sub-element (like FAMC) by tag
    def find_sub_element(element, tag):
        for child in element.get_child_elements():
            if child.get_tag() == tag:
                return child
        return None

    def get_husband_and_wife_ids(family):
        husband_id = None
        wife_id = None
        for child in family.get_child_elements():
            if child.get_tag() == 'HUSB':
                husband_id = child.get_value()
            elif child.get_tag() == 'WIFE':
                wife_id = child.get_value()
        return husband_id, wife_id
    
    # Get the individual elements
    try:
        p1 = parser.get_element_dictionary()[p1_id]
        p2 = parser.get_element_dictionary()[p2_id]
    except KeyError:
        return "unknown/non-individual"

    # --- Check 1: Spouses ---
    p1_families_as_spouse = parser.get_families(p1)
    for family in p1_families_as_spouse:
        husband_id, wife_id = get_husband_and_wife_ids(family)
        if husband_id and wife_id:
            if (p1.get_pointer() == husband_id and p2.get_pointer() == wife_id) or \
               (p1.get_pointer() == wife_id and p2.get_pointer() == husband_id):
                if p1.get_gender() == "M":
                    return "בעלה של"
                else:
                    return "אשתו של"

    # --- Check 2: p1 is Parent of p2 (Look up p2's FAMC) ---
    p2_famc_element = find_sub_element(p2, 'FAMC')
    if p2_famc_element:
        famc_id = p2_famc_element.get_value()
        p2_child_family = parser.get_element_dictionary().get(famc_id)

        if p2_child_family:
            husband_id, wife_id = get_husband_and_wife_ids(p2_child_family)
            
            if husband_id and p1.get_pointer() == husband_id:
                return "אבא של"
            if wife_id and p1.get_pointer() == wife_id:
                return "אמא של"

    # --- Check 3: p2 is Parent of p1 (Look up p1's FAMC) ---
    p1_famc_element = find_sub_element(p1, 'FAMC')
    if p1_famc_element:
        famc_id = p1_famc_element.get_value()
        p1_child_family = parser.get_element_dictionary().get(famc_id)
        
        if p1_child_family:
            husband_id, wife_id = get_husband_and_wife_ids(p1_child_family)
            
            if (husband_id and p2.get_pointer() == husband_id) or \
               (wife_id and p2.get_pointer() == wife_id):
                if p1.get_gender() == "M":
                    return "בן של"
                else:
                    return "בת של"

    return "relative"
def build_issue_body(enriched_list, id2name, today_gregorian, distance_threshold, person_id, parser, individual_details):
    """
    Constructs the Markdown body for the GitHub issue.

    This function formats a list of upcoming events into a human-readable
    Markdown string. It includes emojis, age calculations, and the genealogical
    path from the `PERSONID` if the distance exceeds the threshold.

    Args:
        enriched_list (list): A list of tuples, where each tuple contains event
                              details: (distance, path, gregorian_date,
                              heb_date_str, name, event_type).
        id2name (dict): A dictionary mapping GEDCOM pointers to display names.
        today_gregorian (date): The current date, for the issue header.
        distance_threshold (int): The distance beyond which the genealogical path
                                  should be displayed.
        person_id (str): The GEDCOM pointer ID of the person from whom distances
                         are calculated.
        parser (Parser): The initialized GEDCOM parser instance.
        individual_details (dict): A dictionary with birth/death years for age calculation.

    Returns:
        str: The formatted Markdown string for the GitHub issue body.
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

        # --- Emojis and Age ---
        emoji = ""
        age_str = ""
        if event_type == HEBREW_EVENT_NAMES["BIRT"]:
            emoji = "🎂"
            if name in individual_details and individual_details[name].get("birth_year"):
                birth_year = individual_details[name]["birth_year"]
                age = gregorian_date.year - birth_year
                age_str = f" (גיל {age})"
        elif event_type == HEBREW_EVENT_NAMES["DEAT"]:
            emoji = "🪦"
            if name in individual_details and individual_details[name].get("birth_year") and individual_details[name].get("death_year"):
                birth_year = individual_details[name]["birth_year"]
                death_year = individual_details[name]["death_year"]
                age = death_year - birth_year
                age_str = f" (נפטר בגיל {age})"
        elif event_type == HEBREW_EVENT_NAMES["MARR"]:
            emoji = "💑"

        issue_body += f"#### **{emoji} {hebrew_weekday}, {original_date_str_parsed}**\n"
        issue_body += f"* **אירוע**: `{event_name}`\n"
        issue_body += f"* **אדם/משפחה**: `{name}{age_str}`\n"

        if person_id and dist is not None and dist > distance_threshold and path:
            path_parts = []
            reversed_path = list(reversed(path))
            for i in range(len(reversed_path) - 1):
                p1_id = reversed_path[i]
                p2_id = reversed_path[i+1]
                p1_name = id2name.get(p1_id, p1_id)
                relationship = get_relationship(p1_id, p2_id, parser)
                path_parts.append(f"{p1_name} ({relationship})")
            
            path_parts.append(id2name.get(reversed_path[-1], reversed_path[-1]))
            readable_path = " ".join(path_parts)
            issue_body += f"* **מרחק**: `{dist}`\n"
            issue_body += f"* **נתיב**: `{readable_path}`\n"
        issue_body += "\n"

    return issue_body


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
    processed_rows, individual_details = process_gedcom_file(FIXED_GEDCOM_FILE, OUTPUT_CSV_FILE)
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

    parasha = get_parasha_for_week(today_gregorian)
    issue_title = f"{parasha} - תאריכים עבריים קרובים: {today_gregorian.strftime('%Y-%m-%d')}"
    issue_body = build_issue_body(enriched, id2name, today_gregorian, distance_threshold, person_id, gedcom_parser, individual_details)

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
