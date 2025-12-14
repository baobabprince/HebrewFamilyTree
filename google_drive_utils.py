import os
import io
import json
import logging
import shutil
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_drive_service():
    """
    Authenticates with the Google Drive API and returns a service object.

    This function handles multiple authentication methods:
    1.  It first checks for a local `token.json` file, which is created
        after the first successful user authentication flow.
    2.  If `token.json` is not found or the credentials have expired, it
        attempts to use service account credentials from the
        `GOOGLE_APPLICATION_CREDENTIALS` environment variable.
    3.  If neither method is successful, it returns None.

    Returns:
        googleapiclient.discovery.Resource: The authenticated Google Drive
                                            service object, or None if
                                            authentication fails.
    """
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            credentials_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
            if credentials_json:
                try:
                    credentials_info = json.loads(credentials_json)
                    creds = service_account.Credentials.from_service_account_info(credentials_info, scopes=SCOPES)
                except Exception as e:
                    logging.error(f"Error loading credentials from GOOGLE_APPLICATION_CREDENTIALS: {e}")
                    return None
            else:
                logging.info("GOOGLE_APPLICATION_CREDENTIALS not set. Falling back to local file.")
                return None
    
    try:
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        logging.error(f"Error building Drive service: {e}")
        return None

def download_gedcom_from_drive(file_id, destination_path):
    """
    Downloads a GEDCOM file from Google Drive to a specified local path.

    This function uses the authenticated Google Drive service to download a file
    by its ID. If the download fails or if the service is unavailable, it
    provides a fallback mechanism to use a local `tree.ged` file if it exists.

    Args:
        file_id (str): The ID of the file to download from Google Drive.
        destination_path (str): The local file path where the downloaded
                                content will be saved.

    Returns:
        bool: True if the file was successfully downloaded or the local
              fallback was used, False otherwise.

    Raises:
        HttpError: An error from the Google Drive API, which is caught and
                   logged within the function.
    """
    service = get_drive_service()
    if not service:
        if os.path.exists('tree.ged'):
            if os.path.abspath('tree.ged') != os.path.abspath(destination_path):
                shutil.copy('tree.ged', destination_path)
            logging.info("Using local GEDCOM file: tree.ged")
            return True
        else:
            logging.error("Local GEDCOM file 'tree.ged' not found.")
            return False

    try:
        request = service.files().get_media(fileId=file_id)
        fh = io.FileIO(destination_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            logging.info(f"Download {int(status.progress() * 100)}%.")
        logging.info(f"Successfully downloaded {destination_path} from Google Drive.")
        return True
    except HttpError as error:
        logging.error(f"Error downloading GEDCOM file from Google Drive: {error}")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred during download: {e}")
        return False
