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

# Lines like "אשתו: רננה" are family context, not the person the date belongs to
_RELATIONSHIP_PREFIXES = (
    'אשתו', 'בעלה', 'בעל', 'אשת', 'בנו', 'בתו', 'בן', 'בת',
    'אביו', 'אמו', 'אבא', 'אמא', 'אחיו', 'אחותו', 'אח', 'אחות',
    'חתנו', 'כלתו', 'סבו', 'סבתו', 'נכדו', 'נכדתו',
    'wife', 'husband', 'son', 'daughter', 'father', 'mother',
    'brother', 'sister', 'spouse',
)


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
    if last.isdigit() and len(last) == 4:
        return words[:-1]
    if last.startswith('ת') and len(last) >= 3:
        return words[:-1]
    if last.startswith('הת') and len(last) >= 4:
        return words[:-1]
    return words


def _is_relationship_label(text):
    """True for lines like 'אשתו: רננה' / 'בנו יואב' used as family context only."""
    if not text:
        return False
    cleaned = text.strip()
    # "אשתו: רננה" or "אשתו רננה"
    for sep in (':', '–', '-', ' '):
        if sep in cleaned:
            head = cleaned.split(sep, 1)[0].strip()
            if head in _RELATIONSHIP_PREFIXES:
                return True
    if cleaned in _RELATIONSHIP_PREFIXES:
        return True
    return False


def _is_day_token(token):
    t = token.replace('"', '').replace("'", "").replace('׳', '').replace(',', '').strip()
    if t in HEBREW_DAY_TO_NUM:
        return True
    try:
        n = int(t)
        return 1 <= n <= 31
    except ValueError:
        return False


