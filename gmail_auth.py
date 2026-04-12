import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send'
]

def authenticate():
    creds = None
    
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES
            )
            # Uruchom na porcie 8090 — będziemy tunelować
            creds = flow.run_local_server(
                host='0.0.0.0',
                port=8090,
                open_browser=False
            )
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            print("✅ Token saved to token.json!")
    
    return creds

if __name__ == '__main__':
    creds = authenticate()
    print(f"✅ Authenticated! Token valid: {creds.valid}")
