"""Markdown 보고서를 PDF로 저장.

`startup-invest-agent/src/report/pdf_export.py` 와 동일하게 **파일 경로 API** ``md_to_pdf(md_path, pdf_path)``
를 제공한다 (보고서를 .md로 저장한 뒤 PDF 변환할 때 사용).

구현:
1) WeasyPrint (GTK/Pango 등이 있을 때, HTML/CSS 품질 우선)
2) **fpdf2** 폴백 — WeasyPrint 불가 시 (macOS 등) 네이티브 GTK 없이 PDF 생성

환경변수:

- ``REPORT_PDF_FONT`` — fpdf2 폴백 시 사용할 .ttf 절대 경로 (선택). 미지정 시 Arial Unicode 등 시도.
- ``REPORT_MD_ENCODING`` — 보고서 ``.md`` 파일 인코딩. 기본값 ``utf-8`` (한글·에디터 호환).
  레거시 메모장(cp949)만 쓸 때 ``cp949`` 로 설정.

PDF 본문은 WeasyPrint에서 **Arial** 우선(한글은 Arial Unicode 등으로 폴백).
"""

from __future__ import annotations

import os
import re
import unicodedata
from html import escape
from datetime import date, datetime
from pathlib import Path
from typing import Iterator, Optional, Tuple


def report_md_encoding() -> str:
    """보고서 Markdown 파일 입출력에 쓰는 코덱 이름. 기본 ``utf-8``."""
    enc = os.environ.get("REPORT_MD_ENCODING", "utf-8").strip()
    return enc or "utf-8"


def _normalize_korean_text(text: str) -> str:
    """유니코드 정규화: BOM 제거, 한글 조합형 NFC."""
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    text = text.lstrip("\ufeff")
    return unicodedata.normalize("NFC", text)


def _md_to_html_body(md_text: str) -> str:
    import markdown

    md_text = _normalize_korean_text(md_text)
    extensions = ["tables", "fenced_code", "nl2br"]

    title_match = re.search(r"^\s*#\s+(.+?)\s*$", md_text, re.MULTILINE)
    summary_match = re.search(
        r"(?s)^\s*#\s+.+?\n+##\s+SUMMARY\s*\n+(.*?)\n+---\s*\n+",
        md_text,
    )
    if not title_match or not summary_match:
        return markdown.markdown(
            md_text,
            extensions=extensions,
        )

    title = title_match.group(1).strip()
    summary_md = summary_match.group(1).strip()
    body_md = re.sub(
        r"(?s)^\s*#\s+.+?\n+##\s+SUMMARY\s*\n+.*?\n+---\s*\n+",
        "",
        md_text,
        count=1,
    ).strip()

    date_match = re.search(r"\*\*작성일:\*\*\s*(.+)", body_md)
    report_date = date_match.group(1).strip() if date_match else ""
    if date_match:
        body_md = re.sub(r"\*\*작성일:\*\*\s*.+\n*", "", body_md, count=1).strip()

    toc_match = re.search(r"(?s)^##\s+목차\s*\n+(.*?)\n+---\s*\n+", body_md)
    toc_md = toc_match.group(1).strip() if toc_match else ""
    if toc_match:
        body_md = re.sub(
            r"(?s)^##\s+목차\s*\n+.*?\n+---\s*\n+",
            "",
            body_md,
            count=1,
        ).strip()

    summary_html = markdown.markdown(summary_md, extensions=extensions)
    toc_html = markdown.markdown(toc_md, extensions=extensions) if toc_md else ""
    body_html = markdown.markdown(body_md, extensions=extensions)
    return f"""
<div class="report-cover">
  <div class="cover-kicker">EV BATTERY STRATEGY REPORT</div>
  <h1>{escape(title)}</h1>
  <p class="cover-deck">
    전기차 캐즘 시기 LGES와 CATL의 시장 환경, 포트폴리오, comparative SWOT, 회복탄력성, 전략적 시사점을 정리한 비교 분석 보고서
  </p>
  <div class="cover-meta">
    {f'<span>{escape(report_date)}</span>' if report_date else ''}
    <span>Research → Refine → Analysis → Report</span>
  </div>
</div>
<section class="summary-panel">
  <div class="summary-label">Executive Summary</div>
  <h2>SUMMARY</h2>
  {summary_html}
</section>
{f'''<section class="toc-panel">
  <div class="summary-label">Contents</div>
  <h2>목차</h2>
  {toc_html}
</section>''' if toc_html else ''}
<div class="report-body">
  {body_html}
</div>
"""


