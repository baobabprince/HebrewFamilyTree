import re
import os
import json
import logging
from datetime import date
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

# Gregorian month names (English + common Hebrew labels in notes)
GREGORIAN_MONTHS = {
    'january': 1, 'jan': 1, 'ינואר': 1, 'ינו׳': 1,
    'february': 2, 'feb': 2, 'פברואר': 2, 'פבר׳': 2,
    'march': 3, 'mar': 3, 'מרץ': 3, 'מרס': 3,
    'april': 4, 'apr': 4, 'אפריל': 4, 'אפר׳': 4,
    'may': 5, 'מאי': 5,
    'june': 6, 'jun': 6, 'יוני': 6,
    'july': 7, 'jul': 7, 'יולי': 7,
    'august': 8, 'aug': 8, 'אוגוסט': 8, 'אוג׳': 8,
    'september': 9, 'sep': 9, 'sept': 9, 'ספטמבר': 9, 'ספט׳': 9,
    'october': 10, 'oct': 10, 'אוקטובר': 10, 'אוק׳': 10,
    'november': 11, 'nov': 11, 'נובמבר': 11, 'נוב׳': 11,
    'december': 12, 'dec': 12, 'דצמבר': 12, 'דצמ׳': 12,
}


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


def _strip_optional_hebrew_year(words):
    """
    Remove a trailing Hebrew/Gregorian year token if present so day+month still parse.
    Examples of year-like tokens: תשפ\"ה, 2020, ה'תשפ\"ד
    """
    if not words:
        return words
    last = words[-1].replace('"', '').replace("'", "").replace('׳', '').replace('״', '')
    # Pure digits year
    if last.isdigit() and len(last) == 4:
        return words[:-1]
    # Hebrew year often starts with ת and has length >= 3
    if last.startswith('ת') and len(last) >= 3:
        return words[:-1]
    if last.startswith('הת') and len(last) >= 4:
        return words[:-1]
    return words


def _parse_single_line_for_date(line_clean):
    """
    Helper to extract (month_num, day, formatted_hebrew_date, event_type, subject_name)
    from a line. Year is optional and ignored when present.
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

    subject_name = None
    date_part = line_clean

    for sep in [' - ', ' – ', ' : ', ':', '-']:
        if sep in line_clean:
            parts = line_clean.split(sep, 1)
            date_part = parts[1].strip()
            subject_name = parts[0].strip()
            break

    words = _strip_optional_hebrew_year(date_part.split())
    month_num = None
    month_idx = -1

    # Multi-word Hebrew month names first (e.g. מנחם אב, אדר א)
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


def _parse_gregorian_partial_date(line_clean):
    """
    Parse Gregorian day+month (year optional) from a note line.
    Supports: 15/3, 15.3, 15-3, 3/15/1990, 15 March, March 15, 15 במרץ
    Returns (month, day, event_type, subject_name) or None.
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

    subject_name = None
    date_part = line_clean
    for sep in [' - ', ' – ', ' : ', ':', '-']:
        # Avoid treating 15-3 as a subject separator: only split if left side has letters
        if sep in line_clean:
            left, right = line_clean.split(sep, 1)
            if any(c.isalpha() or '\u0590' <= c <= '\u05FF' for c in left):
                subject_name = left.strip()
                date_part = right.strip()
                break

    # Numeric forms: D/M, D.M, D-M, D/M/YYYY, YYYY-M-D
    m = re.search(r'\b(\d{1,2})[./-](\d{1,2})(?:[./-](\d{2,4}))?\b', date_part)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        # Prefer D/M (Israeli) when both <= 12; if first > 12 it's day? actually first>12 => day/month invalid as M/D
        if a > 12 and b <= 12:
            day, month = a, b
        elif b > 12 and a <= 12:
            month, day = a, b
        else:
            # Default Israeli: day/month
            day, month = a, b
        if 1 <= month <= 12 and 1 <= day <= 31:
            return (month, day, event_type, subject_name)

    # "15 March" / "March 15" / "15 במרץ"
    tokens = re.findall(r'[\w\u0590-\u05FF]+', date_part, flags=re.UNICODE)
    month = None
    day = None
    for i, tok in enumerate(tokens):
        key = tok.lower()
        if key in GREGORIAN_MONTHS:
            month = GREGORIAN_MONTHS[key]
            # day before or after
            for j in (i - 1, i + 1):
                if 0 <= j < len(tokens) and tokens[j].isdigit():
                    day = int(tokens[j])
                    break
            break
    if month and day and 1 <= day <= 31:
        return (month, day, event_type, subject_name)

    return None


