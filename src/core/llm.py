"""LLM factory — OPENAI_API_KEY from environment (.env via python-dotenv)."""

import os
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@lru_cache(maxsize=1)
def get_chat_model(model: Optional[str] = None, temperature: float = 0.3):
    """Returns ChatOpenAI. Raises if OPENAI_API_KEY is missing (fail fast for production runs)."""
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
    """Returns ChatOpenAI when key is set; otherwise returns a minimal stub for offline tests."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("your_"):
        return _StubChatModel()
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model or os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=temperature,
    )


class _StubChatModel:
    """Offline placeholder: returns fixed markdown so the graph can be smoke-tested without API."""

    def invoke(self, messages, **kwargs):
        class R:
            content = (
                "(Stub) OPENAI_API_KEY 미설정 — 실제 보고서 문단은 API 연동 후 생성됩니다.\n\n"
                "## Stub\n\n- 시장·양사·SWOT 컨텍스트가 주입되면 이 영역이 대체됩니다."
            )

        return R()
