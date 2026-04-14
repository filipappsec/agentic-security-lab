import base64

from gmail_auth import authenticate
from googleapiclient.discovery import build
from email.mime.text import MIMEText


def main():
    creds = authenticate()
    service = build("gmail", "v1", credentials=creds)

    # Read recent emails
    print("Recent emails:")
    results = service.users().messages().list(
        userId="me", maxResults=5
    ).execute()

    messages = results.get("messages", [])
    for msg in messages:
        detail = service.users().messages().get(
            userId="me", id=msg["id"], format="metadata",
            metadataHeaders=["From", "Subject"]
        ).execute()

        headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
        print(f"  From: {headers.get('From', 'unknown')}")
        print(f"  Subject: {headers.get('Subject', 'no subject')}")
        print()

    # Send test email to self
    my_email = service.users().getProfile(userId="me").execute()["emailAddress"]
    print(f"Sending test email to: {my_email}")

    message = MIMEText("Test email from AgentAI Lab.")
    message["to"] = my_email
    message["subject"] = "[AgentAI-Lab] Test Email"

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()

    print("Email sent.")


if __name__ == "__main__":
    main()
