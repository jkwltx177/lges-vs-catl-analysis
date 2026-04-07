"""Markdown 보고서를 PDF로 저장 (WeasyPrint). 실패 시 호출자가 MD만 사용."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Optional, Tuple


def markdown_to_pdf(md_text: str, pdf_path: str | Path) -> bool:
    """
    Markdown 문자열 → HTML → PDF.
    한글 본문에 맞게 기본 스타일 적용.
    """
    try:
        import markdown
        from weasyprint import HTML
        from weasyprint.text.fonts import FontConfiguration

        html_body = markdown.markdown(
            md_text,
            extensions=["tables", "fenced_code", "nl2br"],
        )
        full_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <style>
    body {{
      font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', 'Noto Sans KR', 'Helvetica Neue', sans-serif;
      font-size: 11pt;
      line-height: 1.55;
      margin: 2cm;
      color: #111;
    }}
    h1 {{ font-size: 18pt; border-bottom: 2px solid #333; padding-bottom: 0.35em; margin-top: 0; }}
    h2 {{ font-size: 14pt; margin-top: 1.4em; page-break-after: avoid; }}
    h3 {{ font-size: 12pt; margin-top: 1em; page-break-after: avoid; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 10pt; }}
    th, td {{ border: 1px solid #ccc; padding: 6px 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f0f0f0; }}
    ul, ol {{ margin: 0.5em 0; padding-left: 1.5em; }}
    hr {{ border: none; border-top: 1px solid #ddd; margin: 1.2em 0; }}
    .meta-date {{ font-size: 11pt; color: #444; margin-bottom: 0.5em; }}
    @page {{ size: A4; margin: 2cm; }}
  </style>
</head>
<body>
{html_body}
</body>
</html>"""

        pdf_path = Path(pdf_path)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        font_config = FontConfiguration()
        HTML(string=full_html).write_pdf(str(pdf_path), font_config=font_config)
        return True
    except Exception:
        return False


def write_report_artifacts(
    md_text: str,
    *,
    output_dir: Path,
    stem: str,
) -> Tuple[str, str, bool]:
    """
    같은 stem으로 .md / .pdf 저장.
    Returns: (md_path_str, pdf_path_str, pdf_ok)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / f"{stem}.md"
    pdf_path = output_dir / f"{stem}.pdf"
    md_path.write_text(md_text, encoding="utf-8")
    pdf_ok = markdown_to_pdf(md_text, pdf_path)
    return str(md_path.resolve()), str(pdf_path.resolve()) if pdf_ok else "", pdf_ok


def default_report_stem(prefix: str = "lges_vs_catl_report") -> str:
    """파일명: prefix_YYYYMMDD_HHMMSS"""
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def parse_or_today(report_date: Optional[str]) -> date:
    if not report_date or not str(report_date).strip():
        return date.today()
    try:
        return date.fromisoformat(str(report_date).strip()[:10])
    except ValueError:
        return date.today()


def format_report_date_korean(d: date) -> str:
    return f"{d.year}년 {d.month}월 {d.day}일"
