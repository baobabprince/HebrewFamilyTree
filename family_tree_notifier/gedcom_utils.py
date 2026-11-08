import re
import csv
import logging
from gedcom.parser import Parser
from gedcom.element.element import Element
from .constants import HEBREW_MONTHS_MAP, HEBREW_MONTH_NAMES_FULL, HEBREW_DAY_TO_NUM
from .hebcal_api import get_gregorian_date_from_hebrew_api
from .localization import get_translation

# Configure logging for gedcom_utils
logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)


def get_hebrew_day_string(day):
    hebrew_numerals = {
        1: "א", 2: "ב", 3: "ג", 4: "ד", 5: "ה", 6: "ו", 7: "ז", 8: "ח", 9: "ט", 10: "י",
        11: "יא", 12: "יב", 13: "יג", 14: "יד", 15: "טו", 16: "טז", 17: "יז", 18: "יח", 19: "יט",
        20: "כ", 21: "כא", 22: "כב", 23: "כג", 24: "כד", 25: "כה", 26: "כו", 27: "כז", 28: "כח", 29: "כט", 30: "ל"
    }
    return hebrew_numerals.get(day, str(day))

def fix_gedcom_format(input_file, output_file):
    try:
        with open(input_file, "r", encoding="utf-8-sig", errors="replace") as file:
            lines = file.readlines()
    except Exception as e:
        logger.error(f"Error reading input file {input_file}: {e}")
        return

    fixed_lines = []
    GEDCOM_LINE_REGEX = re.compile(r'^(\d+)\s+(?:(@\S+@)\s+)?(\S+)(?:\s+(.*))?$')

    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = GEDCOM_LINE_REGEX.match(line)
        if match:
            level, xref_id, tag, value = match.groups()
            parts = [level]
            if xref_id:
                parts.append(xref_id)
            parts.append(tag)
            if value:
                parts.append(" ".join(value.split()))
            fixed_lines.append(" ".join(parts))
        else:
            logger.warning(f"Dropping non-GEDCOM-compliant line: {line}")

    try:
        with open(output_file, "w", encoding="utf-8") as file:
            for line_to_write in fixed_lines:
                file.write(line_to_write + "\n")
        logger.info(f"Successfully fixed and saved GEDCOM to {output_file}")
    except Exception as e:
        logger.error(f"Error writing output file {output_file}: {e}")


def _extract_surname(name_element):
    for child in name_element.get_child_elements():
        if child.get_tag() == "SURN":
            return child.get_value().strip()
    name_value = name_element.get_value()
    if "/" in name_value:
        try:
            return name_value.split("/")[1].strip()
        except IndexError:
            pass
    return ""

def get_name_from_individual(element, lang="he", include_maiden=True):
    names = []
    for child in element.get_child_elements():
        if child.get_tag() == "NAME":
            name_val = child.get_value().replace("/", "").strip()
            surname = _extract_surname(child)
            is_maiden = False
            for grandchild in child.get_child_elements():
                if grandchild.get_tag() == "TYPE" and grandchild.get_value().lower() in ["birth", "maiden"]:
                    is_maiden = True
                    break
            names.append({"name": name_val, "surname": surname, "is_maiden": is_maiden})
    if not names:
        return "Unknown Name"
    primary = next((n for n in names if not n["is_maiden"]), names[0])
    if not include_maiden:
        return primary["name"]
    gender = element.get_gender()
    if gender and gender.upper() == "F":
        maiden = next((n for n in names if n["is_maiden"]), None)
        if maiden and maiden["surname"] and maiden["surname"] != primary["surname"]:
            nee_label = get_translation(lang, "nee")
            return f"{primary['name']} {nee_label} {maiden['surname']}"
    return primary["name"]

