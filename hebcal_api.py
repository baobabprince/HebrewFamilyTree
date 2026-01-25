from datetime import timedelta
import json
import requests
import logging
from constants import HEBCAL_API_BASE_URL, HEBCAL_FULL_MONTH_NAMES_TO_NUM, HEBREW_DAY_TO_NUM, HEBREW_MONTH_NAMES_TO_NUM

# Mapping from Hebrew month number (as used internally) to English name (for Hebcal API)
HEBREW_MONTH_NUM_TO_ENGLISH_NAME = {
    1: "Tishrei", 2: "Cheshvan", 3: "Kislev", 4: "Tevet", 5: "Shevat",
    6: "Adar", 61: "Adar I", 62: "Adar II",
    7: "Nisan", 8: "Iyyar", 9: "Sivan", 10: "Tamuz", 11: "Av", 12: "Elul",
}

def get_hebrew_date_from_api(gregorian_date_obj):
    """
    Fetches the Hebrew date for a given Gregorian date using Hebcal API.
    Returns (hebrew_month_num, hebrew_day) or None on failure.
    """
    params = {
        "cfg": "json",
        "gy": gregorian_date_obj.year,
        "gm": gregorian_date_obj.month,
        "gd": gregorian_date_obj.day,
        "tzid": "Asia/Jerusalem"
    }
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(HEBCAL_API_BASE_URL, params=params, timeout=10, allow_redirects=False, headers=headers)
        
        if response.is_redirect:
            logging.error(f"Hebcal API converter redirected for Gregorian date {gregorian_date_obj}. This usually means the date is invalid or not found.")
            return None

        response.raise_for_status() # This will raise an exception for 4xx or 5xx errors
        
        data = response.json()
        
        logging.debug(f"API response for {gregorian_date_obj}:\n{json.dumps(data, indent=2)}")
        
        if "hm" in data and "hd" in data:
            hebrew_month_name = data["hm"]
            hebrew_day = int(data["hd"])

            hebrew_month_num = HEBCAL_FULL_MONTH_NAMES_TO_NUM.get(hebrew_month_name)
            
            if hebrew_month_num is not None:
                logging.debug(f"Converted Hebrew month name '{hebrew_month_name}' to number {hebrew_month_num}")
                return (hebrew_month_num, hebrew_day)
            else:
                logging.error(f"Could not map Hebrew month name '{hebrew_month_name}' to a number.")
                return None
        else:
            logging.error(f"API response missing 'hm' or 'hd' keys for {gregorian_date_obj}: {data}")
            return None
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching Hebrew date from Hebcal API for {gregorian_date_obj}: {e}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from Hebcal API for {gregorian_date_obj}. Response: {response.text[:200]}...")
        return None

def get_hebrew_date_range_api(start_gregorian_date, num_days):
    """
    Generates a mapping of (Hebrew month number, Hebrew day) tuples to Gregorian date objects
    for a given date range using the Hebcal API.
    """
    hebrew_dates_map = {}
    logging.info(f"Fetching Hebrew dates for {num_days} days starting from {start_gregorian_date} using Hebcal API...")
    for i in range(num_days):
        current_gregorian = start_gregorian_date + timedelta(days=i)
        hebrew_date_tuple = get_hebrew_date_from_api(current_gregorian)
        if hebrew_date_tuple:
            hebrew_dates_map[hebrew_date_tuple] = current_gregorian
        else:
            logging.warning(f"Could not get Hebrew date for {current_gregorian}, skipping this day.")
    logging.debug(f"Populated hebrew_dates_map: {hebrew_dates_map}")
    return hebrew_dates_map



