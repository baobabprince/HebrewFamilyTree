# Family Tree Event Notifier

This project processes a GEDCOM file to find upcoming Hebrew-date based events (birthdays, anniversaries, yahrzeits), builds a family tree graph to calculate relationships, and generates a GitHub issue with the findings.

זהו פרויקט המעבד קובץ GEDCOM, מוצא תאריכים עבריים חשובים (ימי הולדת, ימי נישואין ויארצייטים), בונה גרף משפחתי לחישוב קרבה משפחתית, ויוצר issue ב-GitHub עם הממצאים.

## Setup

### English

1.  **Clone the repository.**
2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Google API Credentials**:
    - Enable the Google Drive API in your Google Cloud Console.
    - Create a service account and download its JSON key.
    - Share your GEDCOM file in Google Drive with the service account's email.
    - Set the content of the JSON key as a GitHub Secret named `GOOGLE_CREDENTIALS_JSON`.
    - Set the Google Drive file ID of your GEDCOM file as a secret named `GOOGLE_DRIVE_FILE_ID`.

---

### עברית

1.  **שכפלו את המאגר (clone).**
2.  **התקינו את התלויות**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **הגדירו גישה ל-Google API**:
    - הפעילו את Google Drive API ב-Google Cloud Console.
    - צרו חשבון שירות (service account) והורידו את מפתח ה-JSON שלו.
    - שתפו את קובץ ה-GEDCOM שלכם ב-Google Drive עם כתובת המייל של חשבון השירות.
    - הגדירו את תוכן קובץ ה-JSON כ-GitHub Secret בשם `GOOGLE_CREDENTIALS_JSON`.
    - הגדירו את מזהה הקובץ של ה-GEDCOM שלכם מ-Google Drive כ-Secret בשם `GOOGLE_DRIVE_FILE_ID`.

## Usage

### English

The script is designed to be run automatically via GitHub Actions. You can also trigger it manually:

1.  Go to the **Actions** tab in your GitHub repository.
2.  Select the **"Check Google Drive GEDCOM File for Updates and Process"** workflow.
3.  Click **"Run workflow"** and provide the `person_id` (the central person's GEDCOM ID) and an optional `distance_threshold`.

Upon completion, a GitHub issue will be created with the upcoming events.

---

### עברית

הסקריפט מיועד לרוץ באופן אוטומטי דרך GitHub Actions. ניתן להפעיל אותו גם ידנית:

1.  עברו ללשונית **Actions** במאגר ה-GitHub שלכם.
2.  בחרו את ה-workflow בשם **"Check Google Drive GEDCOM File for Updates and Process"**.
3.  לחצו על **"Run workflow"** וספקו את ה-`person_id` (מזהה ה-GEDCOM של האדם המרכזי) ואת `distance_threshold` (אופציונלי).

בסיום הריצה, ייווצר issue חדש ב-GitHub עם התאריכים הקרובים.

## Testing / בדיקות

### English

To run the project tests, use the following command:
```bash
python3 -m unittest discover tests
```

---

### עברית

כדי להריץ את הבדיקות של הפרויקט, השתמשו בפקודה הבאה:
```bash
python3 -m unittest discover tests
```

## License

This project is licensed under the MIT License.

פרויקט זה מופץ תחת רישיון MIT.
