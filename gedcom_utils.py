import re
import csv
import logging
from gedcom.parser import Parser
from constants import HEBREW_MONTHS_MAP, HEBREW_EVENT_NAMES, HEBREW_MONTH_NAMES_FULL, HEBREW_DAY_TO_NUM, HEBREW_MONTH_NAMES_TO_NUM

def get_hebrew_day_string(day):
    """Converts a day number to its Hebrew letter representation."""
    hebrew_numerals = {
        1: "א", 2: "ב", 3: "ג", 4: "ד", 5: "ה", 6: "ו", 7: "ז", 8: "ח", 9: "ט", 10: "י",
        11: "יא", 12: "יב", 13: "יג", 14: "יד", 15: "טו", 16: "טז", 17: "יז", 18: "יח", 19: "יט",
        20: "כ", 21: "כא", 22: "כב", 23: "כג", 24: "כד", 25: "כה", 26: "כו", 27: "כז", 28: "כח", 29: "כט", 30: "ל"
    }
    return hebrew_numerals.get(day, str(day))

def fix_gedcom_format(input_file, output_file):
    """Fixes the format of a GEDCOM file."""
    with open(input_file, "r", encoding="utf-8-sig", errors="replace") as file:
        lines = file.readlines()

    fixed_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue

        match = re.match(r'^(\d+)\s+(@?\S+@?)(?:\s+(.*))?$', line)
        if match:
            level, tag_or_xref, value = match.groups()
            if value:
                fixed_line = f"{level} {tag_or_xref} {value}"
            else:
                fixed_line = f"{level} {tag_or_xref}"
        else:
            parts = line.split(None, 2)
            if len(parts) >= 1 and parts[0].isdigit():
                level = parts[0]
                if len(parts) == 3:
                    tag_or_xref = parts[1]
                    val = parts[2]
                    fixed_line = f"{level} {tag_or_xref} {val}"
                elif len(parts) == 2:
                    tag_or_xref = parts[1]
                    fixed_line = f"{level} {tag_or_xref}"
                else:
                    fixed_line = line
            else:
                fixed_line = line
        
        fixed_lines.append(fixed_line)

    with open(output_file, "w", encoding="utf-8") as file:
        for line_to_write in fixed_lines:
            file.write(line_to_write + "\n")

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
            event_type_str = child.get_tag()
            if child.get_tag() == "MARR":
                event_type_str = HEBREW_EVENT_NAMES.get(child.get_tag(), child.get_tag())
            process_event(child, couple_name, dates, event_type=event_type_str)

