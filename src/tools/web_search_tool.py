"""Tavily 웹 검색 도구."""

import os
from typing import Dict, List

from tavily import TavilyClient


def _get_client() -> TavilyClient:
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        raise EnvironmentError("TAVILY_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
    return TavilyClient(api_key=api_key)


def web_search(query: str, max_results: int = 5) -> List[Dict]:
    """Tavily로 웹 검색 후 결과 목록 반환.

    Returns:
        [{"content": ..., "url": ..., "title": ..., "published_date": ...}, ...]
    """
    client = _get_client()
    response = client.search(
        query=query,
        search_depth="advanced",
        max_results=max_results,
        include_raw_content=True,
    )

    results = []
    for item in response.get("results", []):
        results.append(
            {
                "content": item.get("raw_content") or item.get("content", ""),
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "published_date": item.get("published_date", ""),
                "source_type": "web_search",
            }
        )
    return results
