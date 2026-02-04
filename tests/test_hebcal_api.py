import unittest
from unittest.mock import patch, MagicMock
from datetime import date
from hebcal_api import get_hebrew_date_from_api, get_gregorian_date_from_hebrew_api, get_parasha_for_week

class TestHebcalApi(unittest.TestCase):
    @patch('hebcal_api.requests.get')
    def test_get_hebrew_date_from_api_shvat(self, mock_get):
        # Test cases for 5 upcoming dates in Sh'vat 5785 (Jan/Feb 2025)
        test_cases = [
            (date(2025, 1, 30), 5, 1), # 1 Sh'vat 5785
            (date(2025, 1, 31), 5, 2), # 2 Sh'vat 5785
            (date(2025, 2, 1), 5, 3),  # 3 Sh'vat 5785
            (date(2025, 2, 2), 5, 4),  # 4 Sh'vat 5785
            (date(2025, 2, 3), 5, 5)   # 5 Sh'vat 5785
        ]

        for gregorian_date, expected_month, expected_day in test_cases:
            with self.subTest(gregorian_date=gregorian_date):
                # Configure the mock response from Hebcal API
                mock_response = MagicMock()
                mock_response.is_redirect = False
                # Simulate the API returning "Sh'vat"
                mock_response.json.return_value = {"hm": "Sh'vat", "hd": expected_day, "hy": "5785"}
                mock_get.return_value = mock_response

                # Call the function under test
                result = get_hebrew_date_from_api(gregorian_date)

                # Assert the expected outcome
                self.assertEqual(result, (expected_month, expected_day))

    @patch('hebcal_api.requests.get')
    def test_get_parasha_for_week_hebrew(self, mock_get):
        # Configure the mock response from Hebcal API
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {"category": "parashat", "hebrew": "פרשת ויחי"}
            ]
        }
        mock_get.return_value = mock_response

        # Call the function under test
        result = get_parasha_for_week(date(2024, 1, 1), lang="he")

        # Assert the expected outcome
        self.assertEqual(result, "פרשת ויחי")

    @patch('hebcal_api.requests.get')
    def test_get_parasha_for_week_english(self, mock_get):
        # Configure the mock response from Hebcal API
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {"category": "parashat", "title": "Parashat Vayechi"}
            ]
        }
        mock_get.return_value = mock_response

        # Call the function under test
        result = get_parasha_for_week(date(2024, 1, 1), lang="en")

        # Assert the expected outcome
        self.assertEqual(result, "Parashat Vayechi")

if __name__ == '__main__':
    unittest.main()
