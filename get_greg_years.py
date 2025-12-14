import logging
logging.basicConfig(level=logging.DEBUG)

from hebcal_api import get_gregorian_date_from_hebrew_api
from constants import HEBREW_MONTHS_MAP

# 1. @#DHEBREW@ 15 KISLEV 5785
hebrew_year_1 = 5785
hebrew_month_num_1 = HEBREW_MONTHS_MAP["KSL"]
hebrew_day_1 = 15
gregorian_year_1 = get_gregorian_date_from_hebrew_api(hebrew_year_1, hebrew_month_num_1, hebrew_day_1)
print(f"15 KISLEV 5785 -> Gregorian Year: {gregorian_year_1}")

# 2. @#DHEBREW@ ADAR I 5785 (day defaults to 1)
hebrew_year_2 = 5785
hebrew_month_num_2 = HEBREW_MONTHS_MAP["ADAR I"]
hebrew_day_2 = 1
gregorian_year_2 = get_gregorian_date_from_hebrew_api(hebrew_year_2, hebrew_month_num_2, hebrew_day_2)
print(f"ADAR I 5785 (day 1) -> Gregorian Year: {gregorian_year_2}")

# 3. @#DHEBREW@ 10 SIVAN AND 11 TAMMUZ 5780 (only first part is processed, so 10 SIVAN 5780)
hebrew_year_3 = 5780
hebrew_month_num_3 = HEBREW_MONTHS_MAP["SVN"]
hebrew_day_3 = 10
gregorian_year_3 = get_gregorian_date_from_hebrew_api(hebrew_year_3, hebrew_month_num_3, hebrew_day_3)
print(f"10 SIVAN 5780 -> Gregorian Year: {gregorian_year_3}")

# 4. @#DHEBREW@ ABT 10 SIVAN 5780 (approximate, but still 10 SIVAN 5780)
# Same as above
print(f"ABT 10 SIVAN 5780 -> Gregorian Year: {gregorian_year_3}")
