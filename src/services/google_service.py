import os
import logging
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from src.config import settings

logger = logging.getLogger("lilo-hub")

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]


class GoogleService:
    def __init__(self, token_path: Optional[str] = None):
        self.token_path = self._resolve_path(token_path or settings.GOOGLE_TOKEN_PATH, "token.json")
        self._creds: Optional[Credentials] = None

    def _resolve_path(self, primary: str, fallback: str) -> Path:
        p = Path(primary)
        if p.exists():
            return p
        fb = Path(fallback)
        if fb.exists():
            return fb
        return p

    def get_credentials(self) -> Optional[Credentials]:
        if not self.token_path.exists():
            logger.warning(f"No se encontró archivo de token de Google en {self.token_path}")
            return None

        try:
            if not self._creds:
                self._creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

            if self._creds and self._creds.expired and self._creds.refresh_token:
                logger.info("Refrescando token OAuth expirado de Google...")
                self._creds.refresh(Request())
                with open(self.token_path, "w") as f:
                    f.write(self._creds.to_json())
                logger.info("Token de Google refrescado y persistido.")

            return self._creds
        except Exception as e:
            logger.error(f"Error cargando o refrescando credenciales de Google: {e}")
            return None

    def is_authenticated(self) -> bool:
        creds = self.get_credentials()
        return creds is not None and creds.valid

    def get_calendar_events(self, days: int = 1, max_results: int = 10) -> List[Dict[str, Any]]:
        creds = self.get_credentials()
        if not creds:
            return []

        try:
            service = build("calendar", "v3", credentials=creds, cache_discovery=False)
            now = datetime.datetime.now(datetime.timezone.utc)
            time_max = now + datetime.timedelta(days=days)

            events_result = service.events().list(
                calendarId="primary",
                timeMin=now.isoformat(),
                timeMax=time_max.isoformat(),
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            items = events_result.get("items", [])
            formatted = []
            for item in items:
                start = item.get("start", {})
                start_dt = start.get("dateTime") or start.get("date")
                formatted.append({
                    "id": item.get("id"),
                    "summary": item.get("summary", "Sin título"),
                    "start": start_dt,
                    "location": item.get("location", ""),
                    "description": item.get("description", ""),
                    "is_all_day": "dateTime" not in start,
                })
            return formatted
        except Exception as e:
            logger.error(f"Error consultando Google Calendar: {e}")
            return []

    def get_unread_emails(self, max_results: int = 5) -> List[Dict[str, Any]]:
        creds = self.get_credentials()
        if not creds:
            return []

        try:
            service = build("gmail", "v1", credentials=creds, cache_discovery=False)
            results = service.users().messages().list(
                userId="me",
                q="is:unread",
                maxResults=max_results
            ).execute()

            messages = results.get("messages", [])
            emails = []
            for msg in messages:
                detail = service.users().messages().get(
                    userId="me",
                    id=msg["id"],
                    format="metadata",
                    metadataHeaders=["From", "Subject", "Date"]
                ).execute()

                headers = {h["name"]: h["value"] for h in detail.get("payload", {}).get("headers", [])}
                emails.append({
                    "id": msg["id"],
                    "sender": headers.get("From", "Desconocido"),
                    "subject": headers.get("Subject", "Sin asunto"),
                    "date": headers.get("Date", ""),
                    "snippet": detail.get("snippet", ""),
                })
            return emails
        except Exception as e:
            logger.error(f"Error consultando Gmail: {e}")
            return []


google_service = GoogleService()