def parse_hebrew_date_and_event_type_from_note(note_text):
    """
    Parses Hebrew dates, event types, and subject names from a contact's note/comment text.

    Returns a list of tuples: (month_num, day, formatted_hebrew_date_str, event_type, subject_name)
    Year is never required.
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
            if not subject_name:
                if i + 1 < len(lines) and not _parse_single_line_for_date(lines[i+1]):
                    subject_name = lines[i+1]
                    i += 1
                elif i > 0 and not _parse_single_line_for_date(lines[i-1]):
                    subject_name = lines[i-1]

            results.append((month_num, day, formatted_date, event_type, subject_name))
        else:
            if i + 1 < len(lines):
                next_parsed = _parse_single_line_for_date(lines[i+1])
                if next_parsed:
                    month_num, day, formatted_date, event_type, s_name = next_parsed
                    if not s_name:
                        s_name = line
                    results.append((month_num, day, formatted_date, event_type, s_name))
                    i += 1
        i += 1

    return results


def parse_gregorian_partial_dates_from_note(note_text):
    """Parse Gregorian day+month (no year required) from note lines."""
    if not note_text:
        return []
    results = []
    for line in note_text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Prefer Hebrew parser; only fall back to Gregorian if no Hebrew month found
        if _parse_single_line_for_date(line):
            continue
        parsed = _parse_gregorian_partial_date(line)
        if parsed:
            results.append(parsed)
    return results


def _match_gregorian_month_day(target_hebrew_dates_map, month, day):
    """
    Find gregorian dates in the upcoming window whose month/day match.
    target_hebrew_dates_map values are date objects.
    """
    matches = []
    for gdate in target_hebrew_dates_map.values():
        if isinstance(gdate, date) and gdate.month == month and gdate.day == day:
            matches.append(gdate)
    return matches


def get_upcoming_contact_events(target_hebrew_dates_map):
    """
    Fetches Google Contacts, parses Hebrew (and partial Gregorian) dates from notes
    and structured birthdays/events, and returns events in the target window.

    Day+month without year is fully supported.

    Returns list of tuples:
    (gregorian_date, original_date_str_parsed, contact_name, event_type, contact_id)
    """
    service = get_people_service()
    if not service:
        logger.info("Google People API service unavailable. Skipping contact sync.")
        return []

    contact_events = []
    seen = set()  # (resource_name, date, event_type, display_name)

    def _add(gdate, label, display_name, event_type, resource_name):
        key = (resource_name, gdate, event_type, display_name)
        if key in seen:
            return
        seen.add(key)
        contact_events.append((gdate, label, display_name, event_type, resource_name))

    try:
        page_token = None
        while True:
            results = service.people().connections().list(
                resourceName='people/me',
                pageSize=1000,
                personFields='names,biographies,birthdays,events',
                pageToken=page_token
            ).execute()

            connections = results.get('connections', [])
            for person in connections:
                resource_name = person.get('resourceName', '')
                names = person.get('names', [])
                contact_name = names[0].get('displayName') if names else "Unknown Contact"

                # --- Notes / biographies (Hebrew + partial Gregorian) ---
                biographies = person.get('biographies', [])
                for bio in biographies:
                    note = bio.get('value', '')
                    for item in parse_hebrew_date_and_event_type_from_note(note):
                        month_num, day, formatted_date_str, event_type, subject_name = item
                        hebrew_key = (month_num, day)
                        if hebrew_key in target_hebrew_dates_map:
                            gdate = target_hebrew_dates_map[hebrew_key]
                            display_name = f"{contact_name} ({subject_name})" if subject_name else contact_name
                            _add(gdate, formatted_date_str, display_name, event_type, resource_name)

                    for month, day, event_type, subject_name in parse_gregorian_partial_dates_from_note(note):
                        for gdate in _match_gregorian_month_day(target_hebrew_dates_map, month, day):
                            display_name = f"{contact_name} ({subject_name})" if subject_name else contact_name
                            label = f"{day:02d}/{month:02d}"
                            _add(gdate, label, display_name, event_type, resource_name)

                # --- Structured Google birthday field (year optional) ---
                for bday in person.get('birthdays', []) or []:
                    d = bday.get('date') or {}
                    month = d.get('month')
                    day = d.get('day')
                    if not month or not day:
                        continue
                    for gdate in _match_gregorian_month_day(target_hebrew_dates_map, int(month), int(day)):
                        label = f"{int(day):02d}/{int(month):02d}"
                        _add(gdate, label, contact_name, "BIRT", resource_name)

                # --- Structured events (anniversary etc., year optional) ---
                for ev in person.get('events', []) or []:
                    d = ev.get('date') or {}
                    month = d.get('month')
                    day = d.get('day')
                    if not month or not day:
                        continue
                    ev_type_raw = (ev.get('type') or '').lower()
                    if 'anni' in ev_type_raw or 'wedding' in ev_type_raw or 'marriage' in ev_type_raw:
                        event_type = "MARR"
                    elif 'death' in ev_type_raw or 'yahrzeit' in ev_type_raw:
                        event_type = "DEAT"
                    else:
                        event_type = "BIRT"
                    for gdate in _match_gregorian_month_day(target_hebrew_dates_map, int(month), int(day)):
                        label = f"{int(day):02d}/{int(month):02d}"
                        _add(gdate, label, contact_name, event_type, resource_name)

            page_token = results.get('nextPageToken')
            if not page_token:
                break

    except HttpError as error:
        logger.error(f"Google People API request failed: {error}")
    except Exception as e:
        logger.error(f"Unexpected error while fetching Google Contacts: {e}")

    return contact_events
