from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Callable, Any

PostJson = Callable[[str, dict[str, Any], float], dict[str, Any]]


def build_cleanup_prompt(text: str, mode: str = "punctuate") -> str:
    mode_text = {
        "punctuate": "Add punctuation, capitalization, and paragraph breaks where they are clearly implied.",
        "format": "Clean up formatting while preserving meaning.",
        "command": "Rewrite the dictated command into concise executable text while preserving intent.",
    }.get(mode, "Clean up punctuation and capitalization while preserving meaning.")
    return (
        "You are formatting local speech-to-text dictation.\n"
        f"{mode_text}\n"
        "Do not add new facts. Do not explain. Return only the final text.\n\n"
        f"Dictation:\n{text}"
    )


def post_json(endpoint: str, payload: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8")
    return json.loads(body)


def cleanup_text(
    text: str,
    cleanup_settings: dict,
    *,
    logger: logging.Logger | None = None,
    post_func: PostJson | None = None,
) -> str:
    if not text.strip():
        return text
    if not cleanup_settings.get("enabled", False):
        return text

    log = logger or logging.getLogger(__name__)
    provider = cleanup_settings.get("provider", "ollama")
    if provider != "ollama":
        log.warning("Unsupported cleanup provider %s; using raw transcript.", provider)
        return text

    endpoint = cleanup_settings.get("endpoint", "http://localhost:11434/api/generate")
    timeout = float(cleanup_settings.get("timeout_seconds", 20))
    payload = {
        "model": cleanup_settings.get("model", "gemma3:1b"),
        "prompt": build_cleanup_prompt(text, cleanup_settings.get("mode", "punctuate")),
        "stream": False,
        "options": {"temperature": 0},
    }

    try:
        result = (post_func or post_json)(endpoint, payload, timeout)
    except (OSError, TimeoutError, urllib.error.URLError, json.JSONDecodeError) as exc:
        log.warning("Ollama cleanup failed; using raw transcript: %s", exc)
        return text

    cleaned = str(result.get("response", "")).strip()
    if not cleaned:
        log.warning("Ollama cleanup returned empty text; using raw transcript.")
        return text
    return cleaned


def check_ollama(endpoint: str, timeout_seconds: float = 2) -> tuple[bool, str]:
    tags_endpoint = endpoint.replace("/api/generate", "/api/tags")
    try:
        with urllib.request.urlopen(tags_endpoint, timeout=timeout_seconds) as response:
            if 200 <= response.status < 300:
                return True, "Ollama API is reachable."
            return False, f"Ollama API returned HTTP {response.status}."
    except Exception as exc:
        return False, f"Ollama API is not reachable: {exc}"
