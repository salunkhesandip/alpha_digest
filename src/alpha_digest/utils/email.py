"""Email utilities for sending Alpha Digest summaries via Gmail OAuth."""

import base64
import os
from datetime import datetime
from email.mime.audio import MIMEAudio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def _authorize_gmail(credentials_file: str) -> Credentials:
    """Authorize Gmail access and return user credentials."""
    flow = InstalledAppFlow.from_client_secrets_file(credentials_file, GMAIL_SCOPES)
    oauth_flow = os.getenv("GMAIL_OAUTH_FLOW", "local").strip().lower()

    if oauth_flow == "manual":
        return flow.run_local_server(
            host="127.0.0.1",
            port=0,
            open_browser=False,
            authorization_prompt_message="Open this URL in your browser:\n{url}",
            success_message="Authentication complete. You can close this tab.",
        )

    try:
        return flow.run_local_server(
            host="127.0.0.1",
            port=0,
            open_browser=True,
            success_message="Authentication complete. You can close this tab.",
        )
    except Exception:
        return flow.run_local_server(
            host="127.0.0.1",
            port=0,
            open_browser=False,
            authorization_prompt_message="Automatic browser open failed. Use this URL:\n{url}",
            success_message="Authentication complete. You can close this tab.",
        )


def _write_token(token_file: str, creds: Credentials) -> None:
    """Persist the Gmail token to disk."""
    with open(token_file, "w", encoding="utf-8") as file:
        file.write(creds.to_json())


def _refresh_credentials(creds: Credentials, token_file: str) -> Credentials | None:
    """Attempt to refresh expired credentials, otherwise remove the stale token."""
    try:
        creds.refresh(Request())
        return creds
    except RefreshError:
        if os.path.exists(token_file):
            os.remove(token_file)
        return None


def send_summary_email_oauth(
    summary: str, tickers: str = "", audio_path: str | None = None
) -> str:
    """Send summary email using Gmail OAuth.

    Args:
        summary: Generated summary text
        tickers: Ticker symbols for the subject line
        audio_path: Optional path to an MP3 audio file to attach

    Returns:
        Email status: sent or skipped
    """
    if os.getenv("GMAIL_OAUTH_ENABLED", "false").lower() != "true":
        return "skipped: GMAIL_OAUTH_ENABLED is not true"

    to_email = os.getenv("SUMMARY_EMAIL_TO", "")
    if not to_email:
        raise ValueError("SUMMARY_EMAIL_TO is required when GMAIL_OAUTH_ENABLED=true")

    credentials_file = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")
    token_file = os.getenv("GMAIL_TOKEN_FILE", "token.json")

    if not os.path.exists(credentials_file):
        raise FileNotFoundError(
            f"Gmail OAuth credentials file not found: {credentials_file}"
        )

    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, GMAIL_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds = _refresh_credentials(creds, token_file)

        if not creds or not creds.valid:
            creds = _authorize_gmail(credentials_file)

        _write_token(token_file, creds)

    service = build("gmail", "v1", credentials=creds)

    date_str = datetime.now().strftime("%m/%d/%Y")

    if audio_path and os.path.exists(audio_path):
        message = MIMEMultipart()
        message.attach(MIMEText(summary, "plain", "utf-8"))
        with open(audio_path, "rb") as f:
            audio_part = MIMEAudio(f.read(), _subtype="mpeg")
        audio_filename = f"alpha_digest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
        audio_part.add_header(
            "Content-Disposition", "attachment", filename=audio_filename
        )
        message.attach(audio_part)
    else:
        message = MIMEText(summary, "plain", "utf-8")

    message["to"] = to_email
    message["subject"] = f"Alpha Digest - {date_str}"

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    service.users().messages().send(userId="me", body={"raw": raw_message}).execute()
    return "sent"
