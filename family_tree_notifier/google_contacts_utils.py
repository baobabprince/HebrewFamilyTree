import re
import os
import json
import logging
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .constants import HEBREW_MONTHS_MAP, HEBREW_MONTH_NAMES_FULL, HEBREW_DAY_TO_NUM
from .gedcom_utils import get_hebrew_day_string

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/contacts.readonly'
]

logger = logging.getLogger(__name__)

def get_people_service():
    """
    Authenticates with the Google People API and returns a service object.
    Supports token.json or service account credentials.
    """
    creds = None
    if os.path.exists('token.json'):
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        except Exception as e:
            logger.warning(f"Failed to load token.json: {e}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.warning(f"Failed to refresh credentials: {e}")
                creds = None

        if not creds:
            credentials_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS') or os.environ.get('GOOGLE_CREDENTIALS_JSON')
            if credentials_json:
                try:
                    if os.path.exists(credentials_json):
                        creds = service_account.Credentials.from_service_account_file(credentials_json, scopes=SCOPES)
                    else:
                        credentials_info = json.loads(credentials_json)
                        creds = service_account.Credentials.from_service_account_info(credentials_info, scopes=SCOPES)
                except Exception as e:
                    logger.error(f"Error loading credentials for People API: {e}")
                    return None
            else:
                logger.info("No credentials provided for Google People API.")
                return None

    try:
        service = build('people', 'v1', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Error building People API service: {e}")
        return None

def parse_hebrew_date_and_event_type_from_note(note_text):
    """
    Parses Hebrew dates and event types from a contact's note/comment text.

    Returns a list of tuples: (month_num, day, formatted_hebrew_date_str, event_type)
    event_type can be 'BIRT', 'DEAT', 'MARR'.
    Defaults to 'BIRT' if no explicit event type keyword is detected.
    """
    if not note_text:
        return []

    results = []
    lines = note_text.splitlines()

    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue

        line_lower = line_clean.lower()
        if any(kw in line_lower or kw in line_clean for kw in ["יארצייט", "פטירה", "נפטר", "נפטרה", "yahrzeit", "death", "died"]):
            event_type = "DEAT"
        elif any(kw in line_lower or kw in line_clean for kw in ["נישואין", "חתונה", "anniversary", "wedding", "marriage"]):
            event_type = "MARR"
        else:
            event_type = "BIRT"

        # Search for Hebrew month name in line
        words = line_clean.split()
        month_num = None
        month_idx = -1
        month_abbr = None

        # Check two-word month names first (e.g., ADAR I, אדר א)
        for i in range(len(words) - 1):
            candidate = f"{words[i].upper()} {words[i+1].upper()}"
            if candidate in HEBREW_MONTHS_MAP:
                month_num = HEBREW_MONTHS_MAP[candidate]
                month_idx = i
                month_abbr = candidate
                break

        # Check single-word month names or Hebrew month names
        if month_num is None:
            for i in range(len(words)):
                candidate_clean = words[i].replace('"', '').replace("'", "").replace("ב", "", 1) if words[i].startswith("ב") and len(words[i]) > 2 else words[i].replace('"', '').replace("'", "")
                candidate_upper = candidate_clean.upper()
                if candidate_upper in HEBREW_MONTHS_MAP:
                    month_num = HEBREW_MONTHS_MAP[candidate_upper]
                    month_idx = i
                    month_abbr = candidate_upper
                    break
                elif words[i].replace('"', '').replace("'", "") in HEBREW_MONTHS_MAP:
                    raw_candidate = words[i].replace('"', '').replace("'", "")
                    month_num = HEBREW_MONTHS_MAP[raw_candidate]
                    month_idx = i
                    month_abbr = raw_candidate
                    break

        if month_num is None:
            continue

        # Try to find day
        day = 1
        if month_idx > 0:
            day_candidate_str = words[month_idx - 1].replace('"', '').replace("'", "").replace(',', '').strip()
            if day_candidate_str in HEBREW_DAY_TO_NUM:
                day = HEBREW_DAY_TO_NUM[day_candidate_str]
            else:
                try:
                    day = int(day_candidate_str)
                except ValueError:
                    pass

        hebrew_month_name = HEBREW_MONTH_NAMES_FULL.get(month_num, "")
        formatted_hebrew_date = f"{get_hebrew_day_string(day)} {hebrew_month_name}"

        results.append((month_num, day, formatted_hebrew_date, event_type))

    return results

def get_upcoming_contact_events(target_hebrew_dates_map):
    """
    Fetches Google Contacts, parses Hebrew dates from notes,
    and returns events that fall within target_hebrew_dates_map.

    Returns list of tuples:
    (gregorian_date, original_date_str_parsed, contact_name, event_type, contact_id)
    """
    service = get_people_service()
    if not service:
        logger.info("Google People API service unavailable. Skipping contact sync.")
        return []

    contact_events = []

    try:
        page_token = None
        while True:
            results = service.people().connections().list(
                resourceName='people/me',
                pageSize=1000,
                personFields='names,biographies',
                pageToken=page_token
            ).execute()

            connections = results.get('connections', [])
            for person in connections:
                resource_name = person.get('resourceName', '')
                names = person.get('names', [])
                contact_name = names[0].get('displayName') if names else "Unknown Contact"

                biographies = person.get('biographies', [])
                for bio in biographies:
                    note = bio.get('value', '')
                    parsed_events = parse_hebrew_date_and_event_type_from_note(note)
                    for month_num, day, formatted_date_str, event_type in parsed_events:
                        hebrew_key = (month_num, day)
                        if hebrew_key in target_hebrew_dates_map:
                            gregorian_date = target_hebrew_dates_map[hebrew_key]
                            contact_events.append((
                                gregorian_date,
                                formatted_date_str,
                                contact_name,
                                event_type,
                                resource_name
                            ))

            page_token = results.get('nextPageToken')
            if not page_token:
                break

    except HttpError as error:
        logger.error(f"Google People API request failed: {error}")
    except Exception as e:
        logger.error(f"Unexpected error while fetching Google Contacts: {e}")

    return contact_events
