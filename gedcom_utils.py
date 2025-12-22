import re
import csv
import logging
from gedcom.parser import Parser
from gedcom.element.element import Element
from constants import HEBREW_MONTHS_MAP, HEBREW_EVENT_NAMES, HEBREW_MONTH_NAMES_FULL, HEBREW_DAY_TO_NUM
from hebcal_api import get_gregorian_date_from_hebrew_api

# Configure logging for gedcom_utils
logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(logging.INFO) # Keep INFO for normal operation
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def get_hebrew_day_string(day):
    """
    Converts a numerical day of the month to its Hebrew letter equivalent.

    Args:
        day (int): The day of the month (1-30).

    Returns:
        str: The Hebrew letter representation of the day (e.g., "א", "יב", "ל").
             Returns the original day as a string if not in the range 1-30.
    """
    hebrew_numerals = {
        1: "א", 2: "ב", 3: "ג", 4: "ד", 5: "ה", 6: "ו", 7: "ז", 8: "ח", 9: "ט", 10: "י",
        11: "יא", 12: "יב", 13: "יג", 14: "יד", 15: "טו", 16: "טז", 17: "יז", 18: "יח", 19: "יט",
        20: "כ", 21: "כא", 22: "כב", 23: "כג", 24: "כד", 25: "כה", 26: "כו", 27: "כז", 28: "כח", 29: "כט", 30: "ל"
    }
    return hebrew_numerals.get(day, str(day))

def fix_gedcom_format(input_file, output_file):
    """
    Reads a GEDCOM file, normalizes spacing, and removes non-compliant lines.

    This function cleans a GEDCOM file by:
    1.  Ensuring consistent single-spacing between elements on each line.
    2.  Stripping leading/trailing whitespace from each line.
    3.  Validating each line against a regex for the standard GEDCOM format
        (level, optional ID, tag, optional value).
    4.  Discarding any lines that do not match this format to prevent parsing errors.

    Args:
        input_file (str): The path to the source GEDCOM file.
        output_file (str): The path where the cleaned GEDCOM file will be saved.
    """
    try:
        with open(input_file, "r", encoding="utf-8-sig", errors="replace") as file:
            lines = file.readlines()
    except Exception as e:
        logger.error(f"Error reading input file {input_file}: {e}")
        return

    fixed_lines = []
    
    # Regex for a valid GEDCOM line: Level, Optional XREF_ID, Tag, Optional Value
    GEDCOM_LINE_REGEX = re.compile(r'^(\d+)\s+(?:(@\S+@)\s+)?(\S+)(?:\s+(.*))?$')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Replace the custom tag before regex matching to prevent it being parsed as an ID
        line = line.replace("@#DHEBREW@", "HEBREW_DATE")

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
                parts.append(" ".join(value.split()))
            
            fixed_line = " ".join(parts)
            fixed_lines.append(fixed_line)
        else:
            logger.warning(f"Dropping non-GEDCOM-compliant line: {line}")

    try:
        with open(output_file, "w", encoding="utf-8") as file:
            for line_to_write in fixed_lines:
                file.write(line_to_write + "\n")
        logger.info(f"Successfully fixed and saved GEDCOM to {output_file}")
    except Exception as e:
        logger.error(f"Error writing output file {output_file}: {e}")


def get_name_from_individual(element):
    """
    Extracts the full name from a GEDCOM individual (`INDI`) element.

    Args:
        element (Element): A GEDCOM element representing an individual.

    Returns:
        str: The formatted name of the individual, or "Unknown Name" if not found.
    """
    for child in element.get_child_elements():
        if child.get_tag() == "NAME":
            return child.get_value().replace("/", "").strip()
    return "Unknown Name"

