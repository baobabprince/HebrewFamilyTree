import unittest
from datetime import date
from unittest.mock import Mock
from family_tree_notifier.issue_generator import build_issue_body, get_parents_names
from family_tree_notifier.localization import get_translation

class TestYahrzeitGender(unittest.TestCase):

    def test_build_issue_body_yahrzeit_male(self):
        # Mock data for a male yahrzeit
        enriched_list = [
            (1, ['@I1@'], date(2024, 1, 1), 'א׳ בטבת', 'John Doe', 'DEAT', '@I1@')
        ]
        id2name = {'@I1@': 'John Doe'}
        today_gregorian = date(2024, 1, 1)
        distance_threshold = 0
        person_id = '@I2@'
        parser = Mock()
        parser.get_element_dictionary.return_value = {}
        individual_details = {
            'John Doe': {'birth_year': 1950, 'death_year': 2020, 'gender': 'M'}
        }

        # Generate the issue body
        issue_body = build_issue_body(enriched_list, id2name, today_gregorian, distance_threshold, person_id, parser, individual_details, {}, lang="he")

        # Assertions
        self.assertIn("נפטר בגיל 70", issue_body)
        self.assertIn("4 שנים לפטירתו", issue_body)

    def test_build_issue_body_yahrzeit_female(self):
        # Mock data for a female yahrzeit
        enriched_list = [
            (1, ['@I1@'], date(2024, 1, 1), 'א׳ בטבת', 'Jane Doe', 'DEAT', '@I1@')
        ]
        id2name = {'@I1@': 'Jane Doe'}
        today_gregorian = date(2024, 1, 1)
        distance_threshold = 0
        person_id = '@I2@'
        parser = Mock()
        parser.get_element_dictionary.return_value = {}
        individual_details = {
            'Jane Doe': {'birth_year': 1950, 'death_year': 2020, 'gender': 'F'}
        }

        # Generate the issue body
        issue_body = build_issue_body(enriched_list, id2name, today_gregorian, distance_threshold, person_id, parser, individual_details, {}, lang="he")

        # Assertions
        self.assertIn("נפטרה בגיל 70", issue_body)
        self.assertIn("4 שנים לפטירתה", issue_body)

    def test_build_issue_body_yahrzeit_unknown_birth(self):
        # Mock data for a yahrzeit with unknown birth year
        enriched_list = [
            (1, ['@I1@'], date(2024, 1, 1), 'א׳ בטבת', 'John Doe', 'DEAT', '@I1@')
        ]
        id2name = {'@I1@': 'John Doe'}
        today_gregorian = date(2024, 1, 1)
        distance_threshold = 0
        person_id = '@I2@'
        parser = Mock()
        parser.get_element_dictionary.return_value = {}
        individual_details = {
            'John Doe': {'birth_year': None, 'death_year': 2020, 'gender': 'M'}
        }

        # Generate the issue body
        issue_body = build_issue_body(enriched_list, id2name, today_gregorian, distance_threshold, person_id, parser, individual_details, {}, lang="he")

        # Assertions
        self.assertIn("4 שנים לפטירתו", issue_body)
        self.assertNotIn("גיל", issue_body)

    def test_build_issue_body_deceased_birthday_female(self):
        # Mock data for a deceased female's birthday
        enriched_list = [
            (1, ['@I1@'], date(2024, 1, 1), 'א׳ בטבת', 'Jane Doe', 'BIRT', '@I1@')
        ]
        id2name = {'@I1@': 'Jane Doe'}
        today_gregorian = date(2024, 1, 1)
        distance_threshold = 0
        person_id = '@I2@'
        parser = Mock()
        individual_details = {
            'Jane Doe': {'birth_year': 1950, 'death_year': 2020, 'gender': 'F'}
        }

        # Generate the issue body
        issue_body = build_issue_body(enriched_list, id2name, today_gregorian, distance_threshold, person_id, parser, individual_details, {}, lang="he")

        # Assertions
        self.assertIn("🕯️", issue_body)
        self.assertIn("נפטרה בגיל 70", issue_body)
        self.assertIn("74 שנים מאז לידתה", issue_body)

    def test_build_issue_body_yahrzeit_with_parents(self):
        # Mock person with FAMC pointing to family with HUSB and WIFE
        person = Mock()
        famc = Mock()
        famc.get_tag.return_value = "FAMC"
        famc.get_value.return_value = "@F1@"
        person.get_child_elements.return_value = [famc]

        family = Mock()
        husb = Mock()
        husb.get_tag.return_value = "HUSB"
        husb.get_value.return_value = "@I10@"
        wife = Mock()
        wife.get_tag.return_value = "WIFE"
        wife.get_value.return_value = "@I11@"
        family.get_child_elements.return_value = [husb, wife]

        parser = Mock()
        parser.get_element_dictionary.return_value = {
            "@I1@": person,
            "@F1@": family,
        }

        id2name = {
            "@I1@": "Isaac Avinu",
            "@I10@": "Abraham Avinu",
            "@I11@": "Sarah Imenu",
        }

        parents = get_parents_names("@I1@", parser, id2name, lang="he")
        self.assertEqual(parents, "Abraham Avinu, Sarah Imenu")

        enriched_list = [
            (1, ["@I1@"], date(2024, 1, 1), "א׳ בטבת", "Isaac Avinu", "DEAT", "@I1@")
        ]
        individual_details = {
            "Isaac Avinu": {"birth_year": 1930, "death_year": 2000, "gender": "M"}
        }
        issue_body = build_issue_body(
            enriched_list, id2name, date(2024, 1, 1), 0, "@I2@", parser, individual_details, {}, lang="he"
        )
        self.assertIn("**הורים**: `Abraham Avinu, Sarah Imenu`", issue_body)

        # English label
        issue_body_en = build_issue_body(
            enriched_list, id2name, date(2024, 1, 1), 0, "@I2@", parser, individual_details, {}, lang="en"
        )
        self.assertIn("**Parents**: `Abraham Avinu, Sarah Imenu`", issue_body_en)

if __name__ == '__main__':
    unittest.main()
