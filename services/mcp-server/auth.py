"""
Run this script ONCE locally (not in Docker) to authenticate with Gmail
and generate config/token.json.

    python services/mcp-server/auth.py

The token is saved to config/token.json and will be picked up by Docker
via the volume mount ./config:/app/config.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).parent
_CONFIG = _ROOT / "config"

load_dotenv(_CONFIG / ".env")

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]

credentials_file = os.getenv(
    "GMAIL_CREDENTIALS_FILE",
    str(_CONFIG / "credentials.json"),
)
token_file = _CONFIG / "token.json"

if not Path(credentials_file).exists():
    print(f"ERROR: credentials file not found: {credentials_file}")
    print("Download it from Google Cloud Console → APIs & Services → Credentials.")
    sys.exit(1)

flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
creds = flow.run_local_server(port=0)

token_file.write_text(creds.to_json())
print(f"Token saved to {token_file}")
print("You can now start Docker: docker compose up")
