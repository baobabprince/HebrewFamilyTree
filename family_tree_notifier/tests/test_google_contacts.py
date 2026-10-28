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
        month_num, day, date_str, event_type = parsed[0]
        self.assertEqual(month_num, 8) # Iyyar
        self.assertEqual(day, 15)
        self.assertEqual(date_str, "טו אייר")
        self.assertEqual(event_type, "BIRT")

    def test_parse_hebrew_date_and_event_type_from_note_yahrzeit(self):
        note = "יארצייט ג' בתשרי"
        parsed = parse_hebrew_date_and_event_type_from_note(note)
        self.assertEqual(len(parsed), 1)
        month_num, day, date_str, event_type = parsed[0]
        self.assertEqual(month_num, 1) # Tishrei
        self.assertEqual(day, 3)
        self.assertEqual(date_str, "ג תשרי")
        self.assertEqual(event_type, "DEAT")

    def test_parse_hebrew_date_and_event_type_from_note_anniversary(self):
        note = "יום נישואין: י בטבת"
        parsed = parse_hebrew_date_and_event_type_from_note(note)
        self.assertEqual(len(parsed), 1)
        month_num, day, date_str, event_type = parsed[0]
        self.assertEqual(month_num, 4) # Tevet
        self.assertEqual(day, 10)
        self.assertEqual(date_str, "י טבת")
        self.assertEqual(event_type, "MARR")

    def test_parse_hebrew_date_and_event_type_from_note_multiple_lines(self):
        note = "יום הולדת: טו באייר\nיארצייט: ג בתשרי"
        parsed = parse_hebrew_date_and_event_type_from_note(note)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0][3], "BIRT")
        self.assertEqual(parsed[1][3], "DEAT")

    @patch('family_tree_notifier.google_contacts_utils.get_people_service')
    def test_get_upcoming_contact_events(self, mock_get_people_service):
        mock_service = MagicMock()
        mock_get_people_service.return_value = mock_service

        mock_connections = mock_service.people().connections().list().execute
        mock_connections.return_value = {
            'connections': [
                {
                    'resourceName': 'people/c12345',
                    'names': [{'displayName': 'ישראל ישראלי'}],
                    'biographies': [{'value': 'יום הולדת טו באייר'}]
                }
            ]
        }

        target_hebrew_dates_map = {
            (8, 15): date(2024, 5, 23)
        }

        events = get_upcoming_contact_events(target_hebrew_dates_map)
        self.assertEqual(len(events), 1)
        greg_date, orig_str, name, event_type, resource_name = events[0]
        self.assertEqual(greg_date, date(2024, 5, 23))
        self.assertEqual(orig_str, "טו אייר")
        self.assertEqual(name, "ישראל ישראלי")
        self.assertEqual(event_type, "BIRT")
        self.assertEqual(resource_name, "people/c12345")

if __name__ == '__main__':
    unittest.main()
