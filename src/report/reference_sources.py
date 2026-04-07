"""조사·임베딩 단계 `raw_findings`에서 URL·출처를 추출해 참고문헌 부록용 Markdown 생성."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set

_URL_RE = re.compile(r"https?://[^\s\]\)\"'<>]+")


def _dedupe_preserve_order(items: List[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for x in items:
        x = (x or "").strip()
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def collect_sources_from_raw_findings(raw_findings: Any) -> List[str]:
    """sources 필드 + raw_content 내 URL을 모아 중복 제거."""
    lines: List[str] = []
    if not isinstance(raw_findings, list):
        return lines

    for rf in raw_findings:
        if not isinstance(rf, dict):
            continue
        for s in rf.get("sources") or []:
            if s:
                lines.append(str(s).strip())
        raw = str(rf.get("raw_content", ""))
        for m in _URL_RE.finditer(raw):
            u = m.group(0).rstrip(".,;)]}")
            lines.append(u)

    return _dedupe_preserve_order(lines)


def _urls_from_item_list(items: Any) -> List[str]:
    """`items[]`에 `content`·`source`가 있는 dict 리스트 (CompanyRaw.items 또는 cleaned)."""
    lines: List[str] = []
    if not isinstance(items, list):
        return lines
    for it in items:
        if not isinstance(it, dict):
            continue
        s = (it.get("source") or "").strip()
        if s:
            lines.append(s)
        blob = (
            f"{it.get('content', '')} {it.get('evidence', '')} {it.get('point', '')} "
            f"{it.get('why_it_matters', '')}"
        )
        for m in _URL_RE.finditer(blob):
            lines.append(m.group(0).rstrip(".,;)]}"))
    return lines


def _urls_from_company_raw(company: Any) -> List[str]:
    """`{{ \"name\": ..., \"items\": [...] }}` 형태 Task.1 기업 조사 결과."""
    if not isinstance(company, dict):
        return []
    return _urls_from_item_list(company.get("items"))


def _urls_from_swot(company_swot: Any) -> List[str]:
    """`CompanySWOT` — S/W/O/T 각각 SWOTItem 리스트."""
    if not isinstance(company_swot, dict):
        return []
    lines: List[str] = []
    for letter in ("S", "W", "O", "T"):
        lines.extend(_urls_from_item_list(company_swot.get(letter)))
    return lines


def collect_all_reference_urls(
    raw_findings: Any,
    *,
    company_a: Any = None,
    company_b: Any = None,
    company_a_cleaned: Any = None,
    company_b_cleaned: Any = None,
    company_a_swot: Any = None,
    company_b_swot: Any = None,
) -> List[str]:
    """
    보고서 참고문헌·부록용 URL 전체: Task.1 `raw_findings` + 기업 조사 JSON + 정제 항목 + SWOT 출처.
    (이전에는 `raw_findings`만 보면 company_research의 `items[].source`가 빠졌음.)
    """
    lines: List[str] = []
    lines.extend(collect_sources_from_raw_findings(raw_findings))
    lines.extend(_urls_from_company_raw(company_a))
    lines.extend(_urls_from_company_raw(company_b))
    lines.extend(_urls_from_item_list(company_a_cleaned))
    lines.extend(_urls_from_item_list(company_b_cleaned))
    lines.extend(_urls_from_swot(company_a_swot))
    lines.extend(_urls_from_swot(company_b_swot))
    return _dedupe_preserve_order(lines)


def format_query_coverage_lines(query_coverage: Dict[str, Any]) -> List[str]:
    """Task.1 VectorDB·웹 쿼리 커버리지 요약 (보고서 부록용)."""
    if not query_coverage:
        return []
    out: List[str] = []
    for q, info in sorted(query_coverage.items(), key=lambda x: str(x[0]))[:80]:
        if not isinstance(info, dict):
            continue
        cnt = info.get("count", 0)
        avg = info.get("avg_distance")
        src = []
        if info.get("has_vdb"):
            src.append("VDB")
        if info.get("has_web"):
            src.append("WEB")
        avg_s = f"{avg:.3f}" if isinstance(avg, (int, float)) else "—"
        out.append(f"- `{q[:120]}{'…' if len(str(q)) > 120 else ''}` — {cnt}건, dist≈{avg_s}, [{'+'.join(src) or '—'}]")
    return out


def build_reference_appendix_markdown(
    raw_findings: Any,
    *,
    query_coverage: Dict[str, Any] | None = None,
    company_a: Any = None,
    company_b: Any = None,
    company_a_cleaned: Any = None,
    company_b_cleaned: Any = None,
    company_a_swot: Any = None,
    company_b_swot: Any = None,
) -> str:
    """merge 단계에서 참고문헌 뒤에 붙이는 자동 부록."""
    urls = collect_all_reference_urls(
        raw_findings,
        company_a=company_a,
        company_b=company_b,
        company_a_cleaned=company_a_cleaned,
        company_b_cleaned=company_b_cleaned,
        company_a_swot=company_a_swot,
        company_b_swot=company_b_swot,
    )
    parts: List[str] = []
    parts.append("\n### 출처·URL 인덱스 (파이프라인 자동 추출)\n\n")
    parts.append(
        "아래는 Task.1 조사 단계에서 수집·임베딩 검색에 사용된 `raw_findings`에서 추출한 URL·메타입니다. "
        "위의 서술형 참고문헌과 함께 검증하세요.\n\n"
    )
    if urls:
        for i, u in enumerate(urls, 1):
            parts.append(f"{i}. {u}\n")
    else:
        parts.append("*※ 추출된 URL이 없습니다. 조사 단계 `sources`·웹 검색 결과를 확인하세요.*\n")

    qc = format_query_coverage_lines(query_coverage or {})
    if qc:
        parts.append("\n#### 조사 쿼리 커버리지 (Task.1 Retrieval)\n\n")
        parts.extend(line + "\n" for line in qc)

    return "".join(parts)
