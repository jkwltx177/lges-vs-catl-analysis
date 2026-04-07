"""tiktoken 기반 토큰 계산 + 요약 캐시 관리."""

import json
from typing import Any, Dict, List, Mapping, Sequence

import tiktoken

_enc = tiktoken.get_encoding("cl100k_base")


# ----------------------------------------------------------------
# Token Counting
# ----------------------------------------------------------------

def count_tokens(text: str) -> int:
    """cl100k_base 기준 텍스트 토큰 수 반환."""
    return len(_enc.encode(text))


def count_documents_tokens(documents: Sequence[Mapping[str, Any]]) -> int:
    """문서 목록의 총 토큰 수 계산 (content 필드 기준)."""
    total = 0
    for doc in documents:
        content = doc.get("content", "") or doc.get("raw_content", "")
        total += count_tokens(str(content))
    return total


# ----------------------------------------------------------------
# Token Usage Update
# ----------------------------------------------------------------

def update_token_usage(state: Mapping[str, Any]) -> Dict[str, int]:
    """state의 raw_documents + raw_findings 토큰 수를 계산하여 token_usage 반환.

    raw 원문 데이터는 변경하지 않음.
    """
    raw_documents: Sequence[Mapping[str, Any]] = state.get("raw_documents", [])
    raw_findings: Sequence[Mapping[str, Any]] = state.get("raw_findings", [])

    raw_docs_tokens = count_documents_tokens(raw_documents)
    raw_findings_tokens = sum(
        count_tokens(str(f.get("raw_content", ""))) for f in raw_findings
    )

    existing: Mapping[str, int] = state.get("token_usage", {})
    updated = {
        **existing,
        "raw_documents": raw_docs_tokens,
        "raw_findings": raw_findings_tokens,
        "total": raw_docs_tokens + raw_findings_tokens,
    }
    return updated


# ----------------------------------------------------------------
# Summary Cache
# ----------------------------------------------------------------

def add_to_summary_cache(
    state: Mapping[str, Any], query_id: str, summary: str
) -> Dict[str, str]:
    """요약 캐시에 항목 추가. raw_documents는 건드리지 않음."""
    cache: Dict[str, str] = dict(state.get("summary_cache", {}))
    cache[query_id] = summary
    return cache


def get_summary_or_raw(
    state: Mapping[str, Any], query_id: str, raw_content: str
) -> str:
    """캐시된 요약이 있으면 반환, 없으면 raw_content 반환."""
    cache: Mapping[str, str] = state.get("summary_cache", {})
    return cache.get(query_id, raw_content)