def _weasyprint_css() -> str:
    return """
    :root {
      --ink: #1d2733;
      --muted: #5a6573;
      --line: #d7dee7;
      --line-strong: #94a3b8;
      --panel: #f5f7fa;
      --panel-strong: #e2ebf4;
      --accent: #0f4c81;
      --accent-soft: #d9e7f3;
      --accent-dark: #0a3559;
      --accent-ink: #12324f;
    }
    body {
      font-family: Arial, "Arial Unicode MS", "Helvetica Neue", Helvetica, sans-serif;
      font-size: 10.2pt;
      line-height: 1.7;
      margin: 0;
      padding: 0;
      color: var(--ink);
      background: #fff;
    }
    .report-cover {
      margin: 0 0 1.4cm 0;
      padding: 1.2cm 0 0.9cm 0;
      border-top: 10px solid var(--accent);
      border-bottom: 1px solid var(--line);
      min-height: 6.8cm;
      background:
        linear-gradient(135deg, rgba(15, 76, 129, 0.06) 0%, rgba(15, 76, 129, 0) 58%),
        linear-gradient(180deg, #ffffff 0%, #f9fbfd 100%);
    }
    .cover-kicker {
      font-size: 8.4pt;
      font-weight: 700;
      letter-spacing: 0.22em;
      color: var(--accent);
      text-transform: uppercase;
      margin-bottom: 0.45cm;
    }
    .report-cover h1,
    h1 {
      font-size: 22pt;
      font-weight: 800;
      line-height: 1.2;
      margin: 0;
      color: #0f172a;
      border-bottom: none;
      padding-bottom: 0;
      max-width: 90%;
    }
    .cover-deck {
      margin: 0.5cm 0 0 0;
      max-width: 78%;
      color: var(--muted);
      font-size: 10.6pt;
      line-height: 1.72;
    }
    .cover-meta {
      margin-top: 0.75cm;
    }
    .cover-meta span {
      display: inline-block;
      margin-right: 0.24cm;
      margin-bottom: 0.18cm;
      padding: 6px 10px;
      border: 1px solid #c6d4e3;
      border-radius: 999px;
      font-size: 8.7pt;
      font-weight: 700;
      color: var(--accent-ink);
      background: rgba(255, 255, 255, 0.92);
    }
    .summary-panel {
      margin: 0 0 1cm 0;
      padding: 0.6cm 0.7cm;
      background: linear-gradient(180deg, var(--panel) 0%, #ffffff 100%);
      border: 1px solid var(--line);
      border-left: 6px solid var(--accent);
      border-radius: 8px;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04);
    }
    .toc-panel {
      margin: 0 0 1cm 0;
      padding: 0.52cm 0.65cm;
      background: #fff;
      border: 1px solid var(--line);
      border-top: 3px solid var(--accent-soft);
      border-radius: 8px;
    }
    .summary-label {
      font-size: 8.4pt;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--accent);
      margin-bottom: 0.15cm;
    }
    .summary-panel h2 {
      margin-top: 0;
      border-bottom: none;
      padding-bottom: 0;
    }
    .toc-panel h2 {
      margin-top: 0;
      border-bottom: none;
      padding-bottom: 0;
    }
    .toc-panel ol {
      margin: 0.3em 0 0 0;
      padding-left: 1.2em;
    }
    .toc-panel li {
      margin: 0.24em 0;
      color: #334155;
    }
    .report-body {
      margin-top: 0.2cm;
    }
    .report-body > h2 {
      break-before: auto;
      page-break-before: auto;
    }
    h2 {
      font-size: 13.8pt;
      font-weight: 800;
      margin: 1.3em 0 0.58em 0;
      page-break-after: avoid;
      color: #0f172a;
      border-bottom: 2px solid var(--accent-soft);
      padding-bottom: 0.18em;
    }
    h3 {
      font-size: 11.5pt;
      font-weight: 800;
      margin: 1.12em 0 0.4em 0;
      page-break-after: avoid;
      color: var(--accent-dark);
    }
    h4 {
      font-size: 10.6pt;
      font-weight: 700;
      margin: 0.9em 0 0.35em 0;
      color: #334155;
    }
    p {
      margin: 0.38em 0;
      text-align: left;
      line-height: 1.68;
      word-break: keep-all;
      overflow-wrap: anywhere;
    }
    em, i { font-style: italic; }
    strong { font-weight: 800; color: #111827; }
    li {
      line-height: 1.58;
      text-align: left;
      margin: 0.18em 0;
    }
    table {
      border-collapse: collapse;
      width: 100%;
      margin: 0.95em 0 1.1em 0;
      font-size: 8.9pt;
      table-layout: auto;
      page-break-inside: auto;
      border: 1px solid var(--line);
    }
    thead { display: table-header-group; }
    tr { page-break-inside: avoid; }
    tbody tr:nth-child(even) td {
      background: #fafbfd;
    }
    th, td {
      border: 1px solid var(--line);
      padding: 7px 9px;
      text-align: left;
      vertical-align: top;
      word-wrap: break-word;
      overflow-wrap: anywhere;
      hyphens: manual;
    }
    th {
      background: var(--accent);
      color: #fff;
      font-weight: 700;
      border-color: var(--accent);
    }
    ul, ol {
      margin: 0.45em 0;
      padding-left: 1.35em;
    }
    hr {
      border: none;
      border-top: 1px solid var(--line-strong);
      margin: 1.3em 0;
    }
    blockquote {
      margin: 0.8em 0;
      padding: 0.2em 0 0.2em 0.75em;
      border-left: 4px solid var(--accent-soft);
      color: var(--muted);
      background: #fbfcfe;
    }
    img {
      max-width: 100%;
      height: auto;
    }
    code, pre {
      font-family: Consolas, "Courier New", monospace;
      font-size: 8.8pt;
    }
    pre {
      background: #f8fafc;
      border: 1px solid var(--line);
      padding: 0.35cm;
      border-radius: 4px;
      overflow: hidden;
    }
    @page {
      size: A4;
      margin: 1.7cm 1.75cm 1.85cm 1.75cm;
      @top-right {
        content: "LGES vs CATL";
        color: #64748b;
        font-size: 8pt;
      }
      @bottom-left {
        content: "EV Battery Strategy Report";
        color: #94a3b8;
        font-size: 8pt;
      }
      @bottom-right {
        content: counter(page);
        color: #64748b;
        font-size: 8pt;
      }
    }
    @page :first {
      @top-right {
        content: "";
      }
      @bottom-left {
        content: "";
      }
    }
    """


