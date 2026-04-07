"""Markdown 보고서를 PDF로 저장.

`startup-invest-agent/src/report/pdf_export.py` 와 동일하게 **파일 경로 API** ``md_to_pdf(md_path, pdf_path)``
를 제공한다 (보고서를 .md로 저장한 뒤 PDF 변환할 때 사용).

구현:
1) WeasyPrint (GTK/Pango 등이 있을 때, HTML/CSS 품질 우선)
2) **fpdf2** 폴백 — WeasyPrint 불가 시 (macOS 등) 네이티브 GTK 없이 PDF 생성

환경변수:

- ``REPORT_PDF_FONT`` — fpdf2 폴백 시 사용할 .ttf 절대 경로 (선택).
- ``REPORT_MD_ENCODING`` — 보고서 ``.md`` 파일 인코딩. 기본값 ``cp949`` (한국 Windows 메모장 등과 호환).
  UTF-8로 저장하려면 ``utf-8`` 또는 ``utf-8-sig`` 로 설정.
"""

from __future__ import annotations

import os
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Iterator, Optional, Tuple


def report_md_encoding() -> str:
    """보고서 Markdown 파일 입출력에 쓰는 코덱 이름. 기본 ``cp949``."""
    enc = os.environ.get("REPORT_MD_ENCODING", "cp949").strip()
    return enc or "cp949"


def _normalize_korean_text(text: str) -> str:
    """유니코드 정규화: BOM 제거, 한글 조합형 NFC."""
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="replace")
    text = text.lstrip("\ufeff")
    return unicodedata.normalize("NFC", text)


def _md_to_html_body(md_text: str) -> str:
    import markdown

    md_text = _normalize_korean_text(md_text)
    return markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "nl2br"],
    )


def _weasyprint_html(md_text: str) -> str:
    """WeasyPrint용 전체 HTML + 스타일."""
    html_body = _md_to_html_body(md_text)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
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
    p {{ margin: 0.35em 0; text-align: left; line-height: 1.65; word-break: keep-all; overflow-wrap: anywhere; }}
    li {{ line-height: 1.55; text-align: left; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1em 0; font-size: 9.5pt; table-layout: auto; page-break-inside: auto; }}
    thead {{ display: table-header-group; }}
    tr {{ page-break-inside: avoid; }}
    th, td {{ border: 1px solid #ccc; padding: 6px 8px; text-align: left; vertical-align: top;
             word-wrap: break-word; overflow-wrap: anywhere; hyphens: manual; }}
    th {{ background: #f0f0f0; }}
    ul, ol {{ margin: 0.5em 0; padding-left: 1.5em; }}
    hr {{ border: none; border-top: 1px solid #ddd; margin: 1.2em 0; }}
    @page {{ size: A4; margin: 2cm; }}
  </style>
</head>
<body>
{html_body}
</body>
</html>"""


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
    # macOS
    yield Path("/Library/Fonts/Arial Unicode.ttf")
    yield Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf")
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
    """``REPORT_MD_ENCODING``(기본 cp949)으로 디코드. UTF-8로 저장된 기존 파일은 자동 폴백."""
    raw = md_path.read_bytes()
    primary = report_md_encoding()
    try:
        return raw.decode(primary)
    except UnicodeDecodeError:
        pass
    for fallback in ("utf-8-sig", "utf-8"):
        try:
            return raw.decode(fallback)
        except UnicodeDecodeError:
            continue
    return raw.decode(primary, errors="replace")


def md_to_pdf(md_path: str | Path, pdf_path: str | Path) -> bool:
    """
    Markdown **파일** → PDF (startup-invest-agent ``md_to_pdf`` 와 동일 사용 패턴).

    1. ``md_path`` 를 ``report_md_encoding()``(기본 cp949)로 읽고, 실패 시 UTF-8 폴백
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
    # cp949에 없는 문자(이모지 등)는 U+FFFD로 대체해 파이프라인이 중단되지 않게 함
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
