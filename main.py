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
import json
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
                    return "husband (of)"
                else:
                    return "wife (of)"

    # --- Check 2: p1 is Parent of p2 (Look up p2's FAMC) ---
    # FIX: Use find_sub_element helper instead of p2.get_sub_element
    p2_famc_element = find_sub_element(p2, 'FAMC')
    if p2_famc_element:
        famc_id = p2_famc_element.get_value()
        p2_child_family = parser.get_element_dictionary().get(famc_id)

        if p2_child_family:
            husband_id, wife_id = get_husband_and_wife_ids(p2_child_family)
            
            if husband_id and p1.get_pointer() == husband_id:
                return "father (of)"
            if wife_id and p1.get_pointer() == wife_id:
                return "mother (of)"

    # --- Check 3: p2 is Parent of p1 (Look up p1's FAMC) ---
    # FIX: Use find_sub_element helper instead of p1.get_sub_element
    p1_famc_element = find_sub_element(p1, 'FAMC')
    if p1_famc_element:
        famc_id = p1_famc_element.get_value()
        p1_child_family = parser.get_element_dictionary().get(famc_id)
        
        if p1_child_family:
            husband_id, wife_id = get_husband_and_wife_ids(p1_child_family)
            
            # Check if p2 is the father or mother of p1
            if (husband_id and p2.get_pointer() == husband_id) or \
               (wife_id and p2.get_pointer() == wife_id):
                if p1.get_gender() == "M":
                    return "son (of)"
                else:
                    return "daughter (of)"

    return "relative"
from hebcal import HebrewDate

def get_hebrew_year_from_date_str(date_str):
    if not date_str or not date_str.startswith("@#DHEBREW@"):
        return None
    parts = date_str.split()
    if len(parts) > 2:
        try:
            return int(parts[-1])
        except (ValueError, IndexError):
            return None
    return None

def get_event_details(event, individuals, current_hebrew_year):
    years_passed = None
    details = ""
    if event.get('year'):
        years_passed = current_hebrew_year - event['year']

    if event['event_type'] == 'יום הולדת' and not individuals.get(event['individual_id'], {}).get('death_date'):
        if years_passed is not None:
            age = years_passed
            details = f"🎂 ({years_passed} שנים, גיל {age})"
        else:
            details = "🎂"
    elif event['event_type'] == 'נישואין':
        detail_parts = []
        if years_passed is not None:
            detail_parts.append(f"{years_passed} שנים")

        husband_id = event.get('husband_id')
        wife_id = event.get('wife_id')

        if husband_id and not individuals.get(husband_id, {}).get('death_date'):
            birth_year = get_hebrew_year_from_date_str(individuals.get(husband_id, {}).get('birth_date'))
            if birth_year:
                age = current_hebrew_year - birth_year
                detail_parts.append(f"גיל הבעל: {age}")

        if wife_id and not individuals.get(wife_id, {}).get('death_date'):
            birth_year = get_hebrew_year_from_date_str(individuals.get(wife_id, {}).get('birth_date'))
            if birth_year:
                age = current_hebrew_year - birth_year
                detail_parts.append(f"גיל האישה: {age}")

        details = f"💍 ({', '.join(detail_parts)})" if detail_parts else "💍"
    elif event['event_type'] == 'יארצייט':
        detail_parts = []
        if years_passed is not None:
            detail_parts.append(f"{years_passed} שנים")

        birth_year = get_hebrew_year_from_date_str(individuals.get(event['individual_id'], {}).get('birth_date'))
        death_year = event.get('year')

        if birth_year and death_year:
            age_at_death = death_year - birth_year
            detail_parts.append(f"בן {age_at_death} בפטירתו")

        details = f"🕯️ ({', '.join(detail_parts)})" if detail_parts else "🕯️"

    if years_passed and years_passed > 0 and years_passed % 19 == 0:
        details += " (שנת י\"ט)"

    return details
