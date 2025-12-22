import unittest
from unittest.mock import patch, MagicMock
from datetime import date
import os
import main
from gedcom.parser import Parser

class TestMain(unittest.TestCase):

    def setUp(self):
        # Create a dummy GEDCOM file for testing
        self.gedcom_file = "test_duplicate_names.ged"
        self.person_id = "@I1@"
        self.distance_threshold = 1
        self.fixed_ged_path = "fixed_tree.ged"

    def tearDown(self):
        if os.path.exists(self.fixed_ged_path):
            os.remove(self.fixed_ged_path)

    @patch('main.download_gedcom_from_drive')
    @patch('main.fix_gedcom_format')
    @patch('main.process_gedcom_file')
    @patch('main.get_hebrew_date_range_api')
    @patch('main.find_relevant_hebrew_dates')
    @patch('main.get_parasha_for_week')
    def test_main_with_duplicate_names(self, mock_get_parasha, mock_find_relevant, mock_get_hebrew_range, mock_process_gedcom, mock_fix_gedcom, mock_download_gedcom):
        # --- Mock Setup ---

        # Mock external dependencies
        mock_download_gedcom.return_value = True
        mock_get_parasha.return_value = "פרשת השבוע"

        # Mock gedcom_utils.process_gedcom_file
        mock_process_gedcom.return_value = (
            [
                ['1 Kislev', 'Duplicate Name', 'Birthday', '@I3@'],
                ['10 Kislev', 'Duplicate Name', 'Birthday', '@I5@']
            ],
            {
                "Duplicate Name": {"birth_year": 2000}
            }
        )

        # Mock hebcal_api.find_relevant_hebrew_dates
        mock_find_relevant.return_value = [
            (date(2024, 12, 2), '1 Kislev', 'Duplicate Name', 'Birthday', '@I3@'),
            (date(2024, 12, 11), '10 Kislev', 'Duplicate Name', 'Birthday', '@I5@')
        ]

        # --- Test Execution ---
        os.environ['PERSONID'] = self.person_id
        os.environ['DISTANCE_THRESHOLD'] = str(self.distance_threshold)

        # Use a real parser instance with the test GEDCOM file
        gedcom_parser = Parser()
        gedcom_parser.parse_file(self.gedcom_file)

        # Create a dummy fixed_tree.ged for main.py to open
        with open(self.fixed_ged_path, "w") as f:
            f.write("")

        # Mock the build_issue_body to capture its input
        with patch('main.build_issue_body') as mock_build_issue_body:
            mock_build_issue_body.return_value = "Mocked Issue Body"

            # We need to let build_graph run with the real file
            with patch('main.build_graph') as mock_build_graph:
                from gedcom_graph import build_graph as actual_build_graph
                G, id2name = actual_build_graph(self.gedcom_file)
                mock_build_graph.return_value = (G, id2name)

                # Run the main function
                main.main()

        # --- Assertions ---

        # Check that build_issue_body was called
        self.assertTrue(mock_build_issue_body.called)

        # Get the arguments passed to build_issue_body
        enriched_list = mock_build_issue_body.call_args[0][0]

        # Find the results for each duplicate name
        result_i3 = next((item for item in enriched_list if item[4] == 'Duplicate Name' and item[1] == ['@I1@', '@I2@', '@I3@']), None)
        result_i5 = next((item for item in enriched_list if item[4] == 'Duplicate Name' and item[1] == ['@I1@', '@I4@', '@I5@']), None)

        # Assert that both individuals were found and have the correct paths
        self.assertIsNotNone(result_i3, "Path for @I3@ should be present")
        self.assertIsNotNone(result_i5, "Path for @I5@ should be present")

        # Assert the distances and paths are correct
        # Path: Root (@I1@) -> Child One (@I2@) -> Duplicate Name (@I3@)
        self.assertEqual(result_i3[0], 2) # distance
        self.assertEqual(result_i3[1], ['@I1@', '@I2@', '@I3@'])

        # Path: Root (@I1@) -> Sibling One (@I4@) -> Duplicate Name (@I5@)
        self.assertEqual(result_i5[0], 2) # distance
        self.assertEqual(result_i5[1], ['@I1@', '@I4@', '@I5@'])

if __name__ == '__main__':
    unittest.main()