def find_relevant_hebrew_dates(processed_gedcom_rows, target_hebrew_dates_map, has_id_column=False):
    """
    Filters GEDCOM processed dates to find those matching the target Hebrew date range.
    Returns a list of tuples based on `has_id_column`.
    """
    relevant_dates = []
    logging.debug(f"Target Hebrew dates map (keys): {target_hebrew_dates_map.keys()}")

    for row in processed_gedcom_rows:
        if has_id_column:
            if len(row) != 4:
                logging.warning(f"Skipping row with unexpected number of elements: {row}")
                continue
            original_date_str_parsed, name, event_type, gedcom_id = row
        else:
            if len(row) != 3:
                logging.warning(f"Skipping row with unexpected number of elements: {row}")
                continue
            original_date_str_parsed, name, event_type = row
            gedcom_id = None

        logging.debug(f"Processing GEDCOM date: {original_date_str_parsed}")
        parts = original_date_str_parsed.split()
        if len(parts) < 2:
            logging.debug(f"Skipping invalid date format: {original_date_str_parsed}")
            continue

        day_str = parts[0]
        month_str = " ".join(parts[1:])

        day = HEBREW_DAY_TO_NUM.get(day_str)
        if day is None:
            try:
                day = int(day_str)
            except (ValueError, TypeError):
                logging.debug(f"Could not parse day from: {day_str}")
                continue

        month_num = HEBREW_MONTH_NAMES_TO_NUM.get(month_str)
        if month_num is None:
            logging.debug(f"Could not map month from: {month_str}")
            continue

        hebrew_date_tuple = (month_num, day)
        logging.debug(f"Extracted Hebrew date tuple from GEDCOM: {hebrew_date_tuple}")

        if hebrew_date_tuple in target_hebrew_dates_map:
            gregorian_date = target_hebrew_dates_map[hebrew_date_tuple]
            logging.info(f"Found relevant date: {original_date_str_parsed} ({name} - {event_type}) matches {gregorian_date}")

            if has_id_column:
                relevant_dates.append((gregorian_date, original_date_str_parsed, name, event_type, gedcom_id))
            else:
                relevant_dates.append((gregorian_date, original_date_str_parsed, name, event_type))
        else:
            logging.debug(f"Hebrew date {hebrew_date_tuple} not found in target map.")

    return relevant_dates

def get_parasha_for_week(start_date, lang="he"):
    """
    Finds the Parashat Hashavua for the upcoming week using the /hebcal endpoint.
    """
    end_date = start_date + timedelta(days=7)
    logging.debug(f"Searching for Parasha between {start_date} and {end_date}")

    url = "https://www.hebcal.com/hebcal"
    params = {
        "v": "1",
        "cfg": "json",
        "start": start_date.strftime('%Y-%m-%d'),
        "end": end_date.strftime('%Y-%m-%d'),
        "lg": "h" if lang == "he" else "s",
        "s": "on",      # include weekly parasha
        "leyning": "off"
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        logging.debug(f"Hebcal API response for Parasha: {json.dumps(data, indent=2, ensure_ascii=False)}")

        for item in data.get("items", []):
            if item.get("category") == "parashat":
                if lang == "he":
                    return item.get("hebrew", "")
                else:
                    return item.get("title", "")
        
        logging.warning("No Parasha found in Hebcal API response for the upcoming week.")
        return ""

    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        logging.error(f"Error fetching Parasha from Hebcal API: {e}")
        return ""
        
def get_gregorian_date_from_hebrew_api(hebrew_year, hebrew_month_num, hebrew_day, context=""):
    """
    Converts a Hebrew date to a Gregorian year using the Hebcal API.

    Args:
        hebrew_year (int): The Hebrew year.
        hebrew_month_num (int): The Hebrew month number.
        hebrew_day (int): The Hebrew day.
        context (str, optional): Additional context for logging, such as the
                                 name and event. Defaults to "".

    Returns:
        int or None: The Gregorian year, or None on failure.
    """
    hebrew_month_name_english = HEBREW_MONTH_NUM_TO_ENGLISH_NAME.get(hebrew_month_num)
    if not hebrew_month_name_english:
        logging.error(f"Invalid Hebrew month number: {hebrew_month_num}")
        return None

    params = {
        "cfg": "json",
        "hy": hebrew_year,
        "hm": hebrew_month_name_english,
        "hd": hebrew_day,
    }
    logging.debug(f"Sending parameters to Hebcal API converter: {params}")

    try:
        response = requests.get(HEBCAL_API_BASE_URL, params=params, timeout=10)
        data = response.json()

        # Verify that the Hebrew date in the response matches the requested Hebrew date
        # If the API redirects to a default (like current date), the hebrew year/month will not match
        if "hy" not in data or "hm" not in data or data["hy"] != hebrew_year or data["hm"] != hebrew_month_name_english:
            logging.warning(f"Hebcal API response date mismatch for {context}. Requested: {hebrew_day} {hebrew_month_name_english} {hebrew_year}, Got: {data.get('hd')} {data.get('hm')} {data.get('hy')}. Falling back to Hebrew year.")
            return hebrew_year
        logging.debug(f"API converter response for H: {hebrew_day} {hebrew_month_name_english} {hebrew_year}:\n{json.dumps(data, indent=2)}")

        if "gy" in data:
            return int(data["gy"])
        else:
            logging.error(f"API converter response missing 'gy' key for Hebrew date {hebrew_day} {hebrew_month_name_english} {hebrew_year}: {data}")
            return None

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching Gregorian date from Hebcal API for {hebrew_day} {hebrew_month_name_english} {hebrew_year}: {e}")
        return None
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from Hebcal API for Hebrew date. Response: {response.text[:200]}...")
        return None