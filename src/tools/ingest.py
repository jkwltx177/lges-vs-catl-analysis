"""PDF → Markdown → 구조 기반 청킹 → BGE-M3 임베딩 → Chroma 적재.

실행 방법:
    python src/tools/ingest.py
    python src/tools/ingest.py --file data/raw/LGES_사업보고서_2026.pdf

파일명 규칙:
    {company}_{doc_name}_{year}.pdf
    예: LGES_사업보고서_2026.pdf
"""

import argparse
import re
import uuid
from pathlib import Path
from typing import Dict, List

import pymupdf4llm

from src.core.config import (
    CHROMA_COLLECTION_NAME,
    RAW_DATA_DIR,
    get_chroma_client,
    get_llm,
)
from src.tools.vectordb_tool import embed_texts


# ----------------------------------------------------------------
# 파일명 메타데이터 파싱
# ----------------------------------------------------------------

def parse_filename_metadata(filename: str) -> Dict:
    """파일명에서 company / doc_name / year 추출.

    규칙: {company}_{doc_name}_{year}.pdf
    파싱 실패 시 가능한 범위까지 채움.
    """
    stem = Path(filename).stem
    parts = stem.split("_")
    meta = {
        "company": parts[0] if len(parts) > 0 else "unknown",
        "doc_name": parts[1] if len(parts) > 1 else "unknown",
        "year": parts[2] if len(parts) > 2 else "unknown",
        "source_file": filename,
    }
    return meta


# ----------------------------------------------------------------
# Markdown 구조 기반 청킹
# ----------------------------------------------------------------

TABLE_RE = re.compile(r"(\|.+\|[\s\S]*?)(?=\n\n|\Z)", re.MULTILINE)
HEADING_RE = re.compile(r"(?=^#{1,3} .+)", re.MULTILINE)
BULLET_RE = re.compile(r"((?:^[ \t]*[-*] .+\n?)+)", re.MULTILINE)


def _extract_tables(markdown: str) -> List[Dict]:
    """Markdown 내 table 블록 추출."""
    tables = []
    for m in TABLE_RE.finditer(markdown):
        text = m.group(0).strip()
        if text.count("|") >= 4:  # 최소 유효 표 기준
            tables.append({"text": text, "span": m.span()})
    return tables


def _summarize_table(table_md: str, llm, base_meta: Dict) -> str:
    """LLM으로 표 설명 2~3문장 생성."""
    company = base_meta.get("company", "")
    prompt = (
        f"다음 표는 {company} 관련 문서에서 추출되었습니다.\n"
        "이 표가 무엇을 나타내는지 2~3문장으로 설명하세요.\n"
        "수치나 핵심 비교 포인트를 포함하세요.\n\n"
        f"[표]\n{table_md}"
    )
    response = llm.invoke(prompt)
    return response.content.strip()


def chunk_by_structure(markdown: str, llm, base_meta: Dict) -> List[Dict]:
    """Markdown을 구조 기반(heading / table / bullet / paragraph)으로 청킹.

    Returns:
        [{"content": ..., "metadata": {...}}, ...]
    """
    chunks: List[Dict] = []
    chunk_index = 0

    # 1. 표 블록 먼저 추출 (위치 기록, 이후 heading 분할 시 제외)
    table_spans = []
    for t in _extract_tables(markdown):
        summary = _summarize_table(t["text"], llm, base_meta)
        content = f"[표 설명]\n{summary}\n\n[원문 표]\n{t['text']}"
        meta = {
            **base_meta,
            "chunk_type": "table",
            "chunk_index": chunk_index,
        }
        chunks.append({"content": content, "metadata": meta})
        table_spans.append(t["span"])
        chunk_index += 1

    # 표 위치를 markdown에서 플레이스홀더로 교체 (중복 청킹 방지)
    cleaned = markdown
    for start, end in sorted(table_spans, reverse=True):
        cleaned = cleaned[:start] + "\n\n" + cleaned[end:]

    # 2. heading(##, ###) 단위로 분할
    sections = HEADING_RE.split(cleaned)
    for section in sections:
        section = section.strip()
        if not section:
            continue

        # 3. section 내 bullet list 블록 추출
        bullet_matches = list(BULLET_RE.finditer(section))
        bullet_spans = [m.span() for m in bullet_matches]

        for m in bullet_matches:
            bullet_text = m.group(0).strip()
            if len(bullet_text) < 50:
                continue
            meta = {
                **base_meta,
                "chunk_type": "bullet",
                "chunk_index": chunk_index,
            }
            chunks.append({"content": bullet_text, "metadata": meta})
            chunk_index += 1

        # bullet을 제거한 나머지 → heading / paragraph
        remaining = section
        for start, end in sorted(bullet_spans, reverse=True):
            remaining = remaining[:start] + remaining[end:]
        remaining = remaining.strip()

        if remaining:
            chunk_type = "heading" if remaining.startswith("#") else "paragraph"
            if len(remaining) < 80:
                continue
            meta = {
                **base_meta,
                "chunk_type": chunk_type,
                "chunk_index": chunk_index,
            }
            chunks.append({"content": remaining, "metadata": meta})
            chunk_index += 1

    return chunks


