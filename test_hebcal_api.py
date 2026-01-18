import unittest
from unittest.mock import patch, MagicMock
from datetime import date
from hebcal_api import get_hebrew_date_from_api, get_gregorian_date_from_hebrew_api

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
    @patch('hebcal_api.logging.warning')
    def test_get_gregorian_date_from_hebrew_api_mismatch_logs_context(self, mock_log_warning, mock_get):
        # Configure the mock to simulate a date mismatch
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "gy": 2024, "gm": 1, "gd": 10,  # A different date
            "hy": 5784, "hm": "Tevet", "hd": 29
        }
        mock_get.return_value = mock_response

        # Call the function with specific context
        context = "John Doe - Birthday"
        result = get_gregorian_date_from_hebrew_api(5731, 5, 28, context=context)

        # Assert that the fallback year is returned
        self.assertEqual(result, 5731)

        # Assert that the logger was called with the context
        mock_log_warning.assert_called_once()
        self.assertIn(context, mock_log_warning.call_args[0][0])

if __name__ == '__main__':
    unittest.main()
