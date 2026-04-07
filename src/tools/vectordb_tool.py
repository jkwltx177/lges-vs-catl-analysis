"""BGE-M3 임베딩 + Chroma VectorDB 검색 도구."""

from typing import Any, Dict, List, Optional, cast

from src.core.config import CHROMA_COLLECTION_NAME, get_chroma_client

# BGE-M3 모델은 최초 호출 시 lazy load (무거운 의존성)
_model = None


def _get_model():
    global _model
    if _model is None:
        try:
            from FlagEmbedding import BGEM3FlagModel
            _model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
        except ImportError as e:
            raise ImportError(
                "FlagEmbedding 패키지가 없습니다. "
                "`pip install FlagEmbedding` 후 재시도하세요."
            ) from e
    return _model


def embed_texts(texts: List[str]) -> List[List[float]]:
    """텍스트 목록을 BGE-M3로 임베딩하여 벡터 목록 반환."""
    model = _get_model()
    result = cast(Dict[str, Any], model.encode(texts, batch_size=12, max_length=8192))
    # dense_vecs는 numpy array 또는 list 형태이며, 각 요소는 float 리스트여야 함
    # np.float16은 ChromaDB에서 오류를 유발할 수 있으므로 표준 float으로 변환
    return [[float(x) for x in vec] for vec in result["dense_vecs"]]


def vectordb_search(
    query: str,
    n_results: int = 5,
    where: Optional[Dict] = None,
) -> List[Dict]:
    """Chroma에서 쿼리와 가장 유사한 청크를 반환.

    Args:
        query: 검색 쿼리 문자열
        n_results: 반환할 결과 수
        where: Chroma 메타데이터 필터 (예: {"company": "LGES"})

    Returns:
        [{"content": ..., "metadata": {...}, "distance": ...}, ...]
    """
    client = get_chroma_client()
    try:
        collection = client.get_collection(CHROMA_COLLECTION_NAME)
    except Exception:
        return []

    query_embedding = embed_texts([query])[0]

    kwargs = {"query_embeddings": [query_embedding], "n_results": n_results}
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)

    docs = []
    for i, doc_id in enumerate(results["ids"][0]):
        docs.append(
            {
                "id": doc_id,
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            }
        )
    return docs
