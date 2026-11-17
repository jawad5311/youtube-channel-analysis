"""Authorize a local Google Sheets connection for later workflows."""
from __future__ import annotations

import argparse
from pathlib import Path

from google.auth.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CREDENTIALS_PATH = PROJECT_ROOT / "config" / "google-oauth-client.json"
DEFAULT_TOKEN_PATH = PROJECT_ROOT / "config" / "google-sheets-token.json"


def authorize(
    credentials_path: Path = DEFAULT_CREDENTIALS_PATH,
    token_path: Path = DEFAULT_TOKEN_PATH,
) -> Credentials:
    """Load or create OAuth credentials for the Google Sheets API."""
    credentials_path = credentials_path.expanduser().resolve()
    token_path = token_path.expanduser().resolve()
    if not credentials_path.is_file():
        raise FileNotFoundError(
            f"Google OAuth credentials file not found: {credentials_path}"
        )

    credentials: Credentials | None = None
    if token_path.is_file():
        from google.oauth2.credentials import Credentials as UserCredentials

        credentials = UserCredentials.from_authorized_user_file(
            str(token_path), SCOPES
        )

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(credentials_path), SCOPES
            )
            credentials = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(credentials.to_json(), encoding="utf-8")

    return credentials


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Authorize Google Sheets access for this project."
    )
    parser.add_argument("--credentials", type=Path, default=DEFAULT_CREDENTIALS_PATH)
    parser.add_argument("--token", type=Path, default=DEFAULT_TOKEN_PATH)
    args = parser.parse_args()
    authorize(args.credentials, args.token)
    print("Google Sheets authorization completed successfully.")
    print(f"Token saved to: {args.token.expanduser().resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
