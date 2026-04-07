"""LLM, VectorDB 초기화 및 공통 설정."""

import os
from pathlib import Path

import src.core.env  # noqa: F401 — 프로젝트 .env 선로드 (OPENAI_API_KEY)
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import chromadb
from chromadb.config import Settings

# env 모듈 이후에도 cwd 기준 .env 보조 (이중 호출 무방)
load_dotenv()

# ----------------------------------------------------------------
# Paths
# ----------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[2]
VECTORDB_DIR = ROOT_DIR / "data" / "vectordb"
RAW_DATA_DIR = ROOT_DIR / "data" / "raw"

VECTORDB_DIR.mkdir(parents=True, exist_ok=True)
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------
# LLM
# ----------------------------------------------------------------
def get_llm(temperature: float = 0.0) -> ChatOpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
    return ChatOpenAI(model="gpt-4o-mini", temperature=temperature, api_key=api_key)


# ----------------------------------------------------------------
# Chroma Client
# ----------------------------------------------------------------
def get_chroma_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(
        path=str(VECTORDB_DIR),
        settings=Settings(anonymized_telemetry=False),
    )


CHROMA_COLLECTION_NAME = "lges_catl_docs"
