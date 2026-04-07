"""LLM 유틸: Task 3(OpenAI JSON) + 보고서(ChatOpenAI)."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Optional, cast

from dotenv import load_dotenv

load_dotenv()

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Task 3: OpenAI Responses + JSON (analysis pipeline)
# ---------------------------------------------------------------------------

_ENV_EXTRA_LOADED = False


def _merge_env_from_dotenv_if_needed() -> None:
    """load_dotenv 이후에도 누락된 키만 .env에서 채움 (main 브랜치 호환)."""
    global _ENV_EXTRA_LOADED
    if _ENV_EXTRA_LOADED:
        return
    project_root = Path(__file__).resolve().parents[2]
    env_path = project_root / ".env"
    if not env_path.exists():
        _ENV_EXTRA_LOADED = True
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
    _ENV_EXTRA_LOADED = True


def llm_enabled() -> bool:
    _merge_env_from_dotenv_if_needed()
    if os.getenv("TASK3_DISABLE_LLM") == "1":
        return False
    return bool(os.getenv("OPENAI_API_KEY")) and OpenAI is not None


def get_model_name() -> str:
    _merge_env_from_dotenv_if_needed()
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
# Report: LangChain ChatOpenAI
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def get_chat_model(model: Optional[str] = None, temperature: float = 0.3):
    from langchain_openai import ChatOpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("your_"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and set a valid key."
        )
    return ChatOpenAI(
        model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=temperature,
    )


def get_chat_model_or_stub(model: Optional[str] = None, temperature: float = 0.3):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("your_"):
        return _StubChatModel()
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=temperature,
    )


class _StubChatModel:
    def invoke(self, messages, **kwargs):
        class R:
            content = (
                "(Stub) OPENAI_API_KEY 미설정 — 실제 보고서 문단은 API 연동 후 생성됩니다.\n\n"
                "## Stub\n\n- 시장·양사·SWOT 컨텍스트가 주입되면 이 영역이 대체됩니다."
            )

        return R()
