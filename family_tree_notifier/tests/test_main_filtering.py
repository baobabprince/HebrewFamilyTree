import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
from datetime import date

# Import main after mocking or directly mock the functions inside it
from family_tree_notifier.main import main

class TestMainFiltering(unittest.TestCase):

    @patch('family_tree_notifier.main.argparse.ArgumentParser.parse_args')
    @patch('family_tree_notifier.main.download_gedcom_from_drive')
    @patch('family_tree_notifier.main.fix_gedcom_format')
    @patch('family_tree_notifier.main.process_gedcom_file')
    @patch('family_tree_notifier.main.get_hebrew_date_range_api')
    @patch('family_tree_notifier.main.find_relevant_hebrew_dates')
    @patch('family_tree_notifier.main.build_graph')
    @patch('family_tree_notifier.main.get_parasha_for_week')
    @patch('family_tree_notifier.main.build_issue_body')
    @patch('family_tree_notifier.main.Parser')
    @patch('builtins.open', new_callable=mock_open)
    @patch.dict(os.environ, {"GITHUB_OUTPUT": "mock_github_output.txt"})
    def test_main_with_event_type_filter_deat(self, mock_file, mock_parser_class, mock_build_issue_body,
                                              mock_get_parasha, mock_build_graph, mock_find_relevant,
                                              mock_get_date_range, mock_process_gedcom, mock_fix_gedcom,
                                              mock_download, mock_parse_args):
        # Set up mock command-line arguments
        args = MagicMock()
        args.lang = "he"
        args.days = 8
        args.event_type = "DEAT"
        mock_parse_args.return_value = args

        # Mock downloads and conversions
        mock_download.return_value = True

        # We need process_gedcom_file to return some non-empty processed_rows so that it doesn't return early.
        mock_process_gedcom.return_value = ([("א' בטבת", "John Doe", "DEAT", "@I1@")], {}, {})

        # Mock some relevant upcoming dates of different types
        # format: (gregorian_date, original_date_str_parsed, name, event_type, gedcom_id)
        mock_find_relevant.return_value = [
            (date(2024, 1, 1), "א' בטבת", "John Doe", "DEAT", "@I1@"),
            (date(2024, 1, 2), "ב' בטבת", "Jane Doe", "BIRT", "@I2@")
        ]

        # Mock family graph and relationship calculations
        mock_build_graph.return_value = (MagicMock(), {})
        mock_get_parasha.return_value = "ויחי"
        mock_build_issue_body.return_value = "Mock Issue Body"

        # Mock file operations for reading fixed tree
        mock_file.return_value.read.return_value = "GEDCOM content"

        # Run main
        main()

        # Verify that only the "DEAT" event was kept
        # The code filters relevant_upcoming_dates:
        # relevant_upcoming_dates = [item for item in relevant_upcoming_dates if item[3] == event_type_filter]
        # In our case, the second item ("BIRT") should be filtered out.
        # Let's verify that we processed only 1 enriched item
        self.assertEqual(mock_build_issue_body.call_count, 1)
        enriched_arg = mock_build_issue_body.call_args[0][0]
        self.assertEqual(len(enriched_arg), 1)
        self.assertEqual(enriched_arg[0][5], "DEAT") # event_type is at index 5 in enriched tuple

        # Verify GITHUB_OUTPUT writes the yahrzeit specific title
        # "אזכרות ויארצייטים קרובים ויחי"
        # We need to check what was written to the file
        written_content = "".join([call[0][0] for call in mock_file().write.call_args_list])
        self.assertIn("issue_title=אזכרות ויארצייטים קרובים ויחי", written_content)
        self.assertIn("has_relevant_dates=true", written_content)

    @patch('family_tree_notifier.main.argparse.ArgumentParser.parse_args')
    @patch('family_tree_notifier.main.download_gedcom_from_drive')
    @patch('family_tree_notifier.main.fix_gedcom_format')
    @patch('family_tree_notifier.main.process_gedcom_file')
    @patch('family_tree_notifier.main.get_hebrew_date_range_api')
    @patch('family_tree_notifier.main.find_relevant_hebrew_dates')
    @patch('family_tree_notifier.main.build_graph')
    @patch('family_tree_notifier.main.get_parasha_for_week')
    @patch('family_tree_notifier.main.build_issue_body')
    @patch('family_tree_notifier.main.Parser')
    @patch('builtins.open', new_callable=mock_open)
    @patch.dict(os.environ, {"GITHUB_OUTPUT": "mock_github_output.txt"})
    def test_main_with_no_relevant_dates(self, mock_file, mock_parser_class, mock_build_issue_body,
                                         mock_get_parasha, mock_build_graph, mock_find_relevant,
                                         mock_get_date_range, mock_process_gedcom, mock_fix_gedcom,
                                         mock_download, mock_parse_args):
        # Set up mock command-line arguments
        args = MagicMock()
        args.lang = "he"
        args.days = 8
        args.event_type = "DEAT"
        mock_parse_args.return_value = args

        # Mock downloads and conversions
        mock_download.return_value = True
        mock_process_gedcom.return_value = ([("א' בטבת", "John Doe", "DEAT", "@I1@")], {}, {})

        # No upcoming dates
        mock_find_relevant.return_value = []

        # Mock family graph and relationship calculations
        mock_build_graph.return_value = (MagicMock(), {})
        mock_get_parasha.return_value = ""
        mock_build_issue_body.return_value = ""

        # Mock file operations for reading fixed tree
        mock_file.return_value.read.return_value = "GEDCOM content"

        # Run main
        main()

        # Verify GITHUB_OUTPUT has has_relevant_dates=false
        written_content = "".join([call[0][0] for call in mock_file().write.call_args_list])
        self.assertIn("has_relevant_dates=false", written_content)

if __name__ == '__main__':
    unittest.main()
