import unittest
from datetime import date
from unittest.mock import Mock
from family_tree_notifier.issue_generator import build_issue_body
from family_tree_notifier.localization import get_translation

class TestMain(unittest.TestCase):

    def test_build_issue_body_deceased_birthday(self):
        # Mock data for a deceased person's birthday
        enriched_list = [
            (1, ['@I1@'], 'direct', date(2024, 1, 1), 'א׳ בטבת', 'John Doe', 'BIRT')
        ]
        id2name = {'@I1@': 'John Doe'}
        today_gregorian = date(2024, 1, 1)
        config = {'PERSON_ID': '@I2@', 'SHOW_PATH_DISTANCE_DIRECT': '0'}
        parser = Mock()
        individual_details = {
            'John Doe': {'birth_year': 1950, 'death_year': 2020}
        }

        # Generate the issue body
        issue_body = build_issue_body(enriched_list, id2name, today_gregorian, config, parser, individual_details, {}, lang="he")

        # Assertions
        self.assertIn("🕯️", issue_body)
        self.assertIn("נפטר בגיל 70", issue_body)
        self.assertIn("74 שנים מאז לידתו", issue_body)
        self.assertNotIn("🎂", issue_body)

    def test_build_issue_body_living_birthday(self):
        # Mock data for a living person's birthday
        enriched_list = [
            (1, ['@I1@'], 'direct', date(2024, 1, 1), 'א׳ בטבת', 'Jane Doe', 'BIRT')
        ]
        id2name = {'@I1@': 'Jane Doe'}
        today_gregorian = date(2024, 1, 1)
        config = {'PERSON_ID': '@I2@', 'SHOW_PATH_DISTANCE_DIRECT': '0'}
        parser = Mock()
        individual_details = {
            'Jane Doe': {'birth_year': 1990, 'death_year': None}
        }

        # Generate the issue body
        issue_body = build_issue_body(enriched_list, id2name, today_gregorian, config, parser, individual_details, {}, lang="he")

        # Assertions
        self.assertIn("🎂", issue_body)
        self.assertIn("(גיל 34)", issue_body)
        self.assertNotIn("🕯️", issue_body)

    def test_build_issue_body_yahrzeit(self):
        # Mock data for a yahrzeit
        enriched_list = [
            (1, ['@I1@'], 'direct', date(2024, 1, 1), 'א׳ בטבת', 'John Doe', 'DEAT')
        ]
        id2name = {'@I1@': 'John Doe'}
        today_gregorian = date(2024, 1, 1)
        config = {'PERSON_ID': '@I2@', 'SHOW_PATH_DISTANCE_DIRECT': '0'}
        parser = Mock()
        individual_details = {
            'John Doe': {'birth_year': 1950, 'death_year': 2020}
        }

        # Generate the issue body
        issue_body = build_issue_body(enriched_list, id2name, today_gregorian, config, parser, individual_details, {}, lang="he")

        # Assertions
        self.assertIn("🪦", issue_body)
        self.assertIn("נפטר בגיל 70", issue_body)
        self.assertIn("4 שנים לפטירתו", issue_body)

    def test_build_issue_body_anniversary(self):
        # Mock data for an anniversary
        enriched_list = [
            (1, ['@I1@', '@I2@'], 'direct', date(2024, 1, 1), 'א׳ בטבת', 'John Doe & Jane Doe', 'MARR')
        ]
        id2name = {'@I1@': 'John Doe', '@I2@': 'Jane Doe'}
        today_gregorian = date(2024, 1, 1)
        config = {'PERSON_ID': '@I3@', 'SHOW_PATH_DISTANCE_DIRECT': '1'}
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
        issue_body = build_issue_body(enriched_list, id2name, today_gregorian, config, parser, individual_details, family_details, lang="he")

        # Assertions
        self.assertIn("💑", issue_body)
        self.assertIn("(נשואים: 30 שנים)", issue_body)

    def test_build_issue_body_anniversary_deceased_spouse(self):
        # Mock data for an anniversary where one spouse is deceased
        enriched_list = [
            (1, ['@I1@', '@I2@'], 'direct', date(2024, 1, 1), 'א׳ בטבת', 'John Doe & Jane Doe', 'MARR')
        ]
        id2name = {'@I1@': 'John Doe', '@I2@': 'Jane Doe'}
        today_gregorian = date(2024, 1, 1)
        config = {'PERSON_ID': '@I3@', 'SHOW_PATH_DISTANCE_DIRECT': '1'}
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
        issue_body = build_issue_body(enriched_list, id2name, today_gregorian, config, parser, individual_details, family_details, lang="he")

        # Assertions
        self.assertIn("💑", issue_body)
        self.assertIn("(היו נשואים 26 שנים)", issue_body)

    def test_build_issue_body_anniversary_divorced_couple(self):
        # Mock data for a divorced couple's anniversary
        enriched_list = [
            (1, ['@I1@', '@I2@'], 'direct', date(2024, 1, 1), 'א׳ בטבת', 'John Doe & Jane Doe', 'MARR')
        ]
        id2name = {'@I1@': 'John Doe', '@I2@': 'Jane Doe'}
        today_gregorian = date(2024, 1, 1)
        config = {'PERSON_ID': '@I3@', 'SHOW_PATH_DISTANCE_DIRECT': '1'}
        parser = Mock()
        individual_details = {}
        family_details = {
            'John Doe & Jane Doe': {
                'marriage_year': 1994,
                'divorce_year': 2010
            }
        }

        # Generate the issue body
        issue_body = build_issue_body(enriched_list, id2name, today_gregorian, config, parser, individual_details, family_details, lang="he")

        # Assertions
        self.assertIn("💑", issue_body)
        self.assertIn("(נישאו בשנת 1994)", issue_body)

    def test_build_issue_body_english_translation(self):
        # Mock data for a living person's birthday in English
        enriched_list = [
            (1, ['@I1@'], 'direct', date(2024, 1, 1), '1 Tevet', 'Jane Doe', 'BIRT')
        ]
        id2name = {'@I1@': 'Jane Doe'}
        today_gregorian = date(2024, 1, 1)
        config = {'PERSON_ID': '@I2@', 'SHOW_PATH_DISTANCE_DIRECT': '0'}
        parser = Mock()
        individual_details = {
            'Jane Doe': {'birth_year': 1990, 'death_year': None}
        }

        # Generate the issue body in English
        issue_body = build_issue_body(enriched_list, id2name, today_gregorian, config, parser, individual_details, {}, lang="en")

        # Assertions
        self.assertIn("🎂", issue_body)
        self.assertIn("(age 34)", issue_body)
        self.assertIn("Upcoming Hebrew Dates", issue_body)
        self.assertIn("* **Event**: `Birthday`", issue_body)
        self.assertIn("* **Person/Family**: `Jane Doe (age 34)`", issue_body)
        self.assertNotIn("🕯️", issue_body)

    def test_build_issue_body_direct_marker(self):
        # Mock data for a direct relative with a marker
        enriched_list = [
            (1, ['@I1@'], 'direct', date(2024, 1, 1), 'א׳ בטבת', 'John Doe', 'BIRT')
        ]
        id2name = {'@I1@': 'John Doe'}
        today_gregorian = date(2024, 1, 1)
        config = {
            'PERSON_ID': '@I2@',
            'DIRECT_MARKER': '⭐',
            'SHOW_PATH_DISTANCE_DIRECT': '10'
        }
        parser = Mock()
        individual_details = {'John Doe': {'birth_year': 1950}}

        # Generate the issue body
        issue_body = build_issue_body(enriched_list, id2name, today_gregorian, config, parser, individual_details, {}, lang="he")

        # Assertions
        self.assertIn("⭐ John Doe", issue_body)

    def test_build_issue_body_no_direct_marker_for_blood(self):
        # Mock data for a blood relative (non-direct) - should NOT have marker
        enriched_list = [
            (2, ['@I1@', '@I3@', '@I4@'], 'blood', date(2024, 1, 1), 'א׳ בטבת', 'Cousin Joe', 'BIRT')
        ]
        id2name = {'@I1@': 'Me', '@I3@': 'Uncle', '@I4@': 'Cousin Joe'}
        today_gregorian = date(2024, 1, 1)
        config = {
            'PERSON_ID': '@I1@',
            'DIRECT_MARKER': '⭐',
            'SHOW_PATH_DISTANCE_BLOOD': '10'
        }
        parser = Mock()
        individual_details = {'Cousin Joe': {'birth_year': 1990}}

        # Generate the issue body
        issue_body = build_issue_body(enriched_list, id2name, today_gregorian, config, parser, individual_details, {}, lang="he")

        # Assertions
        self.assertIn("Cousin Joe", issue_body)
        self.assertNotIn("⭐ Cousin Joe", issue_body)

if __name__ == '__main__':
    unittest.main()
