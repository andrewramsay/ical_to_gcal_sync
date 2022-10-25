import os

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

def auth_with_calendar_api(config):

    # this file stores your access and refresh tokens, and is
    # created automatically when the auth flow succeeeds for 
    # the first time. 
    creds = None
    if os.path.exists(config['CREDENTIAL_PATH']):
        try:
            creds = Credentials.from_authorized_user_file(config['CREDENTIAL_PATH'], config['SCOPES'])
        except Exception as e:
            os.unlink(config['CREDENTIAL_PATH'])

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(config['CLIENT_SECRET_FILE'],
                                                             [config['SCOPES']])
            creds = flow.run_local_server(port=0)

        # save credentials if successful
        with open(config['CREDENTIAL_PATH'], 'w') as token:
            token.write(creds.to_json())

    service = build('calendar', 'v3', credentials=creds)
    return service