def process_individual_events(element, name, dates, individual_details):
    """
    Parses events (like birth and death) for a single individual.

    This function iterates through the sub-elements of an individual (`INDI`)
    record, identifies event tags, and calls `process_event` to handle date
    extraction. It also populates the `individual_details` dictionary with
    birth and death years.

    Args:
        element (Element): The GEDCOM `INDI` element for the individual.
        name (str): The name of the individual.
        dates (list): A list to which extracted Hebrew date tuples are appended.
        individual_details (dict): A dictionary to store birth and death years for the individual.
    """
    individual_id = element.get_pointer()
    individual_event_tags = [
        "BIRT", "DEAT", "CHR", "BURI", "CREM", "ADOP", "BAPM",
        "BARM", "BASM", "BLES", "CHRA", "CONF", "EMIG", "FCOM", "GRAD",
        "IMMI", "NATU", "ORDN", "RETI", "PROB", "WILL", "EVEN"
    ]
    for child in element.get_child_elements():
        if child.get_tag() in individual_event_tags:
            event_type_str = HEBREW_EVENT_NAMES.get(child.get_tag(), child.get_tag())
            gregorian_year = process_event(child, name, dates, event_type=event_type_str, individual_id=individual_id)

            if gregorian_year:
                if child.get_tag() == "BIRT":
                    individual_details[name]["birth_year"] = gregorian_year
                elif child.get_tag() == "DEAT":
                    individual_details[name]["death_year"] = gregorian_year

def process_family_events(element, individuals, dates):
    """
    Parses events (like marriage) for a single family unit.

    This function identifies the husband and wife in a family (`FAM`) record,
    constructs a couple's name, and then calls `process_event` for each
    family-related event tag (e.g., `MARR`).

    Args:
        element (Element): The GEDCOM `FAM` element for the family.
        individuals (dict): A dictionary mapping individual IDs to names.
        dates (list): A list to which extracted Hebrew date tuples are appended.
    """
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
            process_event(child, couple_name, dates, event_type=event_type_str, husband_id=husband_id, wife_id=wife_id)

def process_event(event_element, name, dates, event_type=None, individual_id=None, husband_id=None, wife_id=None):
    """
    Extracts, parses, and processes a date from a GEDCOM event element.

    This function handles both standard Gregorian and special Hebrew dates
    (prefixed with `@#DHEBREW@`). It attempts to extract a Gregorian year for
    age calculation and parses the Hebrew date components to store for later
    comparison.

    Args:
        event_element (Element): The GEDCOM element for a specific event (e.g., `BIRT`, `MARR`).
        name (str): The name of the individual or couple associated with the event.
        dates (list): The master list where extracted date tuples are stored.
        event_type (str, optional): The type of event. Defaults to None.

    Returns:
        int or None: The Gregorian year of the event if found, otherwise None.
    """
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

            # Check for the new HEBREW_DATE marker
            if not date_str.startswith("HEBREW_DATE"):
                # If it's not a Hebrew date, try to extract a simple 4-digit Gregorian year
                # and then skip further processing for Hebrew dates.
                if gregorian_year is None: # If not found in (YYYY) format
                    simple_greg_match = re.search(r'(\d{4})', date_str)
                    if simple_greg_match:
                        gregorian_year = int(simple_greg_match.group(1))
                continue

            parsing_date_str = date_str.replace("HEBREW_DATE", "").strip()
            if not parsing_date_str:
                continue

            temp_date_parts = list(parsing_date_str.split())
            
            day = 1 # Default day to 1
            month_abbr = None
            month_found_index = -1
            hebrew_year = None

            hebrew_year_match = re.search(r'\s(\d{4})$', parsing_date_str)
            if hebrew_year_match:
                hebrew_year = int(hebrew_year_match.group(1))

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
                    pass

            if gregorian_year is None and hebrew_year and month_abbr and month_abbr in HEBREW_MONTHS_MAP:
                month_num = HEBREW_MONTHS_MAP[month_abbr]
                converted_gregorian_year = get_gregorian_date_from_hebrew_api(hebrew_year, month_num, day)
                if converted_gregorian_year:
                    gregorian_year = converted_gregorian_year
                else:
                    gregorian_year = hebrew_year  # Fallback to Hebrew year

            if month_abbr and month_abbr in HEBREW_MONTHS_MAP:
                month_num = HEBREW_MONTHS_MAP[month_abbr]
                event_tag_name = event_type or event_element.get_tag()
                
                hebrew_month_name = HEBREW_MONTH_NAMES_FULL.get(month_num, "")
                hebrew_date_formatted = f"{get_hebrew_day_string(day)} {hebrew_month_name}"

                dates.append((month_num, day, hebrew_date_formatted, f"{name} - {event_tag_name}: {hebrew_date_formatted}", individual_id, husband_id, wife_id))
            else:
                logger.debug(f"Month abbreviation '{month_abbr}' not found in HEBREW_MONTHS_MAP.")
    return gregorian_year


