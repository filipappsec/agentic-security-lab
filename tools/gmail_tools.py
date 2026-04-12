import os
import sys
import base64
import logging

from langchain_core.tools import tool
from googleapiclient.discovery import build
from email.mime.text import MIMEText

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gmail_auth import authenticate

logger = logging.getLogger(__name__)

_email_sent_count = 0
_max_emails = int(os.getenv("MAX_EMAILS_PER_HOUR", 10))
_allowed_recipients = [
    r.strip() for r in os.getenv("ALLOWED_RECIPIENTS", "").split(",") if r.strip()
]


def _get_service():
    creds = authenticate()
    return build("gmail", "v1", credentials=creds)


def _extract_body(payload):
    """Extract plain text body from gmail message payload."""
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain" and "data" in part.get("body", {}):
                return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
    elif "body" in payload and "data" in payload["body"]:
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
    return ""


@tool
def read_emails(max_results: int = 5) -> str:
    """Read recent emails from inbox."""
    service = _get_service()
    results = service.users().messages().list(
        userId="me", maxResults=max_results, labelIds=["INBOX"]
    ).execute()

    messages = results.get("messages", [])
    if not messages:
        return "No messages in inbox."

    output = []
    for msg in messages:
        detail = service.users().messages().get(
            userId="me", id=msg["id"], format="full"
        ).execute()

        headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
        body = _extract_body(detail["payload"])

        output.append(
            f"From: {headers.get('From', 'unknown')}\n"
            f"Subject: {headers.get('Subject', 'no subject')}\n"
            f"Date: {headers.get('Date', 'unknown')}\n"
            f"Body: {body[:500]}\n"
            f"---"
        )

    return "\n".join(output)


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email. Args: to (recipient), subject, body."""
    global _email_sent_count

    if _email_sent_count >= _max_emails:
        logger.warning("Rate limit reached: %d/%d", _email_sent_count, _max_emails)
        return f"BLOCKED: Rate limit exceeded ({_max_emails} emails/hour)."

    if _allowed_recipients and to not in _allowed_recipients:
        logger.warning("Blocked send attempt to unauthorized recipient: %s", to)
        return f"BLOCKED: Recipient {to} is not on the allowed list."

    service = _get_service()

    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    try:
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        _email_sent_count += 1
        logger.info("Email sent to %s (%d/%d)", to, _email_sent_count, _max_emails)
        return f"Email sent to {to}. ({_email_sent_count}/{_max_emails})"
    except Exception as e:
        logger.error("Failed to send email: %s", str(e))
        return f"Error sending email: {str(e)}"


@tool
def search_emails(query: str, max_results: int = 5) -> str:
    """Search emails using Gmail search syntax (e.g. 'from:someone', 'subject:topic')."""
    service = _get_service()
    results = service.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    if not messages:
        return f"No emails matching: {query}"

    output = [f"Found {len(messages)} result(s):"]
    for msg in messages:
        detail = service.users().messages().get(
            userId="me", id=msg["id"], format="metadata",
            metadataHeaders=["From", "Subject", "Date"]
        ).execute()
        headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
        output.append(
            f"- {headers.get('Subject', 'no subject')} | {headers.get('From', 'unknown')}"
        )

    return "\n".join(output)
