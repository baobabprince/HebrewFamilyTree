import unittest
from unittest.mock import patch, MagicMock, call
from datetime import date, timedelta
from family_tree_notifier.hebcal_api import get_hebrew_date_range_api, get_parasha_for_week
import family_tree_notifier.main as main

class TestRange(unittest.TestCase):

    @patch('family_tree_notifier.hebcal_api.get_hebrew_date_from_api')
    def test_get_hebrew_date_range_api_10_days(self, mock_get_hebrew_date):
        # Setup
        start_date = date(2024, 1, 1)
        num_days = 10
        mock_get_hebrew_date.return_value = (1, 1) # Dummy Hebrew date

        # Execute
        get_hebrew_date_range_api(start_date, num_days)

        # Verify
        self.assertEqual(mock_get_hebrew_date.call_count, 10)
        expected_calls = [call(start_date + timedelta(days=i)) for i in range(10)]
        mock_get_hebrew_date.assert_has_calls(expected_calls)

    @patch('family_tree_notifier.hebcal_api.requests.get')
    def test_get_parasha_for_week_range(self, mock_get):
        # Setup
        start_date = date(2024, 1, 1)
        num_days = 10
        mock_response = MagicMock()
        mock_response.json.return_value = {"items": []}
        mock_get.return_value = mock_response

        # Execute
        get_parasha_for_week(start_date, lang="he", num_days=num_days)

        # Verify
        args, kwargs = mock_get.call_args
        params = kwargs.get('params')
        self.assertEqual(params['start'], '2024-01-01')
        self.assertEqual(params['end'], '2024-01-11') # 2024-01-01 + 10 days

    @patch('family_tree_notifier.main.argparse.ArgumentParser.parse_args')
    @patch('family_tree_notifier.main.download_gedcom_from_drive')
    @patch('family_tree_notifier.main.fix_gedcom_format')
    @patch('family_tree_notifier.main.process_gedcom_file')
    @patch('family_tree_notifier.main.get_hebrew_date_range_api')
    @patch('family_tree_notifier.main.get_parasha_for_week')
    @patch('family_tree_notifier.main.build_graph')
    @patch('family_tree_notifier.main.build_issue_body')
    @patch('family_tree_notifier.main.Parser')
    def test_main_days_argument(self, mock_parser_class, mock_build_issue, mock_build_graph, mock_get_parasha,
                                 mock_get_range, mock_process, mock_fix, mock_download, mock_parse_args):
        # Setup
        mock_parse_args.return_value = MagicMock(lang="he", days=10)
        mock_download.return_value = True
        mock_process.return_value = ([('1 Tevet', 'John Doe', 'BIRT', '@I1@')], {}, {})
        mock_build_graph.return_value = (MagicMock(), {})
        mock_get_range.return_value = {}
        mock_get_parasha.return_value = "Parasha"

        # We need to mock the open for FIXED_GEDCOM_FILE since main.py reads it
        with patch('builtins.open', unittest.mock.mock_open(read_data="dummy content")):
            # Execute
            main.main()

        # Verify
        mock_get_range.assert_called_once()
        self.assertEqual(mock_get_range.call_args[0][1], 10)

        mock_get_parasha.assert_called_once()
        self.assertEqual(mock_get_parasha.call_args[0][2], 10)

if __name__ == '__main__':
    unittest.main()
