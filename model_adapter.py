"""Small Gemini text adapter. A local .env or process environment supplies the key."""

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ModelUnavailable(RuntimeError):
    """The model could not produce usable text."""


def _api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    env_path = Path(__file__).with_name(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            name, separator, value = line.partition("=")
            if separator and name.strip() == "GEMINI_API_KEY":
                return value.strip().strip('"\'')
    return ""


def generate_text(prompt: str, *, temperature: float = 0.7) -> str:
    """Send one prompt to Gemini and return the first text candidate."""
    key = _api_key()
    if not key or key.lower().startswith("your_"):
        raise ModelUnavailable("GEMINI_API_KEY is missing")
    model = os.environ.get("FITFINDR_MODEL", "gemini-3.5-flash-lite")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature, "maxOutputTokens": 500},
    }
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    try:
        with urlopen(request, timeout=25) as response:
            body = json.load(response)
        parts = body["candidates"][0]["content"]["parts"]
        result = "".join(part.get("text", "") for part in parts).strip()
        if not result:
            raise ModelUnavailable("The model returned no text")
        return result
    except (HTTPError, URLError, OSError, ValueError, KeyError, IndexError) as exc:
        raise ModelUnavailable("The model service is unavailable") from exc