# ----------------------------------------------------------------
# PDF → Markdown 변환
# ----------------------------------------------------------------

def pdf_to_markdown(pdf_path: str) -> str:
    """pymupdf4llm으로 PDF를 Markdown으로 변환."""
    return pymupdf4llm.to_markdown(pdf_path)

# ----------------------------------------------------------------
# Chroma 적재
# ----------------------------------------------------------------

def ingest_pdf(pdf_path: str, llm=None) -> int:
    """단일 PDF 파일을 청킹 후 Chroma에 적재.

    Returns:
        적재된 청크 수
    """
    if llm is None:
        llm = get_llm()

    filename = Path(pdf_path).name
    base_meta = parse_filename_metadata(filename)

    # 중복 체크: source_file 기준으로 이미 적재된 경우 skip
    client = get_chroma_client()
    try:
        collection = client.get_collection(CHROMA_COLLECTION_NAME)
        existing = collection.get(where={"source_file": filename}, limit=1)
        if existing["ids"]:
            print(f"[ingest] {filename} 이미 적재됨 — 건너뜀")
            return 0
    except Exception:
        pass  # collection 없으면 그냥 진행

    print(f"[ingest] {filename} 변환 중...")
    markdown = pdf_to_markdown(pdf_path)
    processed_dir = Path("data/processed/md")
    processed_dir.mkdir(parents=True, exist_ok=True)

    md_path = processed_dir / f"{Path(pdf_path).stem}.md"
    md_path.write_text(markdown, encoding="utf-8")
    print(f"[ingest] Markdown 저장 완료: {md_path}")    

    print(f"[ingest] 구조 청킹 중...")
    chunks = chunk_by_structure(markdown, llm, base_meta)
    print(f"[ingest] {len(chunks)}개 청크 생성")

    if not chunks:
        print(f"[ingest] 청크 없음, 건너뜀")
        return 0

    texts = [c["content"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    ids = [str(uuid.uuid4()) for _ in chunks]

    print(f"[ingest] BGE-M3 임베딩 생성 중...")
    embeddings = embed_texts(texts)

    client = get_chroma_client()
    try:
        collection = client.get_collection(CHROMA_COLLECTION_NAME)
    except Exception:
        collection = client.create_collection(
            CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    # 배치 단위로 적재 (Chroma 권장 최대 ~5000)
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        collection.add(
            ids=ids[i : i + batch_size],
            embeddings=embeddings[i : i + batch_size],
            documents=texts[i : i + batch_size],
            metadatas=metadatas[i : i + batch_size],
        )

    print(f"[ingest] {filename} → {len(chunks)}개 청크 적재 완료")
    return len(chunks)


def ingest_all(data_dir: str = None) -> None:
    """data/raw/ 내 모든 PDF 파일을 일괄 적재."""
    directory = Path(data_dir) if data_dir else RAW_DATA_DIR
    pdfs = list(directory.glob("*.pdf"))
    if not pdfs:
        print(f"[ingest] {directory}에 PDF 파일이 없습니다.")
        return

    llm = get_llm()
    total = 0
    for pdf in pdfs:
        total += ingest_pdf(str(pdf), llm)
    print(f"\n[ingest] 전체 완료: {len(pdfs)}개 파일, {total}개 청크 적재")


# ----------------------------------------------------------------
# CLI 진입점
# ----------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF → Chroma 인제스트")
    parser.add_argument("--file", type=str, help="단일 PDF 파일 경로 (생략 시 data/raw/ 전체)")
    args = parser.parse_args()

    if args.file:
        ingest_pdf(args.file)
    else:
        ingest_all()