def get_all_individuals_names(root_elements, lang="he"):
    indis = {}
    for elem in root_elements:
        if elem.get_tag() == "INDI":
            pid = elem.get_pointer()
            gender = elem.get_gender()
            names = []
            for child in elem.get_child_elements():
                if child.get_tag() == "NAME":
                    name_val = child.get_value().replace("/", "").strip()
                    surname = _extract_surname(child)
                    is_maiden = False
                    for grandchild in child.get_child_elements():
                        if grandchild.get_tag() == "TYPE" and grandchild.get_value().lower() in ["birth", "maiden"]:
                            is_maiden = True
                            break
                    full_val = child.get_value()
                    given = full_val.split("/")[0].strip() if "/" in full_val else full_val.strip()
                    names.append({"full": name_val, "given": given, "surname": surname, "is_maiden": is_maiden})
            if not names:
                names = [{"full": "Unknown Name", "given": "Unknown Name", "surname": "", "is_maiden": False}]
            primary = next((n for n in names if not n["is_maiden"]), names[0])
            maiden_tag = next((n for n in names if n["is_maiden"]), None)
            indis[pid] = {
                "given": primary["given"],
                "primary_surname": primary["surname"],
                "maiden_tag_surname": maiden_tag["surname"] if maiden_tag else None,
                "gender": gender,
                "father_surname": None,
                "husband_surnames": []
            }
    for elem in root_elements:
        if elem.get_tag() == "FAM":
            husb_id = wife_id = None
            children = []
            for child in elem.get_child_elements():
                tag = child.get_tag()
                val = child.get_value()
                if tag == "HUSB": husb_id = val
                elif tag == "WIFE": wife_id = val
                elif tag == "CHIL": children.append(val)
            husb_surname = indis.get(husb_id, {}).get("primary_surname") if husb_id else None
            if wife_id and husb_surname and wife_id in indis:
                if husb_surname not in indis[wife_id]["husband_surnames"]:
                    indis[wife_id]["husband_surnames"].append(husb_surname)
            if husb_surname:
                for child_id in children:
                    if child_id in indis:
                        indis[child_id]["father_surname"] = husb_surname
    results = {}
    nee_label = get_translation(lang, "nee")
    for pid, data in indis.items():
        given = data["given"]
        primary_surn = data["primary_surname"]
        if data["gender"] == "F":
            maiden_surn = data["maiden_tag_surname"] or data["father_surname"]
            if primary_surn and primary_surn != maiden_surn:
                married_surn = primary_surn
            elif data["husband_surnames"]:
                married_surn = data["husband_surnames"][0]
            else:
                married_surn = primary_surn
            if not maiden_surn and primary_surn and primary_surn != married_surn:
                maiden_surn = primary_surn
            if married_surn and maiden_surn and married_surn != maiden_surn:
                display_name = f"{given} {married_surn} {nee_label} {maiden_surn}"
                short_name = f"{given} {married_surn}"
            elif married_surn:
                display_name = short_name = f"{given} {married_surn}"
            elif maiden_surn:
                display_name = short_name = f"{given} {maiden_surn}"
            else:
                display_name = short_name = given
        else:
            surn = primary_surn or data["father_surname"]
            name = f"{given} {surn}".strip() if surn else given
            display_name = short_name = name
        results[pid] = {"display": display_name, "short": short_name}
    return results

def process_individual_events(element, name, dates, individual_details):
    """Only birthdays and yahrzeits generate notifications."""
    individual_id = element.get_pointer()
    individual_event_tags = ["BIRT", "DEAT"]
    for child in element.get_child_elements():
        if child.get_tag() in individual_event_tags:
            event_type_str = child.get_tag()
            gregorian_year = process_event(child, name, dates, event_type=event_type_str, individual_id=individual_id)
            if gregorian_year:
                if child.get_tag() == "BIRT":
                    individual_details[name]["birth_year"] = gregorian_year
                elif child.get_tag() == "DEAT":
                    individual_details[name]["death_year"] = gregorian_year

def process_family_events(element, individuals, dates, family_details):
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
            gregorian_year = process_event(child, couple_name, dates, event_type=event_type_str, husband_id=husband_id, wife_id=wife_id)
            if couple_name not in family_details:
                family_details[couple_name] = {}
            if child.get_tag() in ["DIV", "ANUL"]:
                family_details[couple_name]['is_divorced'] = True
            if gregorian_year:
                if child.get_tag() == "MARR":
                    family_details[couple_name]['marriage_year'] = gregorian_year
                elif child.get_tag() == "DIV":
                    family_details[couple_name]['divorce_year'] = gregorian_year

