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

## Development / פיתוח

### English
To run the script locally:
1. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Set environment variables**:
   ```bash
   export PERSONID="@I1@"
   export DISTANCE_THRESHOLD=8
   ```
4. **Run the script**:
   ```bash
   python3 -m family_tree_notifier.main --lang en
   ```

### עברית
להרצת הסקריפט באופן מקומי:
1. **צרו סביבה וירטואלית**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
2. **התקינו תלויות**:
   ```bash
   pip install -r requirements.txt
   ```
3. **הגדירו משתני סביבה**:
   ```bash
   export PERSONID="@I1@"
   export DISTANCE_THRESHOLD=8
   ```
4. **הריצו את הסקריפט**:
   ```bash
   python3 -m family_tree_notifier.main --lang he
   ```

## Architecture Overview / סקירת ארכיטקטורה

### English
The application follows a modular architecture:
- `main.py`: Orchestrator of the workflow.
- `google_drive_utils.py`: Google Drive API interactions.
- `gedcom_utils.py`: Cleaning and parsing of GEDCOM files.
- `gedcom_graph.py`: Family tree graph and distance calculations.
- `hebcal_api.py`: Hebrew date conversions and Parasha info.
- `localization.py`: Multi-language support (HE/EN).
- `issue_generator.py`: Formatting the GitHub issue.

### עברית
האפליקציה בנויה בצורה מודולרית:
- `main.py`: המנצח על זרימת העבודה.
- `google_drive_utils.py`: אינטראקציה עם Google Drive API.
- `gedcom_utils.py`: ניקוי ופענוח קובצי GEDCOM.
- `gedcom_graph.py`: בניית גרף עץ משפחה וחישוב מרחקים.
- `hebcal_api.py`: המרת תאריכים עבריים ומידע על פרשת השבוע.
- `localization.py`: תמיכה בריבוי שפות (עברית/אנגלית).
- `issue_generator.py`: עיצוב ה-GitHub Issue.

## Testing / בדיקות

### English
To run the project tests, use the following command from the root:
```bash
python3 -m unittest discover tests
```

### עברית
כדי להריץ את הבדיקות של הפרויקט מהתיקייה הראשית, השתמשו בפקודה הבאה:
```bash
python3 -m unittest discover tests
```

## Example File / קובץ דוגמה

### English
A clean example GEDCOM file is provided as `examples/example.ged` to demonstrate the supported Hebrew date format (`@#DHEBREW@`) and basic family tree structure.

### עברית
קובץ GEDCOM נקי לדוגמה (`examples/example.ged`) זמין בריפו כדי להדגים את פורמט התאריכים העבריים הנתמך (`@#DHEBREW@`) ומבנה בסיסי של עץ משפחה.

## License

This project is licensed under the MIT License.
