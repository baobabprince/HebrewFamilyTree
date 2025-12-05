import pytest
import os
import textwrap
from gedcom_utils import process_gedcom_file

@pytest.fixture
def create_gedcom_file(tmp_path):
    """A fixture to create a temporary GEDCOM file for date parsing tests."""
    def _creator(filename, content):
        filepath = tmp_path / filename
        dedented_content = textwrap.dedent(content).strip()
        filepath.write_text(dedented_content, encoding='utf-8')
        return str(filepath)
    return _creator

def test_various_date_formats(create_gedcom_file, tmp_path):
    """Tests various valid Hebrew date formats."""
    gedcom_content = """
        0 @I1@ INDI
        1 NAME Person One
        1 BIRT
        2 DATE @#DHEBREW@ 15 SVN 5708
        0 @I2@ INDI
        1 NAME Person Two
        1 BIRT
        2 DATE @#DHEBREW@ "יב" ELL 5751
        0 @I3@ INDI
        1 NAME Person Three
        1 DEAT
        2 DATE @#DHEBREW@ כט CSH 5723
        0 @I4@ INDI
        1 NAME Person Four
        1 BIRT
        2 DATE @#DHEBREW@ 1 ADR 5757
        0 @I5@ INDI
        1 NAME Person Five
        1 BIRT
        2 DATE @#DHEBREW@ 1 ADS 5760
    """
    ged_path = create_gedcom_file("dates.ged", gedcom_content)
    csv_path = os.path.join(tmp_path, "output.csv")
    result = process_gedcom_file(ged_path, csv_path)

    assert len(result) == 5
    result_set = {tuple(row) for row in result}
    expected_set = {
        ('טו סיון', 'Person One', 'יומולדת'),
        ('יב אלול', 'Person Two', 'יומולדת'),
        ('כט חשון', 'Person Three', 'יאהרצייט'),
        ('א אדר', 'Person Four', 'יומולדת'),
        ('א אדר', 'Person Five', 'יומולדת'),
    }
    assert result_set == expected_set

def test_invalid_and_missing_dates(create_gedcom_file, tmp_path):
    """Tests that events with invalid or missing dates are ignored."""
    gedcom_content = """
        0 @I1@ INDI
        1 NAME Valid Person
        1 BIRT
        2 DATE @#DHEBREW@ 1 TSH 5780
        0 @I2@ INDI
        1 NAME Invalid Day
        1 DEAT
        2 DATE @#DHEBREW@ 31 CSH 5723
        0 @I3@ INDI
        1 NAME Invalid Month
        1 BIRT
        2 DATE @#DHEBREW@ 15 XYZ 5700
        0 @I4@ INDI
        1 NAME Missing Date
        1 BIRT
        2 DATE @#DHEBREW@
    """
    ged_path = create_gedcom_file("invalid.ged", gedcom_content)
    csv_path = os.path.join(tmp_path, "output.csv")
    result = process_gedcom_file(ged_path, csv_path)

    assert len(result) == 1
    assert result[0] == ['א תשרי', 'Valid Person', 'יומולדת']
