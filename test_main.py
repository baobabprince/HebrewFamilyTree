import unittest
from datetime import date
from unittest.mock import Mock
from main import build_issue_body
from localization import get_translation

class TestMain(unittest.TestCase):

    def test_build_issue_body_deceased_birthday(self):
        # Mock data for a deceased person's birthday
        enriched_list = [
            (1, ['@I1@'], date(2024, 1, 1), 'א׳ בטבת', 'John Doe', 'BIRT')
        ]
        id2name = {'@I1@': 'John Doe'}
        today_gregorian = date(2024, 1, 1)
        distance_threshold = 0
        person_id = '@I2@'
        parser = Mock()
        individual_details = {
            'John Doe': {'birth_year': 1950, 'death_year': 2020}
        }

        # Generate the issue body
        issue_body = build_issue_body(enriched_list, id2name, today_gregorian, distance_threshold, person_id, parser, individual_details, {}, lang="he")

        # Assertions
        self.assertIn("🕯️", issue_body)
        self.assertIn("נפטר בגיל 70", issue_body)
        self.assertIn("74 שנים מאז לידתו", issue_body)
        self.assertNotIn("🎂", issue_body)

    def test_build_issue_body_living_birthday(self):
        # Mock data for a living person's birthday
        enriched_list = [
            (1, ['@I1@'], date(2024, 1, 1), 'א׳ בטבת', 'Jane Doe', 'BIRT')
        ]
        id2name = {'@I1@': 'Jane Doe'}
        today_gregorian = date(2024, 1, 1)
        distance_threshold = 0
        person_id = '@I2@'
        parser = Mock()
        individual_details = {
            'Jane Doe': {'birth_year': 1990, 'death_year': None}
        }

        # Generate the issue body
        issue_body = build_issue_body(enriched_list, id2name, today_gregorian, distance_threshold, person_id, parser, individual_details, {}, lang="he")

        # Assertions
        self.assertIn("🎂", issue_body)
        self.assertIn("(גיל 34)", issue_body)
        self.assertNotIn("🕯️", issue_body)

    def test_build_issue_body_yahrzeit(self):
        # Mock data for a yahrzeit
        enriched_list = [
            (1, ['@I1@'], date(2024, 1, 1), 'א׳ בטבת', 'John Doe', 'DEAT')
        ]
        id2name = {'@I1@': 'John Doe'}
        today_gregorian = date(2024, 1, 1)
        distance_threshold = 0
        person_id = '@I2@'
        parser = Mock()
        individual_details = {
            'John Doe': {'birth_year': 1950, 'death_year': 2020}
        }

        # Generate the issue body
        issue_body = build_issue_body(enriched_list, id2name, today_gregorian, distance_threshold, person_id, parser, individual_details, {}, lang="he")

        # Assertions
        self.assertIn("🪦", issue_body)
        self.assertIn("נפטר בגיל 70", issue_body)
        self.assertIn("4 שנים לפטירתו", issue_body)

    def test_build_issue_body_anniversary(self):
        # Mock data for an anniversary
        enriched_list = [
            (1, ['@I1@', '@I2@'], date(2024, 1, 1), 'א׳ בטבת', 'John Doe & Jane Doe', 'MARR')
        ]
        id2name = {'@I1@': 'John Doe', '@I2@': 'Jane Doe'}
        today_gregorian = date(2024, 1, 1)
        distance_threshold = 1
        person_id = '@I3@'
        parser = Mock()
        individual_details = {}
        family_details = {
            'John Doe & Jane Doe': {
                'marriage_year': 1994,
                'husband_death_year': None,
                'wife_death_year': None
            }
        }

        # Generate the issue body
        issue_body = build_issue_body(enriched_list, id2name, today_gregorian, distance_threshold, person_id, parser, individual_details, family_details, lang="he")

        # Assertions
        self.assertIn("💑", issue_body)
        self.assertIn("(נישואים: 30 שנים)", issue_body)

    def test_build_issue_body_anniversary_deceased_spouse(self):
        # Mock data for an anniversary where one spouse is deceased
        enriched_list = [
            (1, ['@I1@', '@I2@'], date(2024, 1, 1), 'א׳ בטבת', 'John Doe & Jane Doe', 'MARR')
        ]
        id2name = {'@I1@': 'John Doe', '@I2@': 'Jane Doe'}
        today_gregorian = date(2024, 1, 1)
        distance_threshold = 1
        person_id = '@I3@'
        parser = Mock()
        individual_details = {
            'Jane Doe': {'death_year': 2020}
        }
        family_details = {
            'John Doe & Jane Doe': {
                'marriage_year': 1994,
                'husband_death_year': None,
                'wife_death_year': 2020
            }
        }

        # Generate the issue body
        issue_body = build_issue_body(enriched_list, id2name, today_gregorian, distance_threshold, person_id, parser, individual_details, family_details, lang="he")

        # Assertions
        self.assertIn("💑", issue_body)
        self.assertIn("(היו נשואים 26 שנים)", issue_body)

    def test_build_issue_body_anniversary_divorced_couple(self):
        # Mock data for a divorced couple's anniversary
        enriched_list = [
            (1, ['@I1@', '@I2@'], date(2024, 1, 1), 'א׳ בטבת', 'John Doe & Jane Doe', 'MARR')
        ]
        id2name = {'@I1@': 'John Doe', '@I2@': 'Jane Doe'}
        today_gregorian = date(2024, 1, 1)
        distance_threshold = 1
        person_id = '@I3@'
        parser = Mock()
        individual_details = {}
        family_details = {
            'John Doe & Jane Doe': {
                'marriage_year': 1994,
                'divorce_year': 2010
            }
        }

        # Generate the issue body
        issue_body = build_issue_body(enriched_list, id2name, today_gregorian, distance_threshold, person_id, parser, individual_details, family_details, lang="he")

        # Assertions
        self.assertIn("💑", issue_body)
        self.assertIn("(נישאו בשנת 1994)", issue_body)

    def test_build_issue_body_english_translation(self):
        # Mock data for a living person's birthday in English
        enriched_list = [
            (1, ['@I1@'], date(2024, 1, 1), '1 Tevet', 'Jane Doe', 'BIRT')
        ]
        id2name = {'@I1@': 'Jane Doe'}
        today_gregorian = date(2024, 1, 1)
        distance_threshold = 0
        person_id = '@I2@'
        parser = Mock()
        individual_details = {
            'Jane Doe': {'birth_year': 1990, 'death_year': None}
        }

        # Generate the issue body in English
        issue_body = build_issue_body(enriched_list, id2name, today_gregorian, distance_threshold, person_id, parser, individual_details, {}, lang="en")

        # Assertions
        self.assertIn("🎂", issue_body)
        self.assertIn("(age 34)", issue_body)
        self.assertIn("Upcoming Hebrew Dates", issue_body)
        self.assertIn("* **Event**: `Birthday`", issue_body)
        self.assertIn("* **Person/Family**: `Jane Doe (age 34)`", issue_body)
        self.assertNotIn("🕯️", issue_body)

if __name__ == '__main__':
    unittest.main()
