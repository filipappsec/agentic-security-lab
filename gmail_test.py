from gmail_auth import authenticate
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64

creds = authenticate()
service = build('gmail', 'v1', credentials=creds)

# === TEST 1: Odczytaj maile ===
print("\n📨 Ostatnie 5 maili:")
results = service.users().messages().list(
    userId='me', maxResults=5
).execute()

messages = results.get('messages', [])
for msg in messages:
    detail = service.users().messages().get(
        userId='me', id=msg['id'], format='metadata',
        metadataHeaders=['From', 'Subject']
    ).execute()
    
    headers = {h['name']: h['value'] for h in detail['payload']['headers']}
    print(f"  From: {headers.get('From', '?')}")
    print(f"  Subject: {headers.get('Subject', '?')}")
    print()

# === TEST 2: Wyślij testowy mail (do siebie) ===
my_email = service.users().getProfile(userId='me').execute()['emailAddress']
print(f"📤 Wysyłam test do: {my_email}")

message = MIMEText("🤖 Hello from AgentAI Lab! This is a test email.")
message['to'] = my_email
message['subject'] = '[AgentAI-Lab] Test Email'

raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
service.users().messages().send(
    userId='me', body={'raw': raw}
).execute()

print("✅ Mail wysłany! Sprawdź inbox testowego Gmaila.")
