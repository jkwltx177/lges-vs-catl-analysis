"""LLM 유틸: Task 3(OpenAI JSON) + 보고서(ChatOpenAI). `.env`의 OPENAI_API_KEY 사용."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any, Mapping, Optional, cast

import src.core.env  # noqa: F401 — 프로젝트 .env 선로드

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Task 3: OpenAI Responses + JSON (analysis pipeline)
# ---------------------------------------------------------------------------


def llm_enabled() -> bool:
    if os.getenv("TASK3_DISABLE_LLM") == "1":
        return False
    return bool(os.getenv("OPENAI_API_KEY")) and OpenAI is not None


def get_model_name() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def get_client() -> Optional[Any]:
    if not llm_enabled():
        return None
    openai_cls = cast(Any, OpenAI)
    return openai_cls(api_key=os.getenv("OPENAI_API_KEY"))


def parse_json_object(raw_text: str) -> Optional[dict[str, Any]]:
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
    client = get_client()
    if client is None:
        return None
    response = client.responses.create(
        model=get_model_name(),
        input=[
            {"role": "system", "content": [{"type": "input_text", "text": prompt}]},
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


# ---------------------------------------------------------------------------
# Report: LangChain ChatOpenAI (항상 .env 의 OPENAI_API_KEY 필요)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_chat_model(model: Optional[str] = None, temperature: float = 0.3):
    from langchain_openai import ChatOpenAI

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or api_key.startswith("your_"):
        raise RuntimeError(
            "OPENAI_API_KEY가 없거나 placeholder입니다. 프로젝트 루트 `.env`에 유효한 키를 설정하세요."
        )
    return ChatOpenAI(
        model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=temperature,
        api_key=api_key,
    )
