"""최종 Markdown 병합 및 PDF 저장.

문서 순서:
  제목 → **SUMMARY(제목 직하)** → 작성일 → 목차
  → **서론** → **본론** → **결론**(종합 시사점 + 결론 요약) → **참고문헌**

산출물: `report/final/` 및 **`docs/`**에 동일 stem으로 `.md` + `.pdf` 저장.
PDF는 WeasyPrint 우선, 실패 시 fpdf2 폴백. 둘 다 실패 시 MD만 경로 반환·warnings. `docs/report_pipeline_health_*.md`에 섹션·입력 점검 로그.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from src.report.pdf_export import (
    default_report_stem,
    format_report_date_korean,
    parse_or_today,
    primary_report_path,
    write_report_artifacts,
)
from src.report.pipeline_health import build_pipeline_health_markdown
from src.report.reference_sources import build_reference_appendix_markdown
from src.state.state import ReportGraphState

DEFAULT_TITLE_PLAIN = "글로벌 배터리 패러다임 전환기: LGES vs CATL 전략 비교 분석"

_SUB_INTRO = "### 시장 배경 및 산업 환경 변화"
_SUB_LGES = "### LG Energy Solution (LGES)"
_SUB_CATL = "### CATL"
_SUB_SWOT = "### Comparative SWOT 분석"
_SUB_INSIGHT = "### 종합 시사점 및 전략적 제언"
_SUB_CONCLUSION_SUMMARY = "### 결론 요약"

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_OUTPUT_DIR = _PROJECT_ROOT / "report" / "final"
_DOCS_OUTPUT_DIR = _PROJECT_ROOT / "docs"

_TOC_MARKDOWN = """## 목차

