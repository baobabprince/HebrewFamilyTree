import unittest
import os
import logging
from unittest.mock import patch, mock_open, MagicMock
from gedcom.parser import Parser
# from gedcom.element.individual import IndividualElement
# from gedcom.element.family import FamilyElement
from gedcom.element.element import Element # Import Element to use its constructor properly
from gedcom_utils import (
    get_hebrew_day_string,
    fix_gedcom_format,
    get_name_from_individual,
    process_event,
    process_individual_events,
    process_family_events,
    process_gedcom_file
)
from constants import HEBREW_MONTHS_MAP, HEBREW_EVENT_NAMES, HEBREW_MONTH_NAMES_FULL, HEBREW_DAY_TO_NUM

class TestGedcomUtils(unittest.TestCase):

    def setUp(self):
        # Suppress logging for cleaner test output, unless debugging
        logging.disable(logging.CRITICAL)

        self.test_ged_path = "test_temp.ged"
        self.fixed_ged_path = "fixed_test_temp.ged"
        self.output_csv_path = "output_test.csv"

    def tearDown(self):
        # Clean up created files
        if os.path.exists(self.test_ged_path):
            os.remove(self.test_ged_path)
        if os.path.exists(self.fixed_ged_path):
            os.remove(self.fixed_ged_path)
        if os.path.exists(self.output_csv_path):
            os.remove(self.output_csv_path)
        
        # Re-enable logging after tests
        logging.disable(logging.NOTSET)

    # Test cases for get_hebrew_day_string
    def test_get_hebrew_day_string_single_digit(self):
        self.assertEqual(get_hebrew_day_string(1), "א")
        self.assertEqual(get_hebrew_day_string(9), "ט")

    def test_get_hebrew_day_string_double_digit(self):
        self.assertEqual(get_hebrew_day_string(10), "י")
        self.assertEqual(get_hebrew_day_string(15), "טו")
        self.assertEqual(get_hebrew_day_string(20), "כ")
        self.assertEqual(get_hebrew_day_string(29), "כט")

    def test_get_hebrew_day_string_max_day(self):
        self.assertEqual(get_hebrew_day_string(30), "ל")

    def test_get_hebrew_day_string_out_of_range(self):
        self.assertEqual(get_hebrew_day_string(0), "0")
        self.assertEqual(get_hebrew_day_string(31), "31")
        self.assertEqual(get_hebrew_day_string(-5), "-5")

    # Test cases for get_name_from_individual
    def test_get_name_from_individual_basic(self):
        mock_name_child = MagicMock()
        mock_name_child.get_tag.return_value = "NAME"
        mock_name_child.get_value.return_value = "John /Doe/"
        
        mock_indi_element = MagicMock()
        mock_indi_element.get_child_elements.return_value = [mock_name_child]
        
        self.assertEqual(get_name_from_individual(mock_indi_element), "John Doe")

    def test_get_name_from_individual_no_name(self):
        mock_birt_child = MagicMock()
        mock_birt_child.get_tag.return_value = "BIRT"
        
        mock_indi_element = MagicMock()
        mock_indi_element.get_child_elements.return_value = [mock_birt_child]
        
        self.assertEqual(get_name_from_individual(mock_indi_element), "Unknown Name")

    def test_get_name_from_individual_empty_name(self):
        mock_name_child = MagicMock()
        mock_name_child.get_tag.return_value = "NAME"
        mock_name_child.get_value.return_value = " / / "
        
        mock_indi_element = MagicMock()
        mock_indi_element.get_child_elements.return_value = [mock_name_child]
        
        self.assertEqual(get_name_from_individual(mock_indi_element), "")

    # Test cases for fix_gedcom_format
    def test_fix_gedcom_format_valid_lines(self):
        gedcom_content = [
            "0 @I1@ INDI",
            "1 NAME John /Doe/",
            "2 GIVN John",
            "1 BIRT",
            "2 DATE 1 JAN 1900"
        ]
        with open(self.test_ged_path, "w", encoding="utf-8") as f:
            f.write("\n".join(gedcom_content))
        
        fix_gedcom_format(self.test_ged_path, self.fixed_ged_path)

        with open(self.fixed_ged_path, "r", encoding="utf-8") as f:
            fixed_content = f.read().strip().split("\n")
        
        expected_content = [
            "0 @I1@ INDI",
            "1 NAME John /Doe/",
            "2 GIVN John",
            "1 BIRT",
            "2 DATE 1 JAN 1900"
        ]
        self.assertEqual(fixed_content, expected_content)

    def test_fix_gedcom_format_invalid_lines(self):
        gedcom_content = [
            "0 @I1@ INDI",
            "This is an invalid line", # Should be logged
            "1 NAME John /Doe/",
            "   2 GIVN John", # extra spaces - will be normalized
            "1 BIRT",
            "2 DATE 1 JAN 1900",
            "  Another invalid line with too many spaces" # Should be logged
        ]
        with open(self.test_ged_path, "w", encoding="utf-8") as f:
            f.write("\n".join(gedcom_content))
        
        # Enable logging temporarily for this test to capture warnings
        logging.disable(logging.NOTSET)
        with self.assertLogs('gedcom_utils', level='WARNING') as cm:
            fix_gedcom_format(self.test_ged_path, self.fixed_ged_path)
            self.assertEqual(len(cm.output), 2) # Expect two warning messages
            self.assertIn("WARNING:gedcom_utils:Dropping non-GEDCOM-compliant line: This is an invalid line", cm.output[0])
            # The line is stripped before logging, so the expected string should reflect that
            self.assertIn("WARNING:gedcom_utils:Dropping non-GEDCOM-compliant line: Another invalid line with too many spaces", cm.output[1])
        logging.disable(logging.CRITICAL) # Re-suppress logging

        with open(self.fixed_ged_path, "r", encoding="utf-8") as f:
            fixed_content = f.read().strip().split("\n")
        
        expected_content = [
            "0 @I1@ INDI",
            "1 NAME John /Doe/",
            "2 GIVN John",
            "1 BIRT",
            "2 DATE 1 JAN 1900"
        ]
        self.assertEqual(fixed_content, expected_content)
    
    def test_fix_gedcom_format_empty_input(self):
        with open(self.test_ged_path, "w", encoding="utf-8") as f:
            f.write("")
        
        fix_gedcom_format(self.test_ged_path, self.fixed_ged_path)
        
        with open(self.fixed_ged_path, "r", encoding="utf-8") as f:
            fixed_content = f.read().strip()
        self.assertEqual(fixed_content, "")

    def test_fix_gedcom_format_normalization(self):
        gedcom_content = [
            "0 @I1@ INDI",
            "1 NAME  John   /Doe/", # Multiple spaces
            "2  GIVN John", # Leading spaces on level, should be normalized
            "1 BIRT",
            "2 DATE 1 JAN 1900"
        ]
        with open(self.test_ged_path, "w", encoding="utf-8") as f:
            f.write("\n".join(gedcom_content))
        
        fix_gedcom_format(self.test_ged_path, self.fixed_ged_path)

        with open(self.fixed_ged_path, "r", encoding="utf-8") as f:
            fixed_content = f.read().strip().split("\n")
        
        expected_content = [
            "0 @I1@ INDI",
            "1 NAME John /Doe/",
            "2 GIVN John",
            "1 BIRT",
            "2 DATE 1 JAN 1900"
        ]
        self.assertEqual(fixed_content, expected_content)
    
    # Test cases for process_event
    @patch('gedcom_utils.logger') # Patch the logger specifically
    def test_process_event_hebrew_date_basic(self, mock_logger):
        mock_date_child = MagicMock()
        mock_date_child.get_tag.return_value = "DATE"
        mock_date_child.get_value.return_value = "@#DHEBREW@ 15 KISLEV 5785"

        mock_event_element = MagicMock()
        mock_event_element.get_child_elements.return_value = [mock_date_child]
        mock_event_element.get_tag.return_value = "BIRT" # For event_type fallback

        dates = []
        name = "Test Person"
        event_type = "Birth"
        
        greg_year = process_event(mock_event_element, name, dates, event_type)
        
        # Expecting the Hebrew year as Gregorian if no explicit Gregorian year is provided
        self.assertEqual(greg_year, 5785)
        self.assertEqual(len(dates), 1)
        self.assertEqual(dates[0][0], 3) # KISLEV is 3rd Hebrew month
        self.assertEqual(dates[0][1], 15)
        self.assertEqual(dates[0][2], "טו כסלו")
        self.assertEqual(dates[0][3], "Test Person - Birth: טו כסלו")
    
    @patch('gedcom_utils.logger')
    def test_process_event_hebrew_date_with_gregorian_year(self, mock_logger):
        mock_date_child = MagicMock()
        mock_date_child.get_tag.return_value = "DATE"
        mock_date_child.get_value.return_value = "@#DHEBREW@ 10 TEVET 5785 (12 DEC 2024)"

        mock_event_element = MagicMock()
        mock_event_element.get_child_elements.return_value = [mock_date_child]
        mock_event_element.get_tag.return_value = "DEAT"

        dates = []
        name = "Test Person"
        event_type = "Death"
        
        greg_year = process_event(mock_event_element, name, dates, event_type)
        
        self.assertEqual(greg_year, 2024)
        self.assertEqual(len(dates), 1)
        self.assertEqual(dates[0][0], 4) # TEVET is 4th Hebrew month
        self.assertEqual(dates[0][1], 10)
        self.assertEqual(dates[0][2], "י טבת")
        self.assertEqual(dates[0][3], "Test Person - Death: י טבת")

    @patch('gedcom_utils.logger')
    def test_process_event_hebrew_date_no_day(self, mock_logger):
        mock_date_child = MagicMock()
        mock_date_child.get_tag.return_value = "DATE"
        mock_date_child.get_value.return_value = "@#DHEBREW@ ADAR I 5785"

        mock_event_element = MagicMock()
        mock_event_element.get_child_elements.return_value = [mock_date_child]
        mock_event_element.get_tag.return_value = "BIRT"

        dates = []
        name = "Test Person"
        event_type = "Birth"
        
        greg_year = process_event(mock_event_element, name, dates, event_type)
        
        self.assertEqual(greg_year, 5785) # Expect Hebrew year as Gregorian
        self.assertEqual(len(dates), 1)
        self.assertEqual(dates[0][0], 61) # ADAR I is 61st Hebrew month (internal representation)
        self.assertEqual(dates[0][1], 1) # Defaults to day 1
        self.assertEqual(dates[0][2], "א אדר א")
        self.assertEqual(dates[0][3], "Test Person - Birth: א אדר א")

    @patch('gedcom_utils.logger')
    def test_process_event_gregorian_date_only(self, mock_logger):
        mock_date_child = MagicMock()
        mock_date_child.get_tag.return_value = "DATE"
        mock_date_child.get_value.return_value = "1 JAN 1900"

        mock_event_element = MagicMock()
        mock_event_element.get_child_elements.return_value = [mock_date_child]
        mock_event_element.get_tag.return_value = "BIRT"

        dates = []
        name = "Test Person"
        event_type = "Birth"
        
        greg_year = process_event(mock_event_element, name, dates, event_type)
        
        self.assertEqual(greg_year, 1900)
        self.assertEqual(len(dates), 0) # Should not add Gregorian-only dates to 'dates' list

    @patch('gedcom_utils.logger')
    def test_process_event_empty_date(self, mock_logger):
        mock_date_child = MagicMock()
        mock_date_child.get_tag.return_value = "DATE"
        mock_date_child.get_value.return_value = ""

        mock_event_element = MagicMock()
        mock_event_element.get_child_elements.return_value = [mock_date_child]
        mock_event_element.get_tag.return_value = "BIRT"

        dates = []
        name = "Test Person"
        event_type = "Birth"
        
        greg_year = process_event(mock_event_element, name, dates, event_type)
        
        self.assertEqual(greg_year, None)
        self.assertEqual(len(dates), 0)
    
    @patch('gedcom_utils.logger')
    def test_process_event_no_date_tag(self, mock_logger):
        mock_plac_child = MagicMock()
        mock_plac_child.get_tag.return_value = "PLAC"
        mock_plac_child.get_value.return_value = "London"

        mock_event_element = MagicMock()
        mock_event_element.get_child_elements.return_value = [mock_plac_child]
        mock_event_element.get_tag.return_value = "BIRT"

        dates = []
        name = "Test Person"
        event_type = "Birth"
        
        greg_year = process_event(mock_event_element, name, dates, event_type)
        
        self.assertEqual(greg_year, None)
        self.assertEqual(len(dates), 0)

    @patch('gedcom_utils.logger')
    def test_process_event_hebrew_date_with_qualifier(self, mock_logger):
        mock_date_child = MagicMock()
        mock_date_child.get_tag.return_value = "DATE"
        mock_date_child.get_value.return_value = "@#DHEBREW@ ABT 10 SIVAN 5780"

        mock_event_element = MagicMock()
        mock_event_element.get_child_elements.return_value = [mock_date_child]
        mock_event_element.get_tag.return_value = "BIRT"

        dates = []
        name = "Test Person"
        event_type = "Birth"

        greg_year = process_event(mock_event_element, name, dates, event_type)

        self.assertEqual(greg_year, 5780)
        self.assertEqual(len(dates), 1)
        self.assertEqual(dates[0][0], 9)  # SIVAN is 9th Hebrew month
        self.assertEqual(dates[0][1], 10)
        self.assertEqual(dates[0][2], "י סיון")
        self.assertEqual(dates[0][3], "Test Person - Birth: י סיון")
    
    @patch('gedcom_utils.logger')
    def test_process_event_hebrew_date_with_and_qualifier(self, mock_logger):
        mock_date_child = MagicMock()
        mock_date_child.get_tag.return_value = "DATE"
        mock_date_child.get_value.return_value = "@#DHEBREW@ 10 SIVAN AND 11 TAMMUZ 5780"

        mock_event_element = MagicMock()
        mock_event_element.get_child_elements.return_value = [mock_date_child]
        mock_event_element.get_tag.return_value = "BIRT"

        dates = []
        name = "Test Person"
        event_type = "Birth"

        greg_year = process_event(mock_event_element, name, dates, event_type)

        self.assertEqual(greg_year, 5780)
        self.assertEqual(len(dates), 1) # Should only process the first part
        self.assertEqual(dates[0][0], 9)  # SIVAN is 9th Hebrew month
        self.assertEqual(dates[0][1], 10)
        self.assertEqual(dates[0][2], "י סיון")
        self.assertEqual(dates[0][3], "Test Person - Birth: י סיון")


if __name__ == '__main__':
    unittest.main()