import os
import sys
import csv
from datetime import date, timedelta
from convertdate import hebrew
from gedcom.parser import Parser
from gedcom.element.individual import IndividualElement
from gedcom.element.family import FamilyElement
from calculate_distance import build_family_graph, get_person_name, calculate_distances, find_path
from constants import HEBREW_MONTHS_MAP, HEBREW_EVENT_NAMES, HEBREW_MONTH_NAMES_FULL

def get_hebrew_date_from_gedcom_date(gedcom_date_str):
    # This function needs to parse the GEDCOM Hebrew date format and return (day, month_num)
    # Example GEDCOM Hebrew date: "@#DHEBREW@ 15 Sivan 5784"
    if not gedcom_date_str or not gedcom_date_str.startswith("@#DHEBREW@"):
        return None

    parts = gedcom_date_str[10:].strip().split()
    if not parts:
        return None

    day = 1
    month_abbr = None

    if len(parts) >= 2:
        try:
            day_candidate = int(parts[0].replace('"', '').strip())
            month_abbr_candidate = parts[1].upper()
            if month_abbr_candidate in HEBREW_MONTHS_MAP:
                day = day_candidate
                month_abbr = month_abbr_candidate
        except ValueError:
            month_abbr_candidate = parts[0].upper()
            if month_abbr_candidate in HEBREW_MONTHS_MAP:
                month_abbr = month_abbr_candidate
    elif len(parts) == 1:
        month_abbr_candidate = parts[0].upper()
        if month_abbr_candidate in HEBREW_MONTHS_MAP:
            month_abbr = month_abbr_candidate

    if month_abbr and month_abbr in HEBREW_MONTHS_MAP:
        month_num = HEBREW_MONTHS_MAP[month_abbr]
        return day, month_num
    return None

def get_hebrew_month_name(month_num):
    return HEBREW_MONTH_NAMES_FULL.get(month_num, "")

def get_hebrew_day_string(day):
    hebrew_numerals = {
        1: "א", 2: "ב", 3: "ג", 4: "ד", 5: "ה", 6: "ו", 7: "ז", 8: "ח", 9: "ט", 10: "י",
        11: "יא", 12: "יב", 13: "יג", 14: "יד", 15: "טו", 16: "טז", 17: "יז", 18: "יח", 19: "יט",
        20: "כ", 21: "כב", 22: "כג", 24: "כד", 25: "כה", 26: "כו", 27: "כז", 28: "כח", 29: "כט", 30: "ל"
    }
    return hebrew_numerals.get(day, str(day))

def get_next_hebrew_dates(num_days=8):
    today_greg = date.today()
    today_hebrew = hebrew.from_gregorian(today_greg.year, today_greg.month, today_greg.day)
    
    hebrew_dates = []
    for i in range(num_days):
        current_greg = today_greg + timedelta(days=i)
        current_hebrew = hebrew.from_gregorian(current_greg.year, current_greg.month, current_greg.day)
        hebrew_dates.append((current_hebrew.day, current_hebrew.month))
    return hebrew_dates

def get_event_details(element, event_tag):
    for child in element.get_child_elements():
        if child.get_tag() == event_tag:
            for date_child in child.get_child_elements():
                if date_child.get_tag() == "DATE":
                    return date_child.get_value()
    return None

def get_marriage_details(family_element):
    for child in family_element.get_child_elements():
        if child.get_tag() == "MARR":
            for date_child in child.get_child_elements():
                if date_child.get_tag() == "DATE":
                    return date_child.get_value()
    return None

