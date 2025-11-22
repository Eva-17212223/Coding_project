# gmail_service.py
"""
Gmail API email sender using OAuth2.
Automatically handles:
- Authentication
- Token refresh
- Creation of token.json
- Sending real emails via Gmail API v1

Requires:
- credentials.json (OAuth client)
- token.json (generated automatically)
"""

from __future__ import print_function
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from pathlib import Path
from config import GOOGLE_CREDENTIALS_PATH, GOOGLE_TOKEN_PATH, SENDER_EMAIL


# ---------------------------------------------
# Gmail scopes (send email)
# ---------------------------------------------
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


# ---------------------------------------------
# Load / create credentials
# ---------------------------------------------
def get_gmail_service():
    """
    Returns a Gmail API service object.
    Handles OAuth2 login, token refresh, token saving.
    """
    creds = None

    # If token.json already exists, load it
    if GOOGLE_TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(GOOGLE_TOKEN_PATH), SCOPES)

    # If no valid credentials -> login flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # refresh automatically
            creds.refresh(Request())
        else:
            # First time: do OAuth login
            flow = InstalledAppFlow.from_client_secrets_file(
                str(GOOGLE_CREDENTIALS_PATH),
                SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save the token
        with open(GOOGLE_TOKEN_PATH, "w") as token:
            token.write(creds.to_json())

    # Build Gmail service
    service = build("gmail", "v1", credentials=creds)
    return service


# ---------------------------------------------
# Send email
# ---------------------------------------------
def send_email(to_email: str, subject: str, message_text: str) -> bool:
    """
    Sends a real email using Gmail API.
    Returns True if sent, False otherwise.
    """
    try:
        service = get_gmail_service()

        # MIME email structure
        message = MIMEMultipart()
        message["to"] = to_email
        message["from"] = SENDER_EMAIL
        message["subject"] = subject

        message.attach(MIMEText(message_text, "plain"))

        # Encode message base64
        raw_message = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode("utf-8")

        body = {"raw": raw_message}

        # Gmail API call
        service.users().messages().send(
            userId="me", body=body
        ).execute()

        return True

    except Exception as e:
        print(f"[ERROR Gmail] Could not send email: {e}")
        return False
