import os

# --- Constants for Hebrew Months Mapping (from GEDCOM abbreviations to month numbers) ---
HEBREW_MONTHS_MAP = {
    "TSH": 1, "CSH": 2, "KSL": 3, "TVT": 4, "SHV": 5, "ADR": 6,
    "ADS": 6, 
    "NSN": 7, "IYR": 8, "SVN": 9, "TMZ": 10, "AAV": 11, "ELL": 12,
}

HEBCAL_FULL_MONTH_NAMES_TO_NUM = {
    "Tishrei": 1, "Cheshvan": 2, "Kislev": 3, "Tevet": 4, "Shevat": 5,
    "Adar": 6, "Adar I": 6, "Adar II": 6,
    "Nisan": 7, "Iyyar": 8, "Sivan": 9, "Tamuz": 10, "Av": 11, "Elul": 12,
}

HEBREW_MONTH_NAMES_FULL = {
    1: "תשרי", 2: "חשון", 3: "כסלו", 4: "טבת", 5: "שבט", 6: "אדר",
    7: "ניסן", 8: "אייר", 9: "סיון", 10: "תמוז", 11: "אב", 12: "אלול",
}

HEBREW_DAY_TO_NUM = {
    "א": 1, "ב": 2, "ג": 3, "ד": 4, "ה": 5, "ו": 6, "ז": 7, "ח": 8, "ט": 9, "י": 10,
    "יא": 11, "יב": 12, "יג": 13, "יד": 14, "טו": 15, "טז": 16, "יז": 17, "יח": 18, "יט": 19,
    "כ": 20, "כא": 21, "כב": 22, "כג": 23, "כד": 24, "כה": 25, "כו": 26, "כז": 27, "כח": 28, "כט": 29, "ל": 30
}

HEBREW_MONTH_NAMES_TO_NUM = {v: k for k, v in HEBREW_MONTH_NAMES_FULL.items()}

HEBCAL_API_BASE_URL = "https://www.hebcal.com/converter"
UPCOMING_DAYS = 7

HEBREW_WEEKDAYS = {
    "Monday": "יום שני",
    "Tuesday": "יום שלישי",
    "Wednesday": "יום רביעי",
    "Thursday": "יום חמישי",
    "Friday": "יום שישי",
    "Saturday": "יום שבת",
    "Sunday": "יום ראשון",
}

HEBREW_EVENT_NAMES = {
    "BIRT": "יומולדת",
    "DEAT": "יאהרצייט",
    "MARR": "יום נישואין"
}

GOOGLE_DRIVE_FILE_ID = os.environ.get('GOOGLE_DRIVE_FILE_ID', '1ZPt2FeXPueje3P6WqXfs_3-gsxi_G154')
LOG_ALL_PATHS_DISTANCE_THRESHOLD = 6
INPUT_GEDCOM_FILE = "tree.ged"
FIXED_GEDCOM_FILE = "fixed_tree.ged"
OUTPUT_CSV_FILE = "dates.csv"
