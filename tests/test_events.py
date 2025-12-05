import pytest
import os
from gedcom_utils import process_gedcom_file

@pytest.fixture
def process_test_gedcom(tmp_path):
    """Fixture to process a GEDCOM file from the test_data directory."""
    def _processor(gedcom_filename):
        test_data_path = os.path.join("tests", "test_data", gedcom_filename)
        output_csv_path = tmp_path / "output.csv"
        events = process_gedcom_file(test_data_path, str(output_csv_path))
        return events
    return _processor

def test_birthdays(process_test_gedcom):
    """Tests processing of birthday events."""
    events = process_test_gedcom("birthdays.ged")
    assert len(events) == 4
    names = {e[1] for e in events}
    assert "Shlomo /Cohen/" in names
    assert "Rivka /Levi/" in names
    assert all(e[2] == "יומולדת" for e in events)

def test_yahrzeits(process_test_gedcom):
    """Tests processing of yahrzeit (death) events."""
    events = process_test_gedcom("yahrzeits.ged")
    assert len(events) == 2
    names = {e[1] for e in events}
    assert "Moshe /Shapira/" in names
    assert all(e[2] == "יאהרצייט" for e in events)

def test_anniversaries(process_test_gedcom):
    """Tests processing of anniversary events."""
    events = process_test_gedcom("anniversaries.ged")
    assert len(events) == 1
    assert events[0][1] == "Yitzhak /Barak/ & Leah /Barak/"
    assert events[0][2] == "יום נישואין"

def test_missing_dates_are_ignored(process_test_gedcom):
    """Tests that individuals with missing dates are ignored."""
    events = process_test_gedcom("missing_dates.ged")
    assert len(events) == 0

def test_leap_year_events(process_test_gedcom):
    """Tests processing of events in Adar (ADR) and Adar Sheni (ADS)."""
    events = process_test_gedcom("leap_year.ged")
    assert len(events) == 2
    event_descs = {e[0] for e in events}
    assert "יד אדר" in event_descs
    assert "טו אדר" in event_descs
