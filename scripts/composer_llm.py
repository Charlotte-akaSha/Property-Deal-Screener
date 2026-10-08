"""OpenAI-compatible Composer API for structured JSON (extraction, research, scoring)."""

from __future__ import annotations

import base64
import json
import os
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import certifi
import jsonschema

from utils import load_env, parse_json_response, validate_against_schema

_DEFAULT_TIMEOUT_SEC = 120.0
_EXT_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def _ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certifi.where())


def composer_settings() -> tuple[str, str, str]:
    load_env()
    base = os.getenv("COMPOSER_API_BASE_URL", "http://127.0.0.1:8787/v1").strip().rstrip("/")
    key = (
        os.getenv("COMPOSER_API_KEY", "").strip()
        or os.getenv("OPENAI_API_KEY", "").strip()
        or "local"
    )
    model = (
        os.getenv("COMPOSER_MODEL", "").strip()
        or os.getenv("MARKET_RESEARCH_MODEL", "").strip()
        or "composer-2.5-fast"
    )
    return base, key, model


def probe_composer_api(timeout_sec: float = 3.0) -> tuple[bool, str]:
    """Return (ok, message) for whether the local Composer HTTP API answers."""
    base, key, model = composer_settings()
    url = f"{base.rstrip('/')}/models"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {key}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec, context=_ssl_context()) as resp:
            resp.read(256)
        return True, f"Composer API reachable at {base} (model {model})"
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            return False, f"Composer API rejected the API key (HTTP {exc.code}). Check COMPOSER_API_KEY."
        return True, f"Composer API reachable (HTTP {exc.code})"
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        return False, (
            f"Composer API not running at {base}: {reason}. "
            "Install/start the local Cursor bridge (see docs/composer-setup.md)."
        )


def _timeout_sec() -> float:
    load_env()
    raw = os.getenv("COMPOSER_TIMEOUT_SEC", "").strip()
    if not raw:
        return _DEFAULT_TIMEOUT_SEC
    try:
        return max(30.0, float(raw))
    except ValueError:
        return _DEFAULT_TIMEOUT_SEC


def _mime_for_name(name: str) -> str:
    ext = Path(name).suffix.lower()
    return _EXT_MIME.get(ext, "image/jpeg")


def _chat_completion(messages: list[dict[str, Any]], *, model: str | None = None) -> str:
    base, key, default_model = composer_settings()
    url = f"{base}/chat/completions"
    payload = {
        "model": model or default_model,
        "messages": messages,
        "temperature": 0.2,
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(
            req, timeout=_timeout_sec(), context=_ssl_context()
        ) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Composer API HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Composer API unreachable at {url}: {exc.reason}") from exc

    data = json.loads(raw)
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("Composer API returned no choices.")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not content:
        raise RuntimeError("Composer API returned empty message content.")
    return str(content)


def generate_json_composer(
    *,
    system_prompt: str,
    text_parts: list[str],
    schema: dict[str, Any],
    image_uploads: list[tuple[str, bytes]] | None = None,
    image_paths: list[Path] | None = None,
    retry_hint: str | None = None,
) -> dict[str, Any]:
    user_content: list[dict[str, Any]] = []
    for part in text_parts:
        if part.strip():
            user_content.append({"type": "text", "text": part})
    if image_paths:
        for path in image_paths:
            data = path.read_bytes()
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": (
                            f"data:{_mime_for_name(path.name)};base64,"
                            f"{base64.standard_b64encode(data).decode('ascii')}"
                        )
                    },
                }
            )
    if image_uploads:
        for name, data in image_uploads:
            user_content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": (
                            f"data:{_mime_for_name(name)};base64,"
                            f"{base64.standard_b64encode(data).decode('ascii')}"
                        )
                    },
                }
            )
    schema_note = (
        "Return a single JSON object only (no markdown fences) matching this schema:\n"
        + json.dumps(schema, indent=2)
    )
    if retry_hint:
        schema_note += f"\n\nFix validation errors:\n{retry_hint}"
    user_content.append({"type": "text", "text": schema_note})

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    raw = _chat_completion(messages)
    data = parse_json_response(raw)
    if not isinstance(data, dict):
        raise ValueError("Composer returned non-object JSON.")
    return data


def generate_json_composer_with_retry(
    *,
    system_prompt: str,
    text_parts: list[str],
    schema: dict[str, Any],
    image_uploads: list[tuple[str, bytes]] | None = None,
    image_paths: list[Path] | None = None,
) -> dict[str, Any]:
    last_error: Exception | None = None
    hint: str | None = None
    for _ in range(2):
        try:
            data = generate_json_composer(
                system_prompt=system_prompt,
                text_parts=text_parts,
                schema=schema,
                image_uploads=image_uploads,
                image_paths=image_paths,
                retry_hint=hint,
            )
            validate_against_schema(data, schema)
            return data
        except (json.JSONDecodeError, jsonschema.ValidationError, ValueError) as exc:
            last_error = exc
            hint = str(exc)
    raise RuntimeError(f"Composer JSON validation failed: {last_error}") from last_error
