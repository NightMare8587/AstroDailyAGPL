"""Sending one push message. ``FcmSender`` talks to Firebase Cloud Messaging (HTTP v1); ``LogSender`` is the
stand-in used when no credentials are configured, so the whole pipeline can run without sending anything."""
import json
import logging
from dataclasses import dataclass
from typing import Literal, Protocol

log = logging.getLogger("astrodaily.notify")

Outcome = Literal["ok", "dead_token", "retry", "error"]
SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]


@dataclass(frozen=True)
class Push:
    title: str
    body: str
    data: dict[str, str]


class Sender(Protocol):
    name: str

    def send(self, token: str, push: Push) -> Outcome: ...


class LogSender:
    """Records nothing about the user: only that a message would have gone out."""
    name = "log"

    def send(self, token: str, push: Push) -> Outcome:
        log.info("notify (not sent, no FCM credentials): %d chars", len(push.title) + len(push.body))
        return "ok"


class FcmSender:
    name = "fcm"

    def __init__(self, service_account_json: str, session=None, credentials=None):
        info = json.loads(service_account_json)
        self.project_id = info["project_id"]
        self._creds = credentials
        if self._creds is None:
            from google.oauth2 import service_account
            self._creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        if session is None:
            import requests
            session = requests.Session()
        self._session = session

    def _bearer(self) -> str:
        if not self._creds.valid:
            from google.auth.transport.requests import Request
            self._creds.refresh(Request())
        return self._creds.token

    def send(self, token: str, push: Push) -> Outcome:
        body = {"message": {
            "token": token,
            "notification": {"title": push.title, "body": push.body},
            "data": push.data,
            "android": {"priority": "high", "notification": {"channel_id": "daily"}},
        }}
        try:
            r = self._session.post(
                f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send",
                headers={"Authorization": f"Bearer {self._bearer()}"}, json=body, timeout=10)
        except Exception as exc:  # network trouble, auth refresh trouble: try again next run
            log.warning("fcm request failed: %s", type(exc).__name__)
            return "retry"
        if r.status_code == 200:
            return "ok"
        try:
            err = r.json().get("error", {})
        except ValueError:
            err = {}
        code = next((d.get("errorCode") for d in err.get("details", []) if isinstance(d, dict)
                     and d.get("errorCode")), err.get("status"))
        if r.status_code == 404 or code in ("UNREGISTERED", "SENDER_ID_MISMATCH"):
            return "dead_token"
        if r.status_code in (429, 500, 502, 503, 504) or code in ("UNAVAILABLE", "INTERNAL", "QUOTA_EXCEEDED"):
            return "retry"
        log.warning("fcm rejected a message: status %s code %s", r.status_code, code)
        return "error"


def make_sender(service_account_json: str | None) -> Sender:
    return FcmSender(service_account_json) if service_account_json else LogSender()
