import re
import csv
import logging
from gedcom.parser import Parser
from constants import HEBREW_MONTHS_MAP, HEBREW_EVENT_NAMES, HEBREW_MONTH_NAMES_FULL, HEBREW_DAY_TO_NUM

# Configure logging for gedcom_utils
logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(logging.INFO) # Keep INFO for normal operation
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def get_hebrew_day_string(day):
    """Converts a day number to its Hebrew letter representation."""
    hebrew_numerals = {
        1: "א", 2: "ב", 3: "ג", 4: "ד", 5: "ה", 6: "ו", 7: "ז", 8: "ח", 9: "ט", 10: "י",
        11: "יא", 12: "יב", 13: "יג", 14: "יד", 15: "טו", 16: "טז", 17: "יז", 18: "יח", 19: "יט",
        20: "כ", 21: "כא", 22: "כב", 23: "כג", 24: "כד", 25: "כה", 26: "כו", 27: "כז", 28: "כח", 29: "כט", 30: "ל"
    }
    return hebrew_numerals.get(day, str(day))

def fix_gedcom_format(input_file, output_file):
    """
    Fixes the format of a GEDCOM file by normalizing spacing AND removing
    any line that does not conform to the basic GEDCOM line structure.
    """
    try:
        with open(input_file, "r", encoding="utf-8-sig", errors="replace") as file:
            lines = file.readlines()
    except Exception as e:
        logger.error(f"Error reading input file {input_file}: {e}")
        return

    fixed_lines = []
    
    # Regex for VALID GEDCOM line: Level, Optional XREF_ID, Tag, Optional Value
    GEDCOM_LINE_REGEX = re.compile(r'^(\d+)\s+(?:(@\S+@)\s+)?(\S+)(?:\s+(.*))?$')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        match = GEDCOM_LINE_REGEX.match(line)
        
        if match:
            level, xref_id, tag, value = match.groups()
            
            # Reconstruct the line with normalized single spaces
            parts = [level]
            if xref_id:
                parts.append(xref_id)
            parts.append(tag)
            # Normalize spaces within the value part as well
            if value:
                parts.append(" ".join(value.split())) # FIX: Normalize spaces in value
            
            fixed_line = " ".join(parts)
            fixed_lines.append(fixed_line)
        else:
            # *Crucial Change*: Instead of keeping the original line, drop it and log the warning.
            logger.warning(f"Dropping non-GEDCOM-compliant line: {line}")
            # Do NOT append 'line' to 'fixed_lines'

    try:
        with open(output_file, "w", encoding="utf-8") as file:
            for line_to_write in fixed_lines:
                file.write(line_to_write + "\n")
        logger.info(f"Successfully fixed and saved GEDCOM to {output_file}")
    except Exception as e:
        logger.error(f"Error writing output file {output_file}: {e}")


def get_name_from_individual(element):
    """Extracts name from an individual element."""
    for child in element.get_child_elements():
        if child.get_tag() == "NAME":
            return child.get_value().replace("/", "").strip()
    return "Unknown Name"

def process_individual_events(element, name, dates, individual_details):
    """Processes birth, death, and other events for an individual."""
    individual_event_tags = [
        "BIRT", "DEAT", "CHR", "BURI", "CREM", "ADOP", "BAPM",
        "BARM", "BASM", "BLES", "CHRA", "CONF", "EMIG", "FCOM", "GRAD",
        "IMMI", "NATU", "ORDN", "RETI", "PROB", "WILL", "EVEN"
    ]
    for child in element.get_child_elements():
        if child.get_tag() in individual_event_tags:
            event_type_str = HEBREW_EVENT_NAMES.get(child.get_tag(), child.get_tag())
            gregorian_year = process_event(child, name, dates, event_type=event_type_str)

            if gregorian_year:
                if child.get_tag() == "BIRT":
                    individual_details[name]["birth_year"] = gregorian_year
                elif child.get_tag() == "DEAT":
                    individual_details[name]["death_year"] = gregorian_year

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
            event_type_str = child.get_tag()
            if child.get_tag() == "MARR":
                event_type_str = HEBREW_EVENT_NAMES.get(child.get_tag(), child.get_tag())
            process_event(child, couple_name, dates, event_type=event_type_str)