def process_gedcom_file(file_path, output_csv_file):
    """
    Orchestrates the parsing of a GEDCOM file to extract Hebrew date events.

    This function performs a full scan of the GEDCOM file:
    1.  It first iterates through all records to build a map of individual IDs to names.
    2.  It then re-iterates to process events for both individuals and families.
    3.  Finally, it sorts the collected dates and writes the relevant information
        to a CSV file.

    Args:
        file_path (str): The path to the cleaned GEDCOM file.
        output_csv_file (str): The path to write the output CSV file.

    Returns:
        tuple: A tuple containing:
            - list: A list of lists, where each inner list represents a row in the CSV
                    (date, name, event type).
            - dict: A dictionary containing details for each individual, such as
                    birth and death years.
    """
    gedcom_parser = Parser()
    try:
        gedcom_parser.parse_file(file_path)
    except Exception as e:
        logger.error(f"Error parsing GEDCOM file {file_path}: {e}")
        return [], {}

    root_child_elements = gedcom_parser.get_root_child_elements()

    dates = []
    individuals = {}
    individual_details = {}

    for element in root_child_elements:
        if element.get_tag() == "INDI":
            individual_id = element.get_pointer()
            name = get_name_from_individual(element)
            individuals[individual_id] = name
            individual_details[name] = {"birth_year": None, "death_year": None}

    for element in root_child_elements:
        if element.get_tag() == "INDI":
            name = individuals.get(element.get_pointer(), "Unknown Individual")
            process_individual_events(element, name, dates, individual_details)
        elif element.get_tag() == "FAM":
            process_family_events(element, individuals, dates)

    dates.sort(key=lambda x: (x[0], x[1]))

    csv_data_rows = []
    for _, _, original_date_str_parsed, output_str, individual_id, husband_id, wife_id in dates:
        try:
            name, event_description = output_str.split(" - ", 1)
            event_type = event_description.split(":")[0].strip()

            # Determine the ID to be written to the CSV
            id_to_write = individual_id if individual_id else (husband_id if husband_id else (wife_id if wife_id else ""))

            # For marriage events, you might want to store both IDs
            if event_type == HEBREW_EVENT_NAMES.get("MARR") and husband_id and wife_id:
                id_to_write = f"{husband_id},{wife_id}"

            csv_data_rows.append([original_date_str_parsed, name, event_type, id_to_write])
        except ValueError:
            logger.warning(f"Could not parse output string for CSV: {output_str}")
            csv_data_rows.append([original_date_str_parsed, "Error in processing", "Error", ""])

    with open(output_csv_file, 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(["Date", "Name", "Event", "ID"])
        csv_writer.writerows(csv_data_rows)
    
    logger.info(f"Data successfully written to {output_csv_file}")
    logger.debug(f"Dates list before returning: {dates}")
    return csv_data_rows, individual_details

def convert_keys_to_strings(some_dict):
    """
    Converts the keys of a dictionary to strings.

    Args:
        some_dict (dict): The dictionary to process.

    Returns:
        dict: A new dictionary with all keys converted to strings.
    """
    return {str(k): v for k, v in some_dict.items()}
