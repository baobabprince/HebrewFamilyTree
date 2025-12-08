from datetime import timedelta
import json
import requests
import logging
from constants import HEBCAL_API_BASE_URL, HEBCAL_FULL_MONTH_NAMES_TO_NUM, HEBREW_DAY_TO_NUM, HEBREW_MONTH_NAMES_TO_NUM

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
        response = requests.get(HEBCAL_API_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        
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

def get_hebrew_year_from_api(gregorian_date_obj):
    """
    Fetches the Hebrew year for a given Gregorian date using Hebcal API.
    Returns hebrew_year or None on failure.
    """
    params = {
        "cfg": "json",
        "gy": gregorian_date_obj.year,
        "gm": gregorian_date_obj.month,
        "gd": gregorian_date_obj.day,
        "tzid": "Asia/Jerusalem"
    }

    try:
        response = requests.get(HEBCAL_API_BASE_URL, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()

        if "hy" in data:
            return int(data["hy"])
        else:
            logging.error(f"API response missing 'hy' key for {gregorian_date_obj}: {data}")
            return None

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching Hebrew year from Hebcal API for {gregorian_date_obj}: {e}")
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



def find_relevant_hebrew_dates(processed_gedcom_rows, target_hebrew_dates_map):
    """
    Filters GEDCOM processed dates to find those matching the target Hebrew date range.
    Returns a list of tuples: (gregorian_date, original_date_str, name, event_type)
    """
    relevant_dates = []
    logging.debug(f"Target Hebrew dates map (keys): {target_hebrew_dates_map.keys()}")
    for original_date_str_parsed, name, event_type in processed_gedcom_rows:
        logging.debug(f"Processing GEDCOM date: {original_date_str_parsed}")
        parts = original_date_str_parsed.split()
        if len(parts) < 2:
            logging.debug(f"Skipping invalid date format: {original_date_str_parsed}")
            continue

        day_str = parts[0]
        month_str = parts[1]

        day = HEBREW_DAY_TO_NUM.get(day_str)
        if day is None:
            try:
                day = int(day_str)
            except ValueError:
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
            relevant_dates.append((gregorian_date, original_date_str_parsed, name, event_type))
        else:
            logging.debug(f"Hebrew date {hebrew_date_tuple} not found in target map. Target map keys: {target_hebrew_dates_map.keys()}")
    return relevant_dates

def get_parasha_for_week(start_date):
    """
    Finds the Parashat Hashavua for the upcoming week.
    """
    days_ahead = 5 - start_date.weekday()  # 5 is Saturday
    if days_ahead <= 0:
        days_ahead += 7
    saturday_date = start_date + timedelta(days=days_ahead)

    logging.debug(f"Calculated upcoming Saturday as: {saturday_date}")

    params = {
        "cfg": "json",
        "v": "1",
        "gy": saturday_date.year,
        "gm": saturday_date.month,
        "gd": saturday_date.day,
        "g2h": "1",
        "hl": "he"  # Request Hebrew output
    }

    try:
        response = requests.get(HEBCAL_API_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        logging.debug(f"Hebcal API response for Parasha: {json.dumps(data, indent=2, ensure_ascii=False)}")

        if "items" in data:
            for item in data["items"]:
                if item.get("category") == "parashat":
                    logging.debug(f"Found Parasha: {item.get('hebrew')}")
                    return item.get("hebrew", "")
        
        logging.debug("No Parasha found in Hebcal API response items.")
        return ""

    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        logging.error(f"Error fetching Parasha from Hebcal API: {e}")
        return ""