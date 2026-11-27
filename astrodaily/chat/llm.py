"""Talking to the language model. ``GeminiClient`` uses the Gemini REST API; tests use a fake with the same shape."""
import logging
from dataclasses import dataclass
from typing import Protocol

log = logging.getLogger("astrodaily.chat")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class LlmError(Exception):
    """The model could not give an answer (network, quota, bad response). Never carries user text."""


@dataclass(frozen=True)
class Turn:
    role: str  # "user" or "assistant"
    text: str


@dataclass(frozen=True)
class LlmResult:
    text: str
    tokens_in: int | None = None
    tokens_out: int | None = None
    model: str | None = None


class LlmClient(Protocol):
    def generate(self, system: str, turns: list[Turn]) -> LlmResult: ...


class GeminiClient:
    def __init__(self, api_key: str, model: str, max_output_tokens: int = 600, timeout: int = 30, session=None):
        self.api_key, self.model = api_key, model
        self.max_output_tokens, self.timeout = max_output_tokens, timeout
        if session is None:
            import requests
            session = requests.Session()
        self._session = session

    def generate(self, system: str, turns: list[Turn]) -> LlmResult:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user" if t.role == "user" else "model", "parts": [{"text": t.text}]}
                         for t in turns],
            "generationConfig": {"maxOutputTokens": self.max_output_tokens, "temperature": 0.6},
        }
        try:  # the key goes in a header, never in the URL, so it cannot end up in logs
            r = self._session.post(GEMINI_URL.format(model=self.model), json=body, timeout=self.timeout,
                                   headers={"x-goog-api-key": self.api_key})
        except Exception as exc:
            log.warning("gemini request failed: %s", type(exc).__name__)
            raise LlmError("network") from None
        if r.status_code != 200:
            log.warning("gemini returned status %s", r.status_code)
            raise LlmError(f"status {r.status_code}")
        try:
            data = r.json()
            cand = data["candidates"][0]
            text = "".join(p.get("text", "") for p in cand["content"]["parts"]).strip()
        except (ValueError, KeyError, IndexError, TypeError):
            raise LlmError("blocked or empty") from None
        if not text:
            raise LlmError("empty")
        usage = data.get("usageMetadata") or {}
        return LlmResult(text=text, tokens_in=usage.get("promptTokenCount"),
                         tokens_out=usage.get("candidatesTokenCount"), model=self.model)
