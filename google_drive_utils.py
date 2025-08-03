import os
import io
import json
import logging
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def get_drive_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
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
                logging.error("GOOGLE_APPLICATION_CREDENTIALS environment variable not set and token.json not found.")
                return None
    
    try:
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        logging.error(f"Error building Drive service: {e}")
        return None

def download_gedcom_from_drive(file_id, destination_path):
    """
    Downloads a file from Google Drive.
    """
    service = get_drive_service()
    if not service:
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