def process_event(event_element, name, dates, event_type=None):
    """Extracts and processes date from an event element."""
    for child in event_element.get_child_elements():
        if child.get_tag() == "DATE":
            date_str = child.get_value()

            logging.debug(f"date_str: {date_str}")
            if not date_str:
                logging.debug("date_str is empty.")
                continue

            if date_str.startswith("@#DHEBREW@"):
                parsing_date_str = date_str[10:].strip()
                logging.debug(f"parsing_date_str (Hebrew): {parsing_date_str}")
            else:
                # If it's not a Hebrew date, we can skip it for now, or process it if no Hebrew date is found.
                # For this fix, we prioritize Hebrew dates.
                continue
            
            if not parsing_date_str:
                logging.debug("parsing_date_str is empty.")
                continue

            temp_date_parts = list(parsing_date_str.split())
            logging.debug(f"temp_date_parts: {temp_date_parts}")
            
            if not temp_date_parts:
                logging.debug("temp_date_parts is empty.")
                continue
            
            if temp_date_parts[0].upper() in ['BET', 'ABT', 'EST', 'CAL', 'FROM', 'TO', 'INT', 'AFT', 'BEF']:
                logging.debug(f"Skipping date due to qualifier: {temp_date_parts[0]}")
                temp_date_parts = temp_date_parts[1:]
                if not temp_date_parts:
                    logging.debug("temp_date_parts empty after removing qualifier.")
                    continue
            
            if 'AND' in [dp.upper() for dp in temp_date_parts]:
                logging.debug(f"Skipping date due to 'AND' keyword: {temp_date_parts}")
                try:
                    and_index = [dp.upper() for dp in temp_date_parts].index('AND')
                    temp_date_parts = temp_date_parts[:and_index]
                    if not temp_date_parts:
                        logging.debug("temp_date_parts empty after removing AND.")
                        continue
                except ValueError:
                    pass

            day = 1
            month_name = None

            if len(temp_date_parts) >= 2:
                day_str = temp_date_parts[0].replace('"', '').strip()
                logging.debug(f"day_str: {day_str}")
                day_candidate = HEBREW_DAY_TO_NUM.get(day_str)
                logging.debug(f"day_candidate from HEBREW_DAY_TO_NUM: {day_candidate}")
                if day_candidate is None:
                    try:
                        day_candidate = int(day_str)
                        logging.debug(f"day_candidate parsed as int: {day_candidate}")
                    except ValueError:
                        logging.debug(f"Could not parse day from: {day_str}")
                        day_candidate = 1 # Default to 1 if not found

                month_abbr_candidate = temp_date_parts[1].upper()
                if month_abbr_candidate in HEBREW_MONTHS_MAP:
                    day = day_candidate
                    month_abbr = month_abbr_candidate
            elif len(temp_date_parts) == 1:
                month_abbr_candidate = temp_date_parts[0].upper()
                if month_abbr_candidate in HEBREW_MONTHS_MAP:
                    month_abbr = month_abbr_candidate
            
            logging.debug(f"Final month_abbr: {month_abbr}")
            if month_abbr and month_abbr in HEBREW_MONTHS_MAP:
                month_num = HEBREW_MONTHS_MAP[month_abbr]
                event_tag_name = event_type or event_element.get_tag()
                
                hebrew_month_name = HEBREW_MONTH_NAMES_FULL.get(month_num, "")
                hebrew_date_formatted = f"{get_hebrew_day_string(day)} {hebrew_month_name}"

                logging.debug(f"Appending date: month_num={month_num}, day={day}, hebrew_date_formatted='{hebrew_date_formatted}', name='{name}', event_tag_name='{event_tag_name}'")
                dates.append((month_num, day, hebrew_date_formatted, f"{name} - {event_tag_name}: {hebrew_date_formatted}"))
            else:
                logging.debug(f"Month abbreviation '{month_abbr}' not found in HEBREW_MONTHS_MAP.")
try:
    from gedcom.parser import Parser
except ImportError:
    logging.warning("gedcom.parser.Parser not found. Using a dummy class. "
          "Ensure your GEDCOM parsing library is correctly set up.")
    class Parser:
        def parse_file(self, file_path):
            logging.info(f"Dummy Parser: Parsing file {file_path}")
            pass
        def get_root_child_elements(self):
            return []

def process_gedcom_file(file_path, output_csv_file):
    """
    Processes a GEDCOM file, extracts information, and writes to dates.csv.
    """
    gedcom_parser = Parser()
    try:
        gedcom_parser.parse_file(file_path)
    except Exception as e:
        logging.error(f"Error parsing GEDCOM file {file_path}: {e}")
        return []

    root_child_elements = gedcom_parser.get_root_child_elements()

    dates = []
    individuals = {}

    for element in root_child_elements:
        if element.get_tag() == "INDI":
            individual_id = element.get_pointer()
            name = get_name_from_individual(element)
            individuals[individual_id] = name

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
            logging.warning(f"Could not parse output string for CSV: {output_str}")
            csv_data_rows.append([original_date_str_parsed, "Error in processing", "Error"])

    with open(output_csv_file, 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(["Date", "Name", "Event"])
        csv_writer.writerows(csv_data_rows)
    
    logging.info(f"Data successfully written to {output_csv_file}")
    logging.debug(f"Dates list before returning: {dates}")
    return csv_data_rows