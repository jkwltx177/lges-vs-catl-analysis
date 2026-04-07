"""Serialize ReportGraphState (and upstream fields) into prompt-safe CONTEXT blocks."""

from __future__ import annotations

import json
from typing import Any, List, Optional

from src.report.reference_sources import collect_all_reference_urls
from src.state.state import ReportGraphState


def _json(obj: Any, limit: Optional[int] = None) -> str:
    s = json.dumps(obj, ensure_ascii=False, indent=2, default=str)
    if limit and len(s) > limit:
        return s[:limit] + "\n... [truncated]"
    return s


def build_report_context(
    state: ReportGraphState,
    *,
    mode: str,
    max_raw_chars_per_finding: int = 800,
    max_findings: int = 20,
) -> str:
    """
    mode: section1 | section2 | section3 | section4 | section5 | section0 | section6
    - section0: 앞선 sections 1~5 텍스트를 포함 (SUMMARY용)
    - section6: raw_findings + 기업 조사/정제/SWOT에서 추출한 URL·메타
    """
    parts: List[str] = []

    parts.append("## Global inputs\n")
    parts.append(_json({"market_context": state.get("market_context")}))
    parts.append("\n## Company portfolios\n")
    parts.append(_json({"company_a_portfolio": state.get("company_a_portfolio")}))
    parts.append("\n")
    parts.append(_json({"company_b_portfolio": state.get("company_b_portfolio")}))

    parts.append("\n## Comparative SWOT (structured)\n")
    parts.append(_json({"comparative_swot": state.get("comparative_swot")}))

    parts.append("\n## Final insight (analysis output)\n")
    parts.append(_json({"final_insight": state.get("final_insight")}))

    if mode != "section6":
        parts.append("\n## Raw findings (excerpts; do not invent beyond this)\n")
        raw = state.get("raw_findings") or []
        for i, rf in enumerate(raw[:max_findings]):
            if not isinstance(rf, dict):
                continue
            content = str(rf.get("raw_content", ""))[:max_raw_chars_per_finding]
            parts.append(
                f"### Finding {i + 1}: {rf.get('agent_name', '')} / {rf.get('subtopic', '')}\n"
                f"sources: {rf.get('sources', [])}\n\n{content}\n"
            )

    if mode == "section0":
        sec = state.get("sections") or {}
        parts.append("\n## Already drafted sections (for SUMMARY only; synthesize, do not repeat verbatim)\n")
        for k in ("section1", "section2", "section3", "section4", "section5"):
            body = sec.get(k) or ""
            parts.append(f"### {k}\n\n{body[:12000]}\n")

    if mode == "section6":
        urls = collect_all_reference_urls(
            state.get("raw_findings") or [],
            company_a=state.get("company_a"),
            company_b=state.get("company_b"),
            company_a_cleaned=state.get("company_a_cleaned"),
            company_b_cleaned=state.get("company_b_cleaned"),
            company_a_swot=state.get("company_a_swot"),
            company_b_swot=state.get("company_b_swot"),
        )
        parts.append(
            "\n## 추출 URL·출처 (파이프라인 자동, 참고문헌에 반드시 반영)\n\n"
        )
        if urls:
            for i, u in enumerate(urls[:250], 1):
                parts.append(f"{i}. {u}\n")
        else:
            parts.append("*(URL이 비어 있으면 아래 findings의 sources 필드를 사용.)*\n")

        qc = state.get("query_coverage") or {}
        if qc:
            parts.append("\n## Task.1 조사 쿼리 커버리지 (임베딩·웹 검색과 연결)\n")
            parts.append(_json(qc, limit=16000))

        parts.append("\n## Raw findings (전체 메타 — 출처 누락 금지)\n")
        raw = state.get("raw_findings") or []
        for i, rf in enumerate(raw):
            if not isinstance(rf, dict):
                continue
            parts.append(
                _json(
                    {
                        "agent_name": rf.get("agent_name"),
                        "subtopic": rf.get("subtopic"),
                        "sources": rf.get("sources"),
                        "source_type": rf.get("source_type"),
                    }
                )
            )
            parts.append("\n")

    return "\n".join(parts)
