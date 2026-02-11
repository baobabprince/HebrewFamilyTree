# Family Tree Event Notifier

This project processes a GEDCOM file to find upcoming Hebrew-date based events (birthdays, anniversaries, yahrzeits), builds a family tree graph to calculate relationships, and generates a GitHub issue with the findings.

זהו פרויקט המעבד קובץ GEDCOM, מוצא תאריכים עבריים חשובים (ימי הולדת, ימי נישואין ויארצייטים), בונה גרף משפחתי לחישוב קרבה משפחתית, ויוצר issue ב-GitHub עם הממצאים.

## Setup / הגדרה

### English
1. **Clone the repository.**
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Google API Credentials**:
   - Enable the Google Drive API in your Google Cloud Console.
   - Create a service account and download its JSON key.
   - Share your GEDCOM file in Google Drive with the service account's email.
   - Set the content of the JSON key as a GitHub Secret named `GOOGLE_CREDENTIALS_JSON`.
   - Set the Google Drive file ID of your GEDCOM file as a secret named `GOOGLE_DRIVE_FILE_ID`.

### עברית
1. **שכפלו את המאגר (clone).**
2. **התקינו את התלויות**:
   ```bash
   pip install -r requirements.txt
   ```
3. **הגדירו גישה ל-Google API**:
   - הפעילו את Google Drive API ב-Google Cloud Console.
   - צרו חשבון שירות (service account) והורידו את מפתח ה-JSON שלו.
   - שתפו את קובץ ה-GEDCOM שלכם ב-Google Drive עם כתובת המייל של חשבון השירות.
   - הגדירו את תוכן קובץ ה-JSON כ-GitHub Secret בשם `GOOGLE_CREDENTIALS_JSON`.
   - הגדירו את מזהה הקובץ של ה-GEDCOM שלכם מ-Google Drive כ-Secret בשם `GOOGLE_DRIVE_FILE_ID`.

## Usage / שימוש

### English
The script is designed to be run automatically via GitHub Actions. You can also trigger it manually:
1. Go to the **Actions** tab in your GitHub repository.
2. Select the **"Check Google Drive GEDCOM File for Updates and Process"** workflow.
3. Click **"Run workflow"** and provide the `person_id` (the central person's GEDCOM ID) and an optional `distance_threshold`.

### עברית
הסקריפט מיועד לרוץ באופן אוטומטי דרך GitHub Actions. ניתן להפעיל אותו גם ידנית:
1. עברו ללשונית **Actions** במאגר ה-GitHub שלכם.
2. בחרו את ה-workflow בשם **"Check Google Drive GEDCOM File for Updates and Process"**.
3. לחצו על **"Run workflow"** וספקו את ה-`person_id` (מזהה ה-GEDCOM של האדם המרכזי) ואת `distance_threshold` (אופציונלי).

## Architecture Overview / סקירת ארכיטקטורה

### English
1. **Download**: GEDCOM from Google Drive.
2. **Clean & Parse**: Normalize GEDCOM and extract events.
3. **Date Filtering**: Fetch upcoming Hebrew dates from Hebcal API.
4. **Graph Construction**: Build family tree graph using `networkx`.
5. **Distance Calculation**: Compute genealogical distance from `PERSONID`.
6. **Issue Generation**: Create Markdown for GitHub issue.

### עברית
1. **הורדה**: הורדת קובץ ה-GEDCOM מ-Google Drive.
2. **ניקוי ופענוח**: נירמול הקובץ וחילוץ אירועים.
3. **סינון תאריכים**: קבלת תאריכים עבריים קרובים מ-Hebcal API.
4. **בניית גרף**: בניית עץ משפחה כגרף באמצעות `networkx`.
5. **חישוב מרחק**: חישוב קרבה משפחתית מ-`PERSONID`.
6. **יצירת Issue**: יצירת תוכן בפורמט Markdown עבור ה-Issue ב-GitHub.

## Testing / בדיקות

### English
To run the project tests, use the following command:
```bash
python3 -m unittest discover family_tree_notifier/tests
```

### עברית
כדי להריץ את הבדיקות של הפרויקט, השתמשו בפקודה הבאה:
```bash
python3 -m unittest discover family_tree_notifier/tests
```

## Example File / קובץ דוגמה

### English
A clean example GEDCOM file is provided as `examples/example.ged` to demonstrate the supported Hebrew date format (`@#DHEBREW@`) and basic family tree structure.

### עברית
קובץ GEDCOM נקי לדוגמה (`examples/example.ged`) זמין בריפו כדי להדגים את פורמט התאריכים העבריים הנתמך (`@#DHEBREW@`) ומבנה בסיסי של עץ משפחה.

## License

This project is licensed under the MIT License.
