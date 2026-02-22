import unittest
from datetime import date
from unittest.mock import Mock
from family_tree_notifier.issue_generator import build_issue_body
from family_tree_notifier.localization import get_translation

class TestYahrzeitGender(unittest.TestCase):

    def test_build_issue_body_yahrzeit_male(self):
        # Mock data for a male yahrzeit
        enriched_list = [
            (1, ['@I1@'], 'direct', date(2024, 1, 1), 'א׳ בטבת', 'John Doe', 'DEAT')
        ]
        id2name = {'@I1@': 'John Doe'}
        today_gregorian = date(2024, 1, 1)
        config = {'PERSON_ID': '@I2@', 'SHOW_PATH_DISTANCE_DIRECT': '0'}
        parser = Mock()
        individual_details = {
            'John Doe': {'birth_year': 1950, 'death_year': 2020, 'gender': 'M'}
        }

        # Generate the issue body
        issue_body = build_issue_body(enriched_list, id2name, today_gregorian, config, parser, individual_details, {}, lang="he")

        # Assertions
        self.assertIn("נפטר בגיל 70", issue_body)
        self.assertIn("4 שנים לפטירתו", issue_body)

    def test_build_issue_body_yahrzeit_female(self):
        # Mock data for a female yahrzeit
        enriched_list = [
            (1, ['@I1@'], 'direct', date(2024, 1, 1), 'א׳ בטבת', 'Jane Doe', 'DEAT')
        ]
        id2name = {'@I1@': 'Jane Doe'}
        today_gregorian = date(2024, 1, 1)
        config = {'PERSON_ID': '@I2@', 'SHOW_PATH_DISTANCE_DIRECT': '0'}
        parser = Mock()
        individual_details = {
            'Jane Doe': {'birth_year': 1950, 'death_year': 2020, 'gender': 'F'}
        }

        # Generate the issue body
        issue_body = build_issue_body(enriched_list, id2name, today_gregorian, config, parser, individual_details, {}, lang="he")

        # Assertions
        self.assertIn("נפטרה בגיל 70", issue_body)
        self.assertIn("4 שנים לפטירתה", issue_body)

    def test_build_issue_body_yahrzeit_unknown_birth(self):
        # Mock data for a yahrzeit with unknown birth year
        enriched_list = [
            (1, ['@I1@'], 'direct', date(2024, 1, 1), 'א׳ בטבת', 'John Doe', 'DEAT')
        ]
        id2name = {'@I1@': 'John Doe'}
        today_gregorian = date(2024, 1, 1)
        config = {'PERSON_ID': '@I2@', 'SHOW_PATH_DISTANCE_DIRECT': '0'}
        parser = Mock()
        individual_details = {
            'John Doe': {'birth_year': None, 'death_year': 2020, 'gender': 'M'}
        }

        # Generate the issue body
        issue_body = build_issue_body(enriched_list, id2name, today_gregorian, config, parser, individual_details, {}, lang="he")

        # Assertions
        self.assertIn("4 שנים לפטירתו", issue_body)
        self.assertNotIn("גיל", issue_body)

    def test_build_issue_body_deceased_birthday_female(self):
        # Mock data for a deceased female's birthday
        enriched_list = [
            (1, ['@I1@'], 'direct', date(2024, 1, 1), 'א׳ בטבת', 'Jane Doe', 'BIRT')
        ]
        id2name = {'@I1@': 'Jane Doe'}
        today_gregorian = date(2024, 1, 1)
        config = {'PERSON_ID': '@I2@', 'SHOW_PATH_DISTANCE_DIRECT': '0'}
        parser = Mock()
        individual_details = {
            'Jane Doe': {'birth_year': 1950, 'death_year': 2020, 'gender': 'F'}
        }

        # Generate the issue body
        issue_body = build_issue_body(enriched_list, id2name, today_gregorian, config, parser, individual_details, {}, lang="he")

        # Assertions
        self.assertIn("🕯️", issue_body)
        self.assertIn("נפטרה בגיל 70", issue_body)
        self.assertIn("74 שנים מאז לידתה", issue_body)

if __name__ == '__main__':
    unittest.main()
