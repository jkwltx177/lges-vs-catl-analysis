"""Lightweight OpenAI client helpers for optional Task 3 LLM analysis."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, Optional, cast

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency at runtime
    OpenAI = None  # type: ignore[assignment]


_ENV_LOADED = False


def _load_project_env() -> None:
    """Load a local .env file from the project root if present."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return

    project_root = Path(__file__).resolve().parents[2]
    env_path = project_root / ".env"
    if not env_path.exists():
        _ENV_LOADED = True
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value

    _ENV_LOADED = True


def llm_enabled() -> bool:
    """Return True when an API key is available and the OpenAI SDK is installed."""
    _load_project_env()
    if os.getenv("TASK3_DISABLE_LLM") == "1":
        return False
    return bool(os.getenv("OPENAI_API_KEY")) and OpenAI is not None


def get_model_name() -> str:
    """Model name for analysis calls. Override with OPENAI_MODEL."""
    _load_project_env()
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def get_client() -> Optional[Any]:
    """Create an OpenAI client if configuration is available."""
    if not llm_enabled():
        return None
    openai_cls = cast(Any, OpenAI)
    return openai_cls(api_key=os.getenv("OPENAI_API_KEY"))


def parse_json_object(raw_text: str) -> Optional[dict[str, Any]]:
    """Parse a JSON object from plain text or fenced code."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.startswith("json"):
            text = text[4:].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None

    return parsed if isinstance(parsed, dict) else None


def invoke_json(prompt: str, payload: Mapping[str, Any]) -> Optional[dict[str, Any]]:
    """Invoke the configured LLM and parse a JSON object response."""
    client = get_client()
    if client is None:
        return None

    response = client.responses.create(
        model=get_model_name(),
        input=[
            {
                "role": "system",
                "content": [{"type": "input_text", "text": prompt}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": json.dumps(payload, ensure_ascii=False)}],
            },
        ],
    )

    output_text = getattr(response, "output_text", "")
    if not output_text:
        return None

    return parse_json_object(output_text)
