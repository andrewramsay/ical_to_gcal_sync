import os
import pickle

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

def auth_with_calendar_api(config):
    creds = None

    # this file stores your access and refresh tokens, and is
    # created automatically when the auth flow succeeeds for 
    # the first time. 
    if os.path.exists(config['CREDENTIAL_PATH']):
        # if credentials file fails to load (e.g. because it's the old
        # style JSON content instead), just delete it
        try:
            with open(config['CREDENTIAL_PATH'], 'rb') as token:
                creds = pickle.load(token)
        except Exception as err:
            os.unlink(config['CREDENTIAL_PATH'])

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(config['CLIENT_SECRET_FILE'],
                                                             [config['SCOPES']])
            creds = flow.run_console() # or run_local_server(port=0)

        # save credentials if successful
        with open(config['CREDENTIAL_PATH'], 'wb') as token:
            pickle.dump(creds, token)

    service = build('calendar', 'v3', credentials=creds)

    return service