def process_event(event_element, name, dates, event_type=None):
    """Extracts and processes date from an event element."""
    gregorian_year = None
    for child in event_element.get_child_elements():
        if child.get_tag() == "DATE":
            date_str = child.get_value()

            # --- Extract Gregorian Year from within parentheses, if present ---
            paren_match = re.search(r'\((.*?)\)', date_str)
            if paren_match:
                content_in_paren = paren_match.group(1)
                year_in_paren_match = re.search(r'(\d{4})', content_in_paren)
                if year_in_paren_match:
                    gregorian_year = int(year_in_paren_match.group(1))

            if not date_str:
                continue

            if not date_str.startswith("@#DHEBREW@"):
                # If it's not a Hebrew date, try to extract a simple 4-digit Gregorian year
                # and then skip further processing for Hebrew dates.
                if gregorian_year is None: # If not found in (YYYY) format
                    simple_greg_match = re.search(r'(\d{4})', date_str)
                    if simple_greg_match:
                        gregorian_year = int(simple_greg_match.group(1))
                continue # This continue is correct here: skip Hebrew date parsing for non-Hebrew dates

            parsing_date_str = date_str[10:].strip()
            # If no Gregorian year was found in parentheses, check for a 4-digit year in the Hebrew part
            if gregorian_year is None:
                hebrew_year_match = re.search(r'\s(\d{4})$', parsing_date_str)
                if hebrew_year_match:
                    # Treat Hebrew year as Gregorian for now if no explicit Gregorian year is provided
                    gregorian_year = int(hebrew_year_match.group(1))
            
            if not parsing_date_str:
                continue

            temp_date_parts = list(parsing_date_str.split())
            
            day = 1 # Default day to 1
            month_abbr = None
            month_found_index = -1

            # Try to match two-word month names first (e.g., ADAR I)
            for i in range(len(temp_date_parts) - 1):
                compound_month_candidate = f"{temp_date_parts[i].upper()} {temp_date_parts[i+1].upper()}"
                if compound_month_candidate in HEBREW_MONTHS_MAP:
                    month_abbr = compound_month_candidate
                    month_found_index = i
                    break
            
            # If no two-word month found, try single-word month names
            if month_abbr is None:
                for i in range(len(temp_date_parts)):
                    single_month_candidate = temp_date_parts[i].upper()
                    if single_month_candidate in HEBREW_MONTHS_MAP:
                        month_abbr = single_month_candidate
                        month_found_index = i
                        break
            
            # If a month was found, try to extract the day from the part before it
            if month_abbr and month_found_index > 0:
                day_str = temp_date_parts[month_found_index - 1].replace('"', '').strip()
                try:
                    day_candidate = int(day_str)
                    day = day_candidate
                except ValueError:
                    pass # Day remains 1 if not parseable or not present

            if month_abbr and month_abbr in HEBREW_MONTHS_MAP:
                month_num = HEBREW_MONTHS_MAP[month_abbr]
                event_tag_name = event_type or event_element.get_tag()
                
                hebrew_month_name = HEBREW_MONTH_NAMES_FULL.get(month_num, "")
                hebrew_date_formatted = f"{get_hebrew_day_string(day)} {hebrew_month_name}"

                dates.append((month_num, day, hebrew_date_formatted, f"{name} - {event_tag_name}: {hebrew_date_formatted}"))
            else:
                logger.debug(f"Month abbreviation '{month_abbr}' not found in HEBREW_MONTHS_MAP or month_abbr is None.")
    return gregorian_year


def process_gedcom_file(file_path, output_csv_file):
    """
    Processes a GEDCOM file, extracts information, and writes to dates.csv.
    """
    gedcom_parser = Parser()
    try:
        gedcom_parser.parse_file(file_path)
    except Exception as e:
        logger.error(f"Error parsing GEDCOM file {file_path}: {e}")
        return [], {{}}

    root_child_elements = gedcom_parser.get_root_child_elements()

    dates = []
    individuals = {{}}
    individual_details = {{}}  # Store birth and death years

    for element in root_child_elements:
        if element.get_tag() == "INDI":
            individual_id = element.get_pointer()
            name = get_name_from_individual(element)
            individuals[individual_id] = name
            individual_details[name] = {{"birth_year": None, "death_year": None}}

    for element in root_child_elements:
        if element.get_tag() == "INDI":
            name = individuals.get(element.get_pointer(), "Unknown Individual")
            # --- Modified to pass individual_details ---
            process_individual_events(element, name, dates, individual_details)
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
            logger.warning(f"Could not parse output string for CSV: {output_str}")
            csv_data_rows.append([original_date_str_parsed, "Error in processing", "Error"])

    with open(output_csv_file, 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(["Date", "Name", "Event"])
        csv_writer.writerows(csv_data_rows)
    
    logger.info(f"Data successfully written to {output_csv_file}")
    logger.debug(f"Dates list before returning: {dates}")
    return csv_data_rows, individual_details
