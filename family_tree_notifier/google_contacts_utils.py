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

def _parse_single_line_for_date(line_clean):
    """
    Helper to extract (month_num, day, formatted_hebrew_date, event_type, subject_name) from a line.
    """
    if not line_clean:
        return None

    line_lower = line_clean.lower()
    if any(kw in line_lower or kw in line_clean for kw in ["יארצייט", "פטירה", "נפטר", "נפטרה", "yahrzeit", "death", "died"]):
        event_type = "DEAT"
    elif any(kw in line_lower or kw in line_clean for kw in ["נישואין", "חתונה", "anniversary", "wedding", "marriage"]):
        event_type = "MARR"
    else:
        event_type = "BIRT"

    # Separate subject name if present before/after a separator like '-' or ':' or '–'
    subject_name = None
    date_part = line_clean

    for sep in [' - ', ' – ', ' : ', ':', '-']:
        if sep in line_clean:
            parts = line_clean.split(sep, 1)
            # Determine which part has the date
            # We will test both parts, but typically first part is name, second is date
            date_part = parts[1].strip()
            subject_name = parts[0].strip()
            break

    words = date_part.split()
    month_num = None
    month_idx = -1

    # Check multi-word month names first (e.g. מנחם אב, אדר א, ADAR I)
    for i in range(len(words) - 1):
        candidate_raw = f"{words[i]} {words[i+1]}".replace('"', '').replace("'", "")
        candidate_upper = candidate_raw.upper()
        if candidate_upper in HEBREW_MONTHS_MAP:
            month_num = HEBREW_MONTHS_MAP[candidate_upper]
            month_idx = i
            break
        elif candidate_raw in HEBREW_MONTHS_MAP:
            month_num = HEBREW_MONTHS_MAP[candidate_raw]
            month_idx = i
            break

    # Check single-word month names
    if month_num is None:
        for i in range(len(words)):
            clean_word = words[i].replace('"', '').replace("'", "")
            candidate_clean = clean_word[1:] if clean_word.startswith("ב") and len(clean_word) > 2 and clean_word[1:] in HEBREW_MONTHS_MAP else clean_word
            candidate_upper = candidate_clean.upper()
            if candidate_upper in HEBREW_MONTHS_MAP:
                month_num = HEBREW_MONTHS_MAP[candidate_upper]
                month_idx = i
                break
            elif clean_word in HEBREW_MONTHS_MAP:
                month_num = HEBREW_MONTHS_MAP[clean_word]
                month_idx = i
                break

    if month_num is None:
        return None

    # Find day before month_idx
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

    return (month_num, day, formatted_hebrew_date, event_type, subject_name)

def parse_hebrew_date_and_event_type_from_note(note_text):
    """
    Parses Hebrew dates, event types, and subject names from a contact's note/comment text.

    Returns a list of tuples: (month_num, day, formatted_hebrew_date_str, event_type, subject_name)
    event_type can be 'BIRT', 'DEAT', 'MARR'.
    subject_name is optional string (e.g. child's name in contact note) or None.
    """
    if not note_text:
        return []

    results = []
    lines = [l.strip() for l in note_text.splitlines() if l.strip()]

    i = 0
    while i < len(lines):
        line = lines[i]
        parsed = _parse_single_line_for_date(line)

        if parsed:
            month_num, day, formatted_date, event_type, subject_name = parsed
            # Check if previous or next line was a standalone subject name if subject_name wasn't in line
            if not subject_name:
                if i + 1 < len(lines) and not _parse_single_line_for_date(lines[i+1]):
                    # Next line might be subject name
                    subject_name = lines[i+1]
                    i += 1
                elif i > 0 and not _parse_single_line_for_date(lines[i-1]):
                    # Previous line might have been subject name
                    subject_name = lines[i-1]

            results.append((month_num, day, formatted_date, event_type, subject_name))
        else:
            # Maybe this line is subject name and next line is date
            if i + 1 < len(lines):
                next_parsed = _parse_single_line_for_date(lines[i+1])
                if next_parsed:
                    month_num, day, formatted_date, event_type, s_name = next_parsed
                    if not s_name:
                        s_name = line
                    results.append((month_num, day, formatted_date, event_type, s_name))
                    i += 1 # skip next line since handled
        i += 1

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
                    for item in parsed_events:
                        if len(item) == 5:
                            month_num, day, formatted_date_str, event_type, subject_name = item
                        else:
                            month_num, day, formatted_date_str, event_type = item[:4]
                            subject_name = None

                        hebrew_key = (month_num, day)
                        if hebrew_key in target_hebrew_dates_map:
                            gregorian_date = target_hebrew_dates_map[hebrew_key]
                            display_name = f"{contact_name} ({subject_name})" if subject_name else contact_name
                            contact_events.append((
                                gregorian_date,
                                formatted_date_str,
                                display_name,
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
