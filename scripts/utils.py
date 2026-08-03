"""Shared helpers: paths, env, prompts, slug, schema validation, Gemini client."""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

import jsonschema
from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_PHOTOS = 5
PROMPT_VERSION = "extraction_v1 / scoring_v1"
MAX_API_RETRIES = 4
API_RETRY_BASE_DELAY_SEC = 2.0
TRANSIENT_API_STATUS_CODES = {429, 500, 502, 503, 504}


def load_env() -> None:
    load_dotenv(ROOT / ".env")


def get_model_name() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()


def get_gemini_client() -> genai.Client:
    load_env()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Copy .env.example to .env and set it.")
    return genai.Client(api_key=api_key)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_prompt(name: str) -> str:
    return read_text(ROOT / "prompts" / name)


def load_schema(name: str) -> dict[str, Any]:
    return json.loads(read_text(ROOT / "schema" / name))


def load_strategy_raw() -> str:
    return read_text(ROOT / "strategy.md")


def strategy_rules_without_weights(strategy_md: str | None = None) -> str:
    text = strategy_md if strategy_md is not None else load_strategy_raw()
    return re.sub(r"```yaml\s*.*?```", "", text, count=1, flags=re.DOTALL | re.IGNORECASE).strip()


def validate_against_schema(data: Any, schema: dict[str, Any]) -> None:
    jsonschema.validate(instance=data, schema=schema)


def slugify(text: str) -> str:
    text = text.strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s-]+", "_", text)
    return text.strip("_")[:120] or "property"


def property_id_from_extracted(extracted: dict[str, Any], label: str | None = None) -> str:
    if label and label.strip():
        return slugify(label)
    parts = [
        extracted.get("address") or "",
        extracted.get("city") or "",
        extracted.get("state") or "",
    ]
    joined = " ".join(p for p in parts if p).strip()
    if not joined:
        raise ValueError("Cannot build Property ID: missing address and no property label.")
    return slugify(joined)


def discover_images(folder: Path) -> list[Path]:
    files = [
        p
        for p in sorted(folder.iterdir())
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS and p.name.lower().startswith("photo")
    ]
    return files[:MAX_PHOTOS]


def image_parts_from_paths(paths: list[Path]) -> list[types.Part]:
    parts: list[types.Part] = []
    for path in paths:
        mime = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }.get(path.suffix.lower(), "image/jpeg")
        # Validate readable image
        with Image.open(path) as img:
            img.verify()
        parts.append(
            types.Part.from_bytes(data=path.read_bytes(), mime_type=mime)
        )
    return parts


def image_parts_from_uploads(uploads: list[tuple[str, bytes]]) -> list[types.Part]:
    parts: list[types.Part] = []
    for name, data in uploads[:MAX_PHOTOS]:
        suffix = Path(name).suffix.lower() or ".jpg"
        mime = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }.get(suffix, "image/jpeg")
        parts.append(types.Part.from_bytes(data=data, mime_type=mime))
    return parts


def parse_json_response(text: str) -> Any:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def is_transient_api_error(exc: Exception) -> bool:
    if isinstance(exc, errors.ServerError):
        return True
    if isinstance(exc, errors.APIError):
        return exc.code in TRANSIENT_API_STATUS_CODES
    return False


def generate_content_with_retry(
    client: genai.Client,
    *,
    model: str,
    contents: list[Any],
    config: types.GenerateContentConfig,
) -> Any:
    last_error: Exception | None = None
    for attempt in range(MAX_API_RETRIES):
        try:
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            if not is_transient_api_error(exc) or attempt == MAX_API_RETRIES - 1:
                raise
            last_error = exc
            time.sleep(API_RETRY_BASE_DELAY_SEC * (2**attempt))
    raise RuntimeError(f"Gemini API failed after {MAX_API_RETRIES} retries") from last_error


def generate_json(
    client: genai.Client,
    *,
    system_prompt: str,
    user_parts: list[Any],
    schema: dict[str, Any],
    retry_hint: str | None = None,
) -> dict[str, Any]:
    contents: list[Any] = list(user_parts)
    if retry_hint:
        contents.append(
            "Previous response failed validation. Fix and return valid JSON only.\n"
            f"Validation error:\n{retry_hint}"
        )
    response = generate_content_with_retry(
        client,
        model=get_model_name(),
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_json_schema=schema,
            temperature=0.2,
        ),
    )
    raw = response.text or ""
    data = parse_json_response(raw)
    if not isinstance(data, dict):
        raise ValueError("Model returned non-object JSON.")
    return data


def generate_json_with_retry(
    client: genai.Client,
    *,
    system_prompt: str,
    user_parts: list[Any],
    schema: dict[str, Any],
) -> dict[str, Any]:
    last_error: Exception | None = None
    hint: str | None = None
    for _ in range(2):
        try:
            data = generate_json(
                client,
                system_prompt=system_prompt,
                user_parts=user_parts,
                schema=schema,
                retry_hint=hint,
            )
            validate_against_schema(data, schema)
            return data
        except (json.JSONDecodeError, jsonschema.ValidationError, ValueError) as exc:
            last_error = exc
            hint = str(exc)
    raise RuntimeError(f"JSON validation failed after retry: {last_error}") from last_error


def normalize_list_items(items: list[str] | None) -> list[str]:
    if not items:
        return []
    result: list[str] = []
    for item in items:
        text = str(item).strip()
        if not text:
            continue
        for part in re.split(r"\n+|\s\|\s", text):
            part = re.sub(r"^[-*•]\s+", "", part.strip())
            if part:
                result.append(part)
    return result


def join_list(items: list[str] | None) -> str:
    """Newline-separated bullets for Google Sheets cells and exports."""
    normalized = normalize_list_items(items)
    if not normalized:
        return ""
    return "\n".join(f"• {item}" for item in normalized)
