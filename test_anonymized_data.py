import unittest
import os
import csv
from gedcom_utils import process_gedcom_file
from anonymized_data import ANONYMIZED_GEDCOM_DATA

class TestAnonymizedData(unittest.TestCase):

    def setUp(self):
        self.test_ged_path = "anonymized_test.ged"
        self.output_csv_path = "anonymized_output_test.csv"
        with open(self.test_ged_path, "w", encoding="utf-8") as f:
            f.write(ANONYMIZED_GEDCOM_DATA)

    def tearDown(self):
        if os.path.exists(self.test_ged_path):
            os.remove(self.test_ged_path)
        if os.path.exists(self.output_csv_path):
            os.remove(self.output_csv_path)

    def test_process_anonymized_data(self):
        csv_data, individual_details = process_gedcom_file(self.test_ged_path, self.output_csv_path)

        # Expected CSV data
        expected_csv_data = [
            ['ז תשרי', 'Person Two', 'יארצייט'],
            ['א חשון', 'Person Two', 'יום הולדת'],
            ['יד אדר', 'Person One', 'יום הולדת']
        ]

        # Expected individual details
        expected_individual_details = {
            'Person One': {'birth_year': 1989, 'death_year': None},
            'Person Two': {'birth_year': 1934, 'death_year': 2020}
        }

        # Assertions
        self.assertEqual(csv_data, expected_csv_data)
        self.assertEqual(individual_details, expected_individual_details)

        # Verify the content of the CSV file
        with open(self.output_csv_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader)
            self.assertEqual(header, ["Date", "Name", "Event"])
            rows = list(reader)
            self.assertEqual(rows, expected_csv_data)

if __name__ == '__main__':
    unittest.main()
