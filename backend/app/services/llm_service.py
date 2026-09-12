"""All communication with the local Ollama/Llama instance lives here."""

import json
import logging
from typing import Any, Iterator, List, Optional

import requests

from app.core.config import settings
from app.core.errors import LLMBadOutput, LLMUnavailable
from app.utils.llm_parser import extract_json

logger = logging.getLogger(__name__)

_TIMEOUT = (settings.llm_connect_timeout, settings.llm_timeout)


def _payload(prompt: str, stream: bool, temperature: Optional[float] = None) -> dict:
    return {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": stream,
        "options": {
            "temperature": settings.llm_temperature if temperature is None else temperature
        },
    }


def is_available() -> bool:
    """Cheap reachability probe used by the health endpoint."""
    try:
        response = requests.get(settings.ollama_tags_url, timeout=3)
        return response.status_code == 200
    except requests.RequestException:
        return False


def installed_models() -> List[str]:
    try:
        response = requests.get(settings.ollama_tags_url, timeout=3)
        response.raise_for_status()
        return [model["name"] for model in response.json().get("models", [])]
    except (requests.RequestException, KeyError, ValueError):
        return []


def ask_llm(prompt: str, temperature: Optional[float] = None) -> str:
    """Send a prompt and return the complete response text."""
    try:
        response = requests.post(
            settings.ollama_generate_url,
            json=_payload(prompt, stream=False, temperature=temperature),
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()["response"]
    except requests.Timeout as exc:
        logger.warning("Ollama timed out after %ss", settings.llm_timeout)
        raise LLMUnavailable(
            f"The model did not respond within {int(settings.llm_timeout)}s. "
            "Try a smaller document scope or a faster model."
        ) from exc
    except requests.ConnectionError as exc:
        logger.warning("Could not connect to Ollama at %s", settings.ollama_url)
        raise LLMUnavailable() from exc
    except requests.HTTPError as exc:
        detail = _http_error_detail(exc)
        logger.warning("Ollama returned an error: %s", detail)
        raise LLMUnavailable(detail) from exc
    except (KeyError, ValueError) as exc:
        raise LLMBadOutput("The model returned an unreadable response.") from exc


def stream_llm(prompt: str, temperature: Optional[float] = None) -> Iterator[str]:
    """Yield response tokens as they are produced by the model."""
    try:
        with requests.post(
            settings.ollama_generate_url,
            json=_payload(prompt, stream=True, temperature=temperature),
            timeout=_TIMEOUT,
            stream=True,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                token = chunk.get("response")
                if token:
                    yield token
                if chunk.get("done"):
                    break
    except requests.Timeout as exc:
        raise LLMUnavailable(
            f"The model did not respond within {int(settings.llm_timeout)}s."
        ) from exc
    except requests.ConnectionError as exc:
        raise LLMUnavailable() from exc
    except requests.HTTPError as exc:
        raise LLMUnavailable(_http_error_detail(exc)) from exc


def ask_llm_json(prompt: str, attempts: int = 2) -> Any:
    """
    Ask for JSON and parse it, retrying once with a stricter reminder before
    giving up. Small local models regularly wrap JSON in prose on the first try.
    """
    last_raw = ""
    for attempt in range(1, attempts + 1):
        effective_prompt = prompt
        if attempt > 1:
            effective_prompt = (
                f"{prompt}\n\n"
                "IMPORTANT: your previous response was not valid JSON. "
                "Respond with the raw JSON array ONLY — no prose, no code fences."
            )

        last_raw = ask_llm(effective_prompt).strip()
        try:
            return extract_json(last_raw)
        except ValueError:
            logger.warning(
                "LLM returned unparseable JSON (attempt %s/%s)", attempt, attempts
            )

    raise LLMBadOutput(
        "The model did not return valid JSON after several attempts. Please try again."
    )


def _http_error_detail(exc: requests.HTTPError) -> str:
    response = exc.response
    if response is None:
        return "The model server returned an error."
    try:
        error = response.json().get("error", "")
    except ValueError:
        error = response.text[:200]
    if "not found" in error.lower():
        return (
            f"The model '{settings.ollama_model}' is not installed. "
            f"Run: ollama pull {settings.ollama_model}"
        )
    return error or f"The model server returned HTTP {response.status_code}."
