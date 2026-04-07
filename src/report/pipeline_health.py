"""보고서·분석 파이프라인 산출물 점검 — 섹션·상위 입력 누락 여부를 문서화."""

from __future__ import annotations

from datetime import datetime
from typing import Any, List, Tuple

from src.state.state import ReportGraphState

SECTION_KEYS = (
    "section0",
    "section1",
    "section2",
    "section3",
    "section4",
    "section5",
    "section6",
)
SECTION_LABELS = {
    "section0": "SUMMARY",
    "section1": "서론 — 시장 배경",
    "section2": "본론 — LGES",
    "section3": "본론 — CATL",
    "section4": "본론 — SWOT",
    "section5": "결론 — 시사점·제언",
    "section6": "참고문헌",
}


def _len_text(s: Any) -> int:
    return len((s or "").strip()) if isinstance(s, str) else 0


def _status(n: int) -> Tuple[str, str]:
    if n == 0:
        return "누락", "❌"
    if n < 80:
        return "짧음", "⚠️"
    return "양호", "✓"


def _has_pipe_table(text: str) -> bool:
    t = text or ""
    return "|" in t and "---" in t


def build_pipeline_health_markdown(
    state: ReportGraphState,
    *,
    md_path: str,
    pdf_path: str,
    pdf_ok: bool,
) -> str:
    """실행 직후 점검용 Markdown (docs/에 저장)."""
    sections = state.get("sections") or {}
    lines: List[str] = []

    lines.append("# 보고서 파이프라인 출력 점검\n")
    lines.append(f"- 생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    lines.append(f"- Markdown: `{md_path}`\n")
    if pdf_ok and pdf_path:
        lines.append(f"- PDF: `{pdf_path}`\n")
    else:
        lines.append("- PDF: **생성 실패** (WeasyPrint·폰트·의존성 확인)\n")
    lines.append("\n---\n\n## 1. 보고서 섹션 에이전트 (section0~6)\n\n")
    lines.append("| 섹션 | 설명 | 글자수(공백 제외 근사) | 상태 | 표 포함 |\n")
    lines.append("|------|------|----------------------|------|--------|\n")

    any_missing = False
    for key in SECTION_KEYS:
        body = (sections.get(key) or "").strip()
        n = len(body)
        st, _ = _status(n)
        if n == 0:
            any_missing = True
        label = SECTION_LABELS.get(key, key)
        tbl = "예" if key == "section4" and _has_pipe_table(body) else ("—" if key != "section4" else "없음")
        lines.append(f"| `{key}` | {label} | {n} | {st} | {tbl} |\n")

    lines.append("\n---\n\n## 2. 분석 단계 입력 (bridge → Report)\n\n")

    rf = state.get("raw_findings") or []
    lines.append(f"- `raw_findings` 문서 수: **{len(rf)}**\n")

    qc = state.get("query_coverage") or {}
    lines.append(f"- `query_coverage` (Task.1 임베딩·검색) 쿼리 수: **{len(qc) if isinstance(qc, dict) else 0}**\n")

    mc = state.get("market_context") or {}
    lines.append(f"- `market_context` 키 수: **{len(mc)}** (비어 있으면 ⚠️)\n")

    cs = state.get("comparative_swot") or {}
    cs_summary = _len_text(cs.get("comparative_summary", ""))
    lines.append(
        f"- `comparative_swot.comparative_summary` 길이: **{cs_summary}** 문자\n"
    )

    fi = state.get("final_insight") or {}
    fi_list = fi.get("final_insights") or []
    lines.append(f"- `final_insight.final_insights` 항목 수: **{len(fi_list) if isinstance(fi_list, list) else 0}**\n")

    pa = state.get("company_a_portfolio") or {}
    pb = state.get("company_b_portfolio") or {}
    n_core_a = len((pa.get("core_services") or []) if isinstance(pa, dict) else [])
    n_core_b = len((pb.get("core_services") or []) if isinstance(pb, dict) else [])
    lines.append(
        f"- 포트폴리오 `core_services`: LGES **{n_core_a}**개, CATL **{n_core_b}**개\n"
    )

    lines.append("\n---\n\n## 3. 권장 후속 조치\n\n")
    if any_missing:
        lines.append(
            "- 일부 섹션이 비어 있습니다. LLM 오류·토큰 한도·CONTEXT 길이를 확인하세요.\n"
        )
    if not pdf_ok:
        lines.append(
            "- PDF가 없으면 `report/final/*.md`와 `docs/*.md`를 편집기나 Pandoc으로 변환할 수 있습니다.\n"
        )
    if len(rf) == 0:
        lines.append("- `raw_findings`가 비어 있으면 Research/Refine 단계를 확인하세요.\n")
    if not any_missing and pdf_ok and len(rf) > 0:
        lines.append("- 모든 섹션에 본문이 있고 PDF가 생성되었습니다.\n")

    return "".join(lines)
