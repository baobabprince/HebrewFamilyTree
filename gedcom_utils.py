import re
import csv
import logging
from gedcom.parser import Parser
from constants import HEBREW_MONTHS_MAP, HEBREW_EVENT_NAMES, HEBREW_MONTH_NAMES_FULL, HEBREW_DAY_TO_NUM

def get_hebrew_day_string(day):
    """Converts a day number to its Hebrew letter representation."""
    hebrew_numerals = {
        1: "א", 2: "ב", 3: "ג", 4: "ד", 5: "ה", 6: "ו", 7: "ז", 8: "ח", 9: "ט", 10: "י",
        11: "יא", 12: "יב", 13: "יג", 14: "יד", 15: "טו", 16: "טז", 17: "יז", 18: "יח", 19: "יט",
        20: "כ", 21: "כא", 22: "כב", 23: "כג", 24: "כד", 25: "כה", 26: "כו", 27: "כז", 28: "כח", 29: "כט", 30: "ל"
    }
    return hebrew_numerals.get(day, str(day))

def get_hebrew_month_name(month_num):
    """Converts a month number to its Hebrew name."""
    return HEBREW_MONTH_NAMES_FULL.get(month_num, "")

def get_hebrew_date_from_gedcom_date(date_str):
    """
    Parses a Hebrew date from a GEDCOM date string.
    Returns a tuple (day, month_num) or None if parsing fails.
    """
    if not date_str or not date_str.startswith("@#DHEBREW@"):
        return None

    parsing_date_str = date_str[10:].strip()
    if not parsing_date_str:
        return None

    temp_date_parts = list(parsing_date_str.split())
    if not temp_date_parts:
        return None

    if temp_date_parts[0].upper() in ['BET', 'ABT', 'EST', 'CAL', 'FROM', 'TO', 'INT', 'AFT', 'BEF']:
        temp_date_parts = temp_date_parts[1:]
        if not temp_date_parts:
            return None
            
    day = 1
    month_abbr = None

    if len(temp_date_parts) >= 2:
        day_str = temp_date_parts[0].replace('"', '').strip()
        day_candidate = HEBREW_DAY_TO_NUM.get(day_str)
        if day_candidate is None:
            try:
                day_candidate = int(day_str)
            except ValueError:
                day_candidate = 0 # Invalid
        month_abbr_candidate = temp_date_parts[1].upper()
        if month_abbr_candidate in HEBREW_MONTHS_MAP:
            day = day_candidate
            month_abbr = month_abbr_candidate
    elif len(temp_date_parts) == 1:
        month_abbr_candidate = temp_date_parts[0].upper()
        if month_abbr_candidate in HEBREW_MONTHS_MAP:
            month_abbr = month_abbr_candidate
    
    if month_abbr and 1 <= day <= 30:
        return (day, HEBREW_MONTHS_MAP[month_abbr])

    return None

def process_event(event_element, name, dates, event_type=None):
    """Extracts and processes date from an event element."""
    for child in event_element.get_child_elements():
        if child.get_tag() == "DATE":
            date_str = child.get_value()
            hebrew_date = get_hebrew_date_from_gedcom_date(date_str)
            
            if hebrew_date:
                day, month_num = hebrew_date
                hebrew_month_name = get_hebrew_month_name(month_num)
                hebrew_date_formatted = f"{get_hebrew_day_string(day)} {hebrew_month_name}"
                event_tag_name = event_type or event_element.get_tag()
                
                dates.append((month_num, day, hebrew_date_formatted, f"{name} - {event_tag_name}: {hebrew_date_formatted}"))

def process_gedcom_file(file_path, output_csv_file):
    """
    Processes a GEDCOM file, extracts information, and writes to dates.csv.
    """
    gedcom_parser = Parser()
    try:
        gedcom_parser.parse_file(file_path, strict=False)
    except Exception as e:
        logging.error(f"Error parsing GEDCOM file {file_path}: {e}")
        return []

    root_child_elements = gedcom_parser.get_root_child_elements()
    dates = []
    individuals = {el.get_pointer(): get_name_from_individual(el) for el in root_child_elements if el.get_tag() == "INDI"}

    for element in root_child_elements:
        if element.get_tag() == "INDI":
            name = individuals.get(element.get_pointer(), "Unknown Individual")
            process_individual_events(element, name, dates)
        elif element.get_tag() == "FAM":
            process_family_events(element, individuals, dates)

    dates.sort(key=lambda x: (x[0], x[1]))

    csv_data_rows = []
    for _, _, original_date_str_parsed, output_str in dates:
        try:
            name, event_description = output_str.split(" - ", 1)
            event_type = event_description.split(":")[0].strip()
            csv_data_rows.append([original_date_str_parsed, name, event_type])
        except ValueError:
            csv_data_rows.append([original_date_str_parsed, "Error", "Error"])

    with open(output_csv_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Date", "Name", "Event"])
        writer.writerows(csv_data_rows)
    
    return csv_data_rows

# (rest of the file remains the same)
def get_name_from_individual(element):
    """Extracts name from an individual element."""
    for child in element.get_child_elements():
        if child.get_tag() == "NAME":
            return child.get_value().replace("/", "").strip()
    return "Unknown Name"

def process_individual_events(element, name, dates):
    """Processes birth, death, and other events for an individual."""
    individual_event_tags = [
        "BIRT", "DEAT", "CHR", "BURI", "CREM", "ADOP", "BAPM",
        "BARM", "BASM", "BLES", "CHRA", "CONF", "EMIG", "FCOM", "GRAD",
        "IMMI", "NATU", "ORDN", "RETI", "PROB", "WILL", "EVEN"
    ]
    for child in element.get_child_elements():
        if child.get_tag() in individual_event_tags:
            event_type_str = HEBREW_EVENT_NAMES.get(child.get_tag(), child.get_tag())
            process_event(child, name, dates, event_type=event_type_str)

def process_family_events(element, individuals, dates):
    """Processes marriage and other events for a family."""
    husband_id = None
    wife_id = None

    for child in element.get_child_elements():
        if child.get_tag() == 'HUSB':
            husband_id = child.get_value()
        elif child.get_tag() == 'WIFE':
            wife_id = child.get_value()

    husband_name = individuals.get(husband_id, "Unknown Husband")
    wife_name = individuals.get(wife_id, "Unknown Wife")
    couple_name = f"{husband_name} & {wife_name}"

    family_event_tags = ["MARR", "DIV", "ANUL", "ENGA", "MARB", "MARC", "MARL", "MARS", "EVEN"]
    for child in element.get_child_elements():
        if child.get_tag() in family_event_tags:
            event_type_str = HEBREW_EVENT_NAMES.get(child.get_tag(), child.get_tag())
            process_event(child, couple_name, dates, event_type=event_type_str)