def process_event(event_element, name, dates, event_type=None, individual_id=None, husband_id=None, wife_id=None):
    gregorian_year = None
    for child in event_element.get_child_elements():
        if child.get_tag() == "DATE":
            date_str = child.get_value()
            paren_match = re.search(r'\((.*?)\)', date_str)
            if paren_match:
                content_in_paren = paren_match.group(1)
                year_in_paren_match = re.search(r'(\d{4})', content_in_paren)
                if year_in_paren_match:
                    gregorian_year = int(year_in_paren_match.group(1))
            if not date_str:
                continue
            if not date_str.startswith("@#DHEBREW@"):
                if gregorian_year is None:
                    simple_greg_match = re.search(r'(\d{4})', date_str)
                    if simple_greg_match:
                        gregorian_year = int(simple_greg_match.group(1))
                continue
            parsing_date_str = date_str[10:].strip()
            if not parsing_date_str:
                continue
            temp_date_parts = list(parsing_date_str.split())
            day = 1
            month_abbr = None
            month_found_index = -1
            hebrew_year = None
            hebrew_year_match = re.search(r'\s(\d{4})$', parsing_date_str)
            if hebrew_year_match:
                hebrew_year = int(hebrew_year_match.group(1))
            for i in range(len(temp_date_parts) - 1):
                compound_month_candidate = f"{temp_date_parts[i].upper()} {temp_date_parts[i+1].upper()}"
                if compound_month_candidate in HEBREW_MONTHS_MAP:
                    month_abbr = compound_month_candidate
                    month_found_index = i
                    break
            if month_abbr is None:
                for i in range(len(temp_date_parts)):
                    single_month_candidate = temp_date_parts[i].upper()
                    if single_month_candidate in HEBREW_MONTHS_MAP:
                        month_abbr = single_month_candidate
                        month_found_index = i
                        break
            if month_abbr and month_found_index > 0:
                day_str = temp_date_parts[month_found_index - 1].replace('"', '').strip()
                try:
                    day = int(day_str)
                except ValueError:
                    pass
            if gregorian_year is None and hebrew_year and month_abbr and month_abbr in HEBREW_MONTHS_MAP:
                month_num = HEBREW_MONTHS_MAP[month_abbr]
                context_for_log = f"{name} - {event_type}" if event_type else name
                gregorian_year = get_gregorian_date_from_hebrew_api(hebrew_year, month_num, day, context=context_for_log)
            if month_abbr and month_abbr in HEBREW_MONTHS_MAP:
                month_num = HEBREW_MONTHS_MAP[month_abbr]
                event_tag_name = event_type or event_element.get_tag()
                hebrew_month_name = HEBREW_MONTH_NAMES_FULL.get(month_num, "")
                hebrew_date_formatted = f"{get_hebrew_day_string(day)} {hebrew_month_name}"
                dates.append((month_num, day, hebrew_date_formatted, f"{name} - {event_tag_name}: {hebrew_date_formatted}", individual_id, husband_id, wife_id))
            else:
                logger.debug(f"Month abbreviation '{month_abbr}' not found in HEBREW_MONTHS_MAP.")
    return gregorian_year


def process_gedcom_file(file_path, output_csv_file, lang="he"):
    gedcom_parser = Parser()
    try:
        gedcom_parser.parse_file(file_path)
    except Exception as e:
        logger.error(f"Error parsing GEDCOM file {file_path}: {e}")
        return [], {}, {}
    root_child_elements = gedcom_parser.get_root_child_elements()
    id2names = get_all_individuals_names(root_child_elements, lang=lang)
    dates = []
    individuals = {}
    individual_details = {}
    family_details = {}
    for element in root_child_elements:
        if element.get_tag() == "INDI":
            individual_id = element.get_pointer()
            name_info = id2names.get(individual_id, {"display": "Unknown Name", "short": "Unknown Name"})
            name = name_info["display"]
            individuals[individual_id] = name
            gender = element.get_gender()
            individual_details[name] = {"birth_year": None, "death_year": None, "gender": gender}
    for element in root_child_elements:
        if element.get_tag() == "INDI":
            name = individuals.get(element.get_pointer(), "Unknown Individual")
            process_individual_events(element, name, dates, individual_details)
        elif element.get_tag() == "FAM":
            process_family_events(element, individuals, dates, family_details)
    for element in root_child_elements:
        if element.get_tag() == "FAM":
            husband_id, wife_id = None, None
            for child in element.get_child_elements():
                if child.get_tag() == 'HUSB':
                    husband_id = child.get_value()
                elif child.get_tag() == 'WIFE':
                    wife_id = child.get_value()
            husband_name = individuals.get(husband_id)
            wife_name = individuals.get(wife_id)
            if husband_name and wife_name:
                couple_name = f"{husband_name} & {wife_name}"
                husband_death_year = individual_details.get(husband_name, {}).get("death_year")
                wife_death_year = individual_details.get(wife_name, {}).get("death_year")
                if couple_name not in family_details:
                    family_details[couple_name] = {}
                family_details[couple_name]["husband_death_year"] = husband_death_year
                family_details[couple_name]["wife_death_year"] = wife_death_year
    dates.sort(key=lambda x: (x[0], x[1]))
    csv_data_rows = []
    for _, _, original_date_str_parsed, output_str, individual_id, husband_id, wife_id in dates:
        try:
            name, event_description = output_str.split(" - ", 1)
            event_type = event_description.split(":")[0].strip()
            id_to_write = individual_id if individual_id else (husband_id if husband_id else (wife_id if wife_id else ""))
            if event_type == "MARR" and husband_id and wife_id:
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
    return csv_data_rows, individual_details, family_details

def convert_keys_to_strings(some_dict):
    return {str(k): v for k, v in some_dict.items()}