def _parse_single_line_for_date(line_clean):
    """
    Helper to extract (month_num, day, formatted_hebrew_date, event_type, subject_name)
    from a line. Year is optional and ignored when present.

    Supports inline names before the date, e.g. "יואב כז חשוון תשע\"ו".
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
            left, right = parts[0].strip(), parts[1].strip()
            # Only treat as name separator if left side looks like a name (not pure date)
            if left and not _parse_month_day_only(left):
                date_part = right
                subject_name = left
                break

    words = _strip_optional_hebrew_year(date_part.split())
    month_num = None
    month_idx = -1

    # Multi-word Hebrew month names first (e.g. מנחם אב, אדר א)
    for i in range(len(words) - 1):
        candidate_raw = f"{words[i]} {words[i+1]}".replace('"', '').replace("'", "").replace('׳', '')
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
            clean_word = words[i].replace('"', '').replace("'", "").replace('׳', '')
            candidate_clean = clean_word[1:] if clean_word.startswith("ב") and len(clean_word) > 2 else clean_word
            candidate_upper = candidate_clean.upper()
            if candidate_upper in HEBREW_MONTHS_MAP:
                month_num = HEBREW_MONTHS_MAP[candidate_upper]
                month_idx = i
                break
            if clean_word in HEBREW_MONTHS_MAP:
                month_num = HEBREW_MONTHS_MAP[clean_word]
                month_idx = i
                break

    if month_num is None:
        return None

    day = 1
    day_idx = month_idx - 1
    if month_idx > 0:
        day_candidate_str = words[month_idx - 1].replace('"', '').replace("'", "").replace('׳', '').replace(',', '').strip()
        if day_candidate_str in HEBREW_DAY_TO_NUM:
            day = HEBREW_DAY_TO_NUM[day_candidate_str]
        else:
            try:
                day = int(day_candidate_str)
            except ValueError:
                day_idx = -1  # word before month is not a day

    # Inline subject: words before the day token, e.g. "יואב כז חשוון"
    if not subject_name and day_idx > 0:
        name_words = words[:day_idx]
        # Drop leading relationship words if the rest is the real name
        while name_words and name_words[0] in _RELATIONSHIP_PREFIXES:
            name_words = name_words[1:]
        if name_words:
            subject_name = ' '.join(name_words).strip() or None

    hebrew_month_name = HEBREW_MONTH_NAMES_FULL.get(month_num, "")
    formatted_hebrew_date = f"{get_hebrew_day_string(day)} {hebrew_month_name}"

    return (month_num, day, formatted_hebrew_date, event_type, subject_name)


def _parse_month_day_only(text):
    """Return True if text itself looks like a Hebrew date fragment (no person name)."""
    words = _strip_optional_hebrew_year(text.split())
    for i, w in enumerate(words):
        clean = w.replace('"', '').replace("'", "").replace('׳', '')
        cand = clean[1:] if clean.startswith('ב') and len(clean) > 2 else clean
        if cand.upper() in HEBREW_MONTHS_MAP or clean in HEBREW_MONTHS_MAP:
            return True
        if i + 1 < len(words):
            two = f"{words[i]} {words[i+1]}".replace('"', '').replace("'", "").replace('׳', '')
            if two.upper() in HEBREW_MONTHS_MAP or two in HEBREW_MONTHS_MAP:
                return True
    return False


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
        if sep in line_clean:
            left, right = line_clean.split(sep, 1)
            if any(c.isalpha() or '\u0590' <= c <= '\u05FF' for c in left):
                subject_name = left.strip()
                date_part = right.strip()
                break

    m = re.search(r'\b(\d{1,2})[./-](\d{1,2})(?:[./-](\d{2,4}))?\b', date_part)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if a > 12 and b <= 12:
            day, month = a, b
        elif b > 12 and a <= 12:
            month, day = a, b
        else:
            day, month = a, b
        if 1 <= month <= 12 and 1 <= day <= 31:
            return (month, day, event_type, subject_name)

    tokens = re.findall(r'[\w\u0590-\u05FF]+', date_part, flags=re.UNICODE)
    month = None
    day = None
    for i, tok in enumerate(tokens):
        key = tok.lower()
        if key in GREGORIAN_MONTHS:
            month = GREGORIAN_MONTHS[key]
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

    Example note:
        י\"ד אדר א
        כה אדר א' התשמ\"ט
        אשתו: רננה
        יואב כז חשוון תשע\"ו
        נגה כז אלול תשע\"ח
    → subjects for last two lines are יואב and נגה; relationship line is ignored.
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
            # Only borrow neighboring lines as subject when this line has no inline name,
            # and the neighbor is not a relationship label / another date.
            if not subject_name:
                if i + 1 < len(lines):
                    nxt = lines[i + 1]
                    if (
                        not _parse_single_line_for_date(nxt)
                        and not _is_relationship_label(nxt)
                    ):
                        subject_name = nxt
                        i += 1
                if not subject_name and i > 0:
                    prev = lines[i - 1]
                    if (
                        not _parse_single_line_for_date(prev)
                        and not _is_relationship_label(prev)
                    ):
                        subject_name = prev

            results.append((month_num, day, formatted_date, event_type, subject_name))
        else:
            # "יואב" on its own line followed by a date line without a name
            if i + 1 < len(lines) and not _is_relationship_label(line):
                next_parsed = _parse_single_line_for_date(lines[i + 1])
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

                biographies = person.get('biographies', [])
                for bio in biographies:
                    note = bio.get('value', '')
                    for item in parse_hebrew_date_and_event_type_from_note(note):
                        month_num, day, formatted_date_str, event_type, subject_name = item
                        hebrew_key = (month_num, day)
                        if hebrew_key in target_hebrew_dates_map:
                            gdate = target_hebrew_dates_map[hebrew_key]
                            # Prefer the subject (child/relative) as the person of the event
                            if subject_name and not _is_relationship_label(subject_name):
                                display_name = subject_name
                            else:
                                display_name = contact_name
                            _add(gdate, formatted_date_str, display_name, event_type, resource_name)

                    for month, day, event_type, subject_name in parse_gregorian_partial_dates_from_note(note):
                        for gdate in _match_gregorian_month_day(target_hebrew_dates_map, month, day):
                            if subject_name and not _is_relationship_label(subject_name):
                                display_name = subject_name
                            else:
                                display_name = contact_name
                            label = f"{day:02d}/{month:02d}"
                            _add(gdate, label, display_name, event_type, resource_name)

                for bday in person.get('birthdays', []) or []:
                    d = bday.get('date') or {}
                    month = d.get('month')
                    day = d.get('day')
                    if not month or not day:
                        continue
                    for gdate in _match_gregorian_month_day(target_hebrew_dates_map, int(month), int(day)):
                        label = f"{int(day):02d}/{int(month):02d}"
                        _add(gdate, label, contact_name, "BIRT", resource_name)

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
