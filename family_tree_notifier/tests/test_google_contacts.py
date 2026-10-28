import unittest
from unittest.mock import MagicMock, patch
from datetime import date

from family_tree_notifier.google_contacts_utils import (
    parse_hebrew_date_and_event_type_from_note,
    get_upcoming_contact_events
)

class TestGoogleContactsUtils(unittest.TestCase):

    def test_parse_hebrew_date_and_event_type_from_note_single_birthday(self):
        note = "תאריך עברי: טו באייר"
        parsed = parse_hebrew_date_and_event_type_from_note(note)
        self.assertEqual(len(parsed), 1)
        month_num, day, date_str, event_type, subject_name = parsed[0]
        self.assertEqual(month_num, 8) # Iyyar
        self.assertEqual(day, 15)
        self.assertEqual(date_str, "טו אייר")
        self.assertEqual(event_type, "BIRT")

    def test_parse_hebrew_date_and_event_type_from_note_yahrzeit(self):
        note = "יארצייט ג' בתשרי"
        parsed = parse_hebrew_date_and_event_type_from_note(note)
        self.assertEqual(len(parsed), 1)
        month_num, day, date_str, event_type, subject_name = parsed[0]
        self.assertEqual(month_num, 1) # Tishrei
        self.assertEqual(day, 3)
        self.assertEqual(date_str, "ג תשרי")
        self.assertEqual(event_type, "DEAT")

    def test_parse_hebrew_date_and_event_type_from_note_anniversary(self):
        note = "יום נישואין: י בטבת"
        parsed = parse_hebrew_date_and_event_type_from_note(note)
        self.assertEqual(len(parsed), 1)
        month_num, day, date_str, event_type, subject_name = parsed[0]
        self.assertEqual(month_num, 4) # Tevet
        self.assertEqual(day, 10)
        self.assertEqual(date_str, "י טבת")
        self.assertEqual(event_type, "MARR")

    def test_parse_hebrew_date_and_event_type_from_note_menachem_av(self):
        note = "שקד - כד מנחם אב תשעט"
        parsed = parse_hebrew_date_and_event_type_from_note(note)
        self.assertEqual(len(parsed), 1)
        month_num, day, date_str, event_type, subject_name = parsed[0]
        self.assertEqual(month_num, 11) # Av
        self.assertEqual(day, 24)
        self.assertEqual(date_str, "כד אב")
        self.assertEqual(event_type, "BIRT")
        self.assertEqual(subject_name, "שקד")

    def test_parse_hebrew_date_and_event_type_from_note_multiline_children(self):
        note = "א ניסן התש\"ן\nנטע\nשקד - כד מנחם אב תשעט\nדרור - טו ניסן תשפב"
        parsed = parse_hebrew_date_and_event_type_from_note(note)
        self.assertEqual(len(parsed), 3)

        self.assertEqual(parsed[0][0], 7) # Nisan
        self.assertEqual(parsed[0][1], 1)
        self.assertEqual(parsed[0][4], "נטע")

        self.assertEqual(parsed[1][0], 11) # Av
        self.assertEqual(parsed[1][1], 24)
        self.assertEqual(parsed[1][4], "שקד")

        self.assertEqual(parsed[2][0], 7) # Nisan
        self.assertEqual(parsed[2][1], 15)
        self.assertEqual(parsed[2][4], "דרור")

    @patch('family_tree_notifier.google_contacts_utils.get_people_service')
    def test_get_upcoming_contact_events(self, mock_get_people_service):
        mock_service = MagicMock()
        mock_get_people_service.return_value = mock_service

        mock_connections = mock_service.people().connections().list().execute
        mock_connections.return_value = {
            'connections': [
                {
                    'resourceName': 'people/c12345',
                    'names': [{'displayName': 'אבנר בן זמרה'}],
                    'biographies': [{'value': 'שקד - כד מנחם אב תשעט'}]
                }
            ]
        }

        target_hebrew_dates_map = {
            (11, 24): date(2024, 8, 28)
        }

        events = get_upcoming_contact_events(target_hebrew_dates_map)
        self.assertEqual(len(events), 1)
        greg_date, orig_str, name, event_type, resource_name = events[0]
        self.assertEqual(greg_date, date(2024, 8, 28))
        self.assertEqual(orig_str, "כד אב")
        self.assertEqual(name, "אבנר בן זמרה (שקד)")
        self.assertEqual(event_type, "BIRT")
        self.assertEqual(resource_name, "people/c12345")

if __name__ == '__main__':
    unittest.main()
