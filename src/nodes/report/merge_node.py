"""최종 Markdown 병합 및 PDF 저장.

문서 순서:
  제목 → 작성일 → SUMMARY → 목차 → 본문(2~5장) → **맨 마지막 REFERENCE(참고문헌)**

산출물: `report/final/`에 `.md` + `.pdf` (PDF 실패 시 MD만 경로 반환, warnings에 기록).
"""

from __future__ import annotations

from pathlib import Path

from src.report.pdf_export import (
    default_report_stem,
    format_report_date_korean,
    parse_or_today,
    write_report_artifacts,
)
from src.state.state import ReportGraphState

# 표지용 (Markdown # 제거)
DEFAULT_TITLE_PLAIN = "글로벌 배터리 패러다임 전환기: LGES vs CATL 전략 비교 분석"

_BODY_ORDER = (
    "section1",
    "section2",
    "section3",
    "section4",
    "section5",
)

_LABELS = {
    "section1": "## 2. 시장 배경 및 산업 환경 변화",
    "section2": "## 3.1 LG Energy Solution (LGES)",
    "section3": "## 3.2 CATL",
    "section4": "## 4. Comparative SWOT 분석",
    "section5": "## 5. 종합 시사점 및 전략적 제언",
    "section6": "## 6. REFERENCE",
}

_TOC_MARKDOWN = """## 목차

1. SUMMARY  
2. 시장 배경 및 산업 환경 변화  
3. LG Energy Solution (LGES)  
4. CATL  
5. Comparative SWOT 분석  
6. 종합 시사점 및 전략적 제언  
7. 참고문헌 (REFERENCE)  
"""

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_OUTPUT_DIR = _PROJECT_ROOT / "report" / "final"


def _title_from_state(state: ReportGraphState) -> str:
    raw = (state.get("report_title") or "").strip()
    if raw:
        return raw.lstrip("#").strip()
    return DEFAULT_TITLE_PLAIN


def build_final_report_markdown(state: ReportGraphState) -> str:
    """제목·작성일·요약·목차·본문·참고문헌 순서의 단일 Markdown 문자열."""
    sections = state.get("sections") or {}
    d = parse_or_today(state.get("report_date"))
    iso = d.isoformat()
    title = _title_from_state(state)

    parts: list[str] = []
    parts.append(f"# {title}\n\n")
    parts.append(
        f"**작성일:** {format_report_date_korean(d)} (`{iso}`)\n\n"
    )
    parts.append("---\n\n")
    parts.append("## SUMMARY\n\n")
    summary_body = (sections.get("section0") or "").strip()
    if not summary_body:
        summary_body = "*(SUMMARY 섹션이 비어 있습니다. section0_node 결과를 확인하세요.)*"
    parts.append(summary_body + "\n\n")
    parts.append("---\n\n")
    parts.append(_TOC_MARKDOWN)
    parts.append("\n---\n\n")

    for key in _BODY_ORDER:
        body = (sections.get(key) or "").strip()
        if not body:
            continue
        label = _LABELS.get(key, f"## {key}")
        parts.append(f"{label}\n\n{body}\n\n")

    parts.append("---\n\n")
    parts.append("## 6. REFERENCE\n\n")
    ref_body = (sections.get("section6") or "").strip()
    if not ref_body:
        ref_body = (
            "*※ 참고문헌: 수집된 `raw_findings`의 출처를 section6 노드에서 정리합니다. "
            "현재 항목이 비어 있으면 조사·정제 파이프라인을 확인하세요.*"
        )
    parts.append(ref_body + "\n\n")

    text = "".join(parts)
    if not text.endswith("\n"):
        text += "\n"
    return text


def merge_node(state: ReportGraphState) -> dict:
    final_report = build_final_report_markdown(state)
    stem = default_report_stem()
    out_dir = _DEFAULT_OUTPUT_DIR
    md_path, pdf_path, pdf_ok = write_report_artifacts(
        final_report,
        output_dir=out_dir,
        stem=stem,
    )

    warnings = list(state.get("warnings") or [])
    if not pdf_ok:
        warnings.append(
            "PDF 변환 실패(WeasyPrint 또는 시스템 폰트). Markdown 파일은 저장되었습니다."
        )

    return {
        "final_report": final_report,
        "final_report_md_path": md_path,
        "final_report_pdf_path": pdf_path if pdf_ok else "",
        "warnings": warnings,
    }


def merge_sections_markdown(sections: dict) -> str:
    """테스트용: sections dict만으로 본문 생성 (파일 저장 없음)."""
    return build_final_report_markdown({"sections": sections})