def build_issue_body(enriched_list, id2name, today_gregorian, distance_threshold, person_id, parser, individuals):
    """
    enriched_list: list of tuples (distance, path, gregorian_date, event_dict)
    id2name      : dict mapping GEDCOM pointer -> display name
    person_id_from_env: The PERSONID value read from the environment in the main function.
    """
    issue_body = (
        f"## תאריכים עבריים קרובים "
        f"({today_gregorian.strftime('%Y-%m-%d')} עד "
        f"{(today_gregorian + timedelta(days=7)).strftime('%Y-%m-%d')})\n\n"
    )

    # sort by date (closest first), then by distance
    enriched_list.sort(key=lambda t: (t[2], t[0]))

    for dist, path, gregorian_date, event in enriched_list:
        hebrew_weekday = HEBREW_WEEKDAYS.get(gregorian_date.strftime('%A'), gregorian_date.strftime('%A'))
        event_name = HEBREW_EVENT_NAMES.get(event['event_type'], event['event_type'])
        event_details = get_event_details(event, individuals, HebrewDate.today().year)

        issue_body += f"#### **{hebrew_weekday}, {event['hebrew_date_formatted']} {event_details}**\n"
        issue_body += f"* **אירוע**: `{event_name}`\n"
        issue_body += f"* **אדם/משפחה**: `{event['name']}`\n"

        # include distance & path only if PERSONID was supplied and distance > 8
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
    logging.info("Step 1: Downloading GEDCOM from Google Drive …")
    if not download_gedcom_from_drive(GOOGLE_DRIVE_FILE_ID, INPUT_GEDCOM_FILE):
        logging.error("Failed to download GEDCOM. Exiting.")
        return

    logging.info("Step 2: Fixing GEDCOM format …")
    fix_gedcom_format(INPUT_GEDCOM_FILE, FIXED_GEDCOM_FILE)

    # Print the content of the fixed GEDCOM file for debugging
    logging.debug(f"Content of {FIXED_GEDCOM_FILE}:")
    with open(FIXED_GEDCOM_FILE, 'r', encoding='utf-8') as f:
        logging.debug(f.read())

    logging.info("Step 3: Processing GEDCOM …")
    person_id = os.environ.get('PERSONID')
    distance_threshold = os.environ.get('DISTANCE_THRESHOLD')
    processed_events, individuals = process_gedcom_file(FIXED_GEDCOM_FILE, OUTPUT_CSV_FILE)
    logging.debug(f"Processed events from GEDCOM: {processed_events}")

    if not processed_events:
        logging.info("No events found in GEDCOM.")
        return

    today_gregorian = date.today()
    hebrew_week_dates_map = get_hebrew_date_range_api(today_gregorian, 7)

    relevant_upcoming_dates = find_relevant_hebrew_dates(processed_events, hebrew_week_dates_map)

    # ---------- build graph for distance / path ----------
    gedcom_parser = Parser()
    gedcom_parser.parse_file(FIXED_GEDCOM_FILE)
    G, id2name = build_graph(FIXED_GEDCOM_FILE)
    PERSONID = os.getenv("PERSONID")
    try:
        distance_threshold = int(os.getenv("DISTANCE_THRESHOLD", DISTANCE_THRESHOLD))
    except (ValueError, TypeError):
        distance_threshold = DISTANCE_THRESHOLD

    enriched = []
    for gregorian_date, event in relevant_upcoming_dates:
        node_id = event.get('individual_id') or event.get('husband_id') # Use husband_id for family events as a representative

        dist, path = None, None
        if PERSONID and node_id and node_id in G:
            dist, path = distance_and_path(G, PERSONID, node_id)

        if dist is not None:
            enriched.append((dist, path, gregorian_date, event))
        else:
            enriched.append((999, [], gregorian_date, event))

    # ---------- build GitHub issue ----------
    parasha = get_parasha_for_week(today_gregorian)
    issue_title = f"{parasha} - תאריכים עבריים קרובים: {today_gregorian.strftime('%Y-%m-%d')}"
    issue_body = build_issue_body(enriched, id2name, today_gregorian, distance_threshold, person_id, parser, individuals)

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