if __name__ == "__main__":
    gedcom_file = "fixed_tree.ged"
    distances_file = "distances.txt"
    person_id_env = os.getenv("PERSONID")

    if not person_id_env:
        print("Error: PERSONID environment variable not set.")
        sys.exit(1)

    # Load distances
    distances = {}
    try:
        with open(distances_file, "r", encoding="utf-8") as f:
            for line in f:
                if ":" in line:
                    parts = line.split(":")
                    name_id_part = parts[0].strip()
                    dist_part = parts[1].strip()
                    
                    # Extract ID from name_id_part like "Name (@ID@)"
                    id_match = name_id_part.rfind("@")
                    if id_match != -1:
                        indi_id = name_id_part[id_match:].replace("(", "").replace(")", "").strip()
                        try:
                            distances[indi_id] = int(dist_part)
                        except ValueError:
                            pass # Skip lines where distance is not an integer
    except FileNotFoundError:
        print(f"Error: {distances_file} not found. Please run calculate_distance.py first.")
        sys.exit(1)

    # Parse GEDCOM and build graph
    parser = Parser()
    parser.parse_file(gedcom_file)
    root_elements = parser.get_root_child_elements()

    individuals = {}
    families = {}
    graph = {}

    for element in root_elements:
        if element.get_tag() == 'INDI':
            indi_id = element.get_pointer()
            individuals[indi_id] = element
        elif element.get_tag() == 'FAM':
            fam_id = element.get_pointer()
            families[fam_id] = element

    graph, _ = build_family_graph(gedcom_file) # Re-use build_family_graph to get the graph

    next_hebrew_dates = get_next_hebrew_dates(8)

    issue_title = f"Upcoming Hebrew Calendar Events for {get_person_name(individuals[person_id_env])}"
    issue_body = []

    for indi_id, individual_element in individuals.items():
        person_name = get_person_name(individual_element)
        current_distance = distances.get(indi_id, -1)

        # Birthdays
        birt_date_str = get_event_details(individual_element, "BIRT")
        if birt_date_str:
            hebrew_birt_date = get_hebrew_date_from_gedcom_date(birt_date_str)
            if hebrew_birt_date and (hebrew_birt_date[0], hebrew_birt_date[1]) in next_hebrew_dates:
                hebrew_date_formatted = f"{get_hebrew_day_string(hebrew_birt_date[0])} ב{get_hebrew_month_name(hebrew_birt_date[1])}"
                event_desc = f"Birthday: {person_name} ({hebrew_date_formatted})"
                if current_distance > 8:
                    path = find_path(graph, person_id_env, indi_id)
                    if path:
                        path_names = [get_person_name(individuals[node_id]) for node_id in path]
                        event_desc += f" (Distance: {current_distance}, Path: {" -> ".join(path_names)})
                issue_body.append(event_desc)

        # Death days
        deat_date_str = get_event_details(individual_element, "DEAT")
        if deat_date_str:
            hebrew_deat_date = get_hebrew_date_from_gedcom_date(deat_date_str)
            if hebrew_deat_date and (hebrew_deat_date[0], hebrew_deat_date[1]) in next_hebrew_dates:
                hebrew_date_formatted = f"{get_hebrew_day_string(hebrew_deat_date[0])} ב{get_hebrew_month_name(hebrew_deat_date[1])}"
                event_desc = f"Death Day: {person_name} ({hebrew_date_formatted})"
                if current_distance > 8:
                    path = find_path(graph, person_id_env, indi_id)
                    if path:
                        path_names = [get_person_name(individuals[node_id]) for node_id in path]
                        event_desc += f" (Distance: {current_distance}, Path: {" -> ".join(path_names)})
                issue_body.append(event_desc)

    # Marriage days
    for fam_id, family_element in families.items():
        marr_date_str = get_marriage_details(family_element)
        if marr_date_str:
            hebrew_marr_date = get_hebrew_date_from_gedcom_date(marr_date_str)
            if hebrew_marr_date and (hebrew_marr_date[0], hebrew_marr_date[1]) in next_hebrew_dates:
                husband_id = None
                wife_id = None
                for child in family_element.get_child_elements():
                    if child.get_tag() == 'HUSB':
                        husband_id = child.get_value()
                    elif child.get_tag() == 'WIFE':
                        wife_id = child.get_value()
                
                husband_name = get_person_name(individuals.get(husband_id, None)) if husband_id else "Unknown"
                wife_name = get_person_name(individuals.get(wife_id, None)) if wife_id else "Unknown"
                
                hebrew_date_formatted = f"{get_hebrew_day_string(hebrew_marr_date[0])} ב{get_hebrew_month_name(hebrew_marr_date[1])}"
                event_desc = f"Marriage Day: {husband_name} & {wife_name} ({hebrew_date_formatted})"

                # Check distance for both husband and wife if available
                if husband_id and distances.get(husband_id, -1) > 8:
                    path = find_path(graph, person_id_env, husband_id)
                    if path:
                        path_names = [get_person_name(individuals[node_id]) for node_id in path]
                        event_desc += f" (Husband Distance: {distances.get(husband_id)}, Path: {" -> ".join(path_names)})"
                
                if wife_id and distances.get(wife_id, -1) > 8:
                    path = find_path(graph, person_id_env, wife_id)
                    if path:
                        path_names = [get_person_name(individuals[node_id]) for node_id in path]
                        event_desc += f" (Wife Distance: {distances.get(wife_id)}, Path: {" -> ".join(path_names)})"
                
                issue_body.append(event_desc)

    if not issue_body:
        issue_body.append("No upcoming Hebrew calendar events in the next 8 days.")

    print(f"ISSUE_TITLE={issue_title}")
    print("ISSUE_BODY<<EOF")
    print("\n".join(issue_body))
    print("EOF")