1. SUMMARY (핵심 요약)  
2. 서론 — 시장 배경 및 산업 환경 변화  
3. 본론 — LGES · CATL · SWOT 비교  
4. 결론 — 종합 시사점 및 결론 요약  
5. 참고문헌  
"""


def _title_from_state(state: ReportGraphState) -> str:
    raw = (state.get("report_title") or "").strip()
    if raw:
        return raw.lstrip("#").strip()
    return DEFAULT_TITLE_PLAIN


def _conclusion_summary_from_section0(section0: str, *, max_chars: int = 600) -> str:
    t = (section0 or "").strip()
    if not t:
        return "*※ SUMMARY가 비어 있어 결론 요약을 생략합니다.*"
    if len(t) <= max_chars:
        return t
    return t[:max_chars].rstrip() + "\n\n*(위는 SUMMARY의 앞부분 발췌입니다.)*"


def build_final_report_markdown(state: ReportGraphState) -> str:
    """제목 → SUMMARY(제목 직하) → 작성일 → 목차 → 서론 → 본론 → 결론 → 참고문헌."""
    sections = state.get("sections") or {}
    d = parse_or_today(state.get("report_date"))
    iso = d.isoformat()
    title = _title_from_state(state)

    summary_body = (sections.get("section0") or "").strip()
    if not summary_body:
        summary_body = "*(SUMMARY 섹션이 비어 있습니다. section0_node 결과를 확인하세요.)*"

    parts: list[str] = []
    parts.append(f"# {title}\n\n")
    parts.append("## SUMMARY\n\n")
    parts.append(summary_body + "\n\n")
    parts.append("---\n\n")
    parts.append(f"**작성일:** {format_report_date_korean(d)} (`{iso}`)\n\n")
    parts.append("---\n\n")
    parts.append(_TOC_MARKDOWN)
    parts.append("\n---\n\n")

    parts.append("## 서론\n\n")
    s1 = (sections.get("section1") or "").strip()
    if s1:
        parts.append(f"{_SUB_INTRO}\n\n{s1}\n\n")
    else:
        parts.append(f"{_SUB_INTRO}\n\n*(서론 본문이 비어 있습니다.)*\n\n")

    parts.append("---\n\n")
    parts.append("## 본론\n\n")
    s2 = (sections.get("section2") or "").strip()
    s3 = (sections.get("section3") or "").strip()
    s4 = (sections.get("section4") or "").strip()
    if s2:
        parts.append(f"{_SUB_LGES}\n\n{s2}\n\n")
    if s3:
        parts.append(f"{_SUB_CATL}\n\n{s3}\n\n")
    if s4:
        parts.append(f"{_SUB_SWOT}\n\n{s4}\n\n")
    if not (s2 or s3 or s4):
        parts.append("*(본론 섹션이 비어 있습니다.)*\n\n")

    parts.append("---\n\n")
    parts.append("## 결론\n\n")
    s5 = (sections.get("section5") or "").strip()
    if s5:
        parts.append(f"{_SUB_INSIGHT}\n\n{s5}\n\n")
    else:
        parts.append(f"{_SUB_INSIGHT}\n\n*(결론 본문이 비어 있습니다.)*\n\n")

    parts.append(f"{_SUB_CONCLUSION_SUMMARY}\n\n")
    parts.append(_conclusion_summary_from_section0(summary_body) + "\n\n")

    parts.append("---\n\n")
    parts.append("## 참고문헌\n\n")
    ref_body = (sections.get("section6") or "").strip()
    if not ref_body:
        ref_body = (
            "*※ 참고문헌: 수집된 `raw_findings`의 출처를 section6 노드에서 정리합니다. "
            "아래 부록에 파이프라인에서 추출한 URL·쿼리 커버리지가 이어집니다.*"
        )
    parts.append(ref_body + "\n\n")
    parts.append(
        build_reference_appendix_markdown(
            state.get("raw_findings") or [],
            query_coverage=state.get("query_coverage") or {},
            company_a=state.get("company_a"),
            company_b=state.get("company_b"),
            company_a_cleaned=state.get("company_a_cleaned"),
            company_b_cleaned=state.get("company_b_cleaned"),
            company_a_swot=state.get("company_a_swot"),
            company_b_swot=state.get("company_b_swot"),
        )
    )

    text = "".join(parts)
    if not text.endswith("\n"):
        text += "\n"
    return text


def merge_node(state: ReportGraphState) -> dict:
    final_report = build_final_report_markdown(state)
    stem = default_report_stem()
    md_path, pdf_path, pdf_ok = write_report_artifacts(
        final_report,
        output_dir=_DEFAULT_OUTPUT_DIR,
        stem=stem,
    )
    md_path_docs, pdf_path_docs, pdf_ok_docs = write_report_artifacts(
        final_report,
        output_dir=_DOCS_OUTPUT_DIR,
        stem=stem,
    )
    if pdf_ok and not pdf_ok_docs:
        try:
            dest_pdf = Path(pdf_path).name
            dest = _DOCS_OUTPUT_DIR / dest_pdf
            shutil.copy2(pdf_path, dest)
            pdf_path_docs = str(dest.resolve())
            pdf_ok_docs = True
        except OSError:
            pass

    health_md = build_pipeline_health_markdown(
        state,
        md_path=md_path_docs,
        pdf_path=pdf_path_docs if pdf_ok_docs else "",
        pdf_ok=pdf_ok_docs,
    )
    health_path = _DOCS_OUTPUT_DIR / f"report_pipeline_health_{stem}.md"
    try:
        health_path.write_text(health_md, encoding="utf-8")
    except OSError:
        pass

    warnings = list(state.get("warnings") or [])
    if not pdf_ok:
        warnings.append(
            "PDF 변환 실패(WeasyPrint·fpdf2 모두 실패 또는 한글 폰트 없음). REPORT_PDF_FONT로 .ttf 지정 가능. Markdown은 저장됨."
        )
    if not pdf_ok_docs and pdf_ok:
        warnings.append("docs/ 폴더에 PDF 저장이 실패했습니다. report/final의 PDF를 확인하세요.")

    sec = state.get("sections") or {}
    for key in ("section0", "section1", "section2", "section3", "section4", "section5", "section6"):
        body = (sec.get(key) or "").strip()
        if not body:
            warnings.append(
                f"보고서 섹션 누락: {key} — 본문이 비어 있습니다. pipeline_health 파일을 확인하세요."
            )

    return {
        "final_report": final_report,
        "final_report_md_path": md_path,
        "final_report_pdf_path": pdf_path if pdf_ok else "",
        "final_report_docs_md_path": md_path_docs,
        "final_report_docs_pdf_path": pdf_path_docs if pdf_ok_docs else "",
        "report_file_path": primary_report_path(md_path, pdf_path, pdf_ok),
        "warnings": warnings,
    }


def merge_sections_markdown(sections: dict) -> str:
    """테스트용: sections dict만으로 본문 생성 (파일 저장 없음)."""
    return build_final_report_markdown({"sections": sections})