def _render_html(md_text: str) -> str:
    html_body = _md_to_html_body(md_text)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
  <style>
{_weasyprint_css()}
  </style>
</head>
<body>
{html_body}
</body>
</html>"""


def _weasyprint_html(md_text: str) -> str:
    """WeasyPrint용 전체 HTML + 스타일."""
    return _render_html(md_text)


def _try_import_weasyprint():
    """GTK/Pango 미설치 시 import 단계에서 실패할 수 있음. 콘솔 스팸 억제."""
    import contextlib
    import io

    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            import weasyprint  # noqa: F401

            return True
        except Exception:
            return False


def markdown_to_pdf_weasyprint(md_text: str, pdf_path: str | Path) -> bool:
    if not _try_import_weasyprint():
        return False
    try:
        from weasyprint import HTML
        from weasyprint.text.fonts import FontConfiguration

        full_html = _weasyprint_html(md_text)
        pdf_path = Path(pdf_path)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        font_config = FontConfiguration()
        # 일부 WeasyPrint 버전은 string 입력에 encoding 인자를 받지 않음
        try:
            HTML(string=full_html, encoding="utf-8").write_pdf(
                str(pdf_path), font_config=font_config
            )
        except TypeError:
            HTML(string=full_html).write_pdf(str(pdf_path), font_config=font_config)
        return True
    except Exception:
        return False


def _iter_font_paths() -> Iterator[Path]:
    env = os.environ.get("REPORT_PDF_FONT", "").strip()
    if env:
        yield Path(env)
    # macOS — Arial 계열 유니코드(한글) 우선, 순수 Arial.ttf는 한글 미지원이라 후순위
    yield Path("/Library/Fonts/Arial Unicode.ttf")
    yield Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")
    yield Path("/System/Library/Fonts/Supplemental/Arial.ttf")
    # Windows
    yield Path(r"C:\Windows\Fonts\malgun.ttf")
    yield Path(r"C:\Windows\Fonts\arialuni.ttf")
    # Linux (Noto 패키지)
    yield Path("/usr/share/fonts/truetype/noto/NotoSansKR-Regular.ttf")
    yield Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")


def _register_fpdf_unicode_font(pdf) -> str:
    """fpdf2에 CJK 지원 폰트 등록. 성공 시 패밀리 이름."""
    last_err: Exception | None = None
    for font_path in _iter_font_paths():
        if not font_path.is_file():
            continue
        try:
            p = str(font_path.resolve())
            for style in ("", "B", "I", "BI"):
                pdf.add_font("ReportPDF", style, p)
            return "ReportPDF"
        except Exception as e:
            last_err = e
            continue
    msg = (
        "한글 PDF용 .ttf 폰트를 찾지 못했습니다. "
        "macOS: Arial Unicode / Windows: 맑은 고딕 / Linux: NotoSansKR-Regular.ttf 설치, "
        "또는 환경변수 REPORT_PDF_FONT=/절대경로/폰트.ttf 를 설정하세요."
    )
    if last_err:
        raise RuntimeError(f"{msg} (마지막 오류: {last_err})") from last_err
    raise RuntimeError(msg)


def markdown_to_pdf_fpdf2(md_text: str, pdf_path: str | Path) -> bool:
    """fpdf2 — 시스템 GTK 없이 Markdown→HTML→PDF."""
    try:
        from fpdf import FPDF
        from fpdf.fonts import TextStyle
    except ImportError:
        return False

    html_body = _md_to_html_body(md_text)
    pdf_path = Path(pdf_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    pdf = FPDF()
    pdf.set_margins(14, 16, 14)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    try:
        _register_fpdf_unicode_font(pdf)
    except Exception:
        return False
    pdf.set_font("ReportPDF", size=10)
    # fpdf2는 tag_styles에 DEFAULT_TAG_STYLES에 없는 태그(예: td/th)를 넣으면 NotImplementedError —
    # SWOT 등 표가 있는 보고서에서 PDF 전체가 실패한다. 표 셀 스타일은 생략하고 내장 렌더러에 맡긴다.
    tag_styles = {
        "p": TextStyle(font_size_pt=10, t_margin=1, b_margin=2.5),
        "h1": TextStyle(font_size_pt=14, t_margin=2, b_margin=3),
        "h2": TextStyle(font_size_pt=12, t_margin=4, b_margin=2),
        "h3": TextStyle(font_size_pt=11, t_margin=3, b_margin=2),
        "li": TextStyle(font_size_pt=10, t_margin=0.5, b_margin=1),
    }
    try:
        # `<code>`/`<pre>` 기본이 Courier라 한글이 깨짐 — 유니코드 TTF(ReportPDF)로 통일
        pdf.write_html(
            html_body,
            table_line_separators=True,
            tag_styles=tag_styles,
            pre_code_font="ReportPDF",
        )
    except Exception:
        return False
    try:
        pdf.output(str(pdf_path))
    except Exception:
        return False
    return pdf_path.is_file() and pdf_path.stat().st_size > 0


def markdown_to_pdf(md_text: str, pdf_path: str | Path) -> bool:
    """
    Markdown 문자열 → PDF.
    WeasyPrint 우선, 실패 시 fpdf2.
    """
    pdf_path = Path(pdf_path)
    if markdown_to_pdf_weasyprint(md_text, pdf_path):
        return True
    return markdown_to_pdf_fpdf2(md_text, pdf_path)


def _read_report_md_file(md_path: Path) -> str:
    """주 인코딩으로 디코드 후, 실패 시 utf-8·cp949 순으로 폴백(한글 깨짐 방지)."""
    raw = md_path.read_bytes()
    primary = report_md_encoding()
    order: list[str] = []
    for enc in (primary, "utf-8-sig", "utf-8", "cp949"):
        if enc not in order:
            order.append(enc)
    for enc in order:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def md_to_pdf(md_path: str | Path, pdf_path: str | Path) -> bool:
    """
    Markdown **파일** → PDF (startup-invest-agent ``md_to_pdf`` 와 동일 사용 패턴).

    1. ``md_path`` 를 ``report_md_encoding()``(기본 utf-8)로 읽고, 실패 시 다른 인코딩 폴백
    2. ``markdown_to_pdf`` 로 ``pdf_path`` 에 저장 (내부는 유니코드 → PDF 엔진)

    실패 시 ``False`` → 호출부가 .md 경로만 쓰도록 처리 가능.
    """
    md_path = Path(md_path)
    if not md_path.is_file():
        return False
    md_text = _read_report_md_file(md_path)
    return markdown_to_pdf(md_text, pdf_path)


def write_report_artifacts(
    md_text: str,
    *,
    output_dir: Path,
    stem: str,
) -> Tuple[str, str, bool]:
    """
    startup-invest-agent ``_save_report_as_pdf`` 와 같이 **먼저 .md 저장 → ``md_to_pdf``**.

    Returns: (md_path_str, pdf_path_str, pdf_ok)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    md_path = output_dir / f"{stem}.md"
    pdf_path = output_dir / f"{stem}.pdf"
    enc = report_md_encoding()
    # utf-8은 한글·이모지 대부분 보존. cp949 등에서만 대체 문자 발생 가능
    md_path.write_text(md_text, encoding=enc, errors="replace")
    pdf_ok = md_to_pdf(md_path, pdf_path)
    return str(md_path.resolve()), str(pdf_path.resolve()) if pdf_ok else "", pdf_ok


def primary_report_path(md_path: str | Path, pdf_path: str | Path, pdf_ok: bool) -> str:
    """
    startup-invest-agent ``_save_report_as_pdf`` 반환값과 동일한 우선순위:
    PDF 성공 시 PDF 절대경로, 실패 시 MD 절대경로.
    """
    md_path = Path(md_path).resolve()
    if pdf_ok and pdf_path:
        p = Path(pdf_path)
        if p.is_file():
            return str(p.resolve())
    return str(md_path)


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
