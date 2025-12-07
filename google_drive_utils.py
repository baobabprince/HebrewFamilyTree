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
