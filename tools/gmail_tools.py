
    if _email_sent_count >= _max_emails:
        logger.warning("Rate limit reached: %d/%d", _email_sent_count, _max_emails)
        return f"BLOCKED: Rate limit exceeded ({_max_emails} emails/hour)."

    if _allowed_recipients and to not in _allowed_recipients:
        logger.warning("Blocked send to unauthorized recipient: %s", to)
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
