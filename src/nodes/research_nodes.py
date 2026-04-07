"""Research Agent 14개 노드 구현."""

import json
import os
import re
from pathlib import Path
from typing import Dict, List
from datetime import datetime

from langgraph.types import interrupt

from src.core.config import RAW_DATA_DIR, get_llm
from src.state.state import ResearchFinding, ResearchGraphState
from src.tools.token_manager import update_token_usage
from src.tools.vectordb_tool import vectordb_search
from src.tools.web_search_tool import web_search

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = get_llm()
    return _llm


# ================================================================
# 1. initialize_node
# ================================================================

def initialize_node(state: ResearchGraphState) -> Dict:
    """goal / target_companies / report_topic 주입, 제어 필드 초기화."""
    return {
        "goal": state.get("goal", "LGES vs CATL SWOT 비교 분석"),
        "target_companies": state.get("target_companies", ["LGES", "CATL"]),
        "report_topic": state.get("report_topic", "EV 배터리 시장 경쟁력 분석"),
        "retry_count": 0,
        "max_retry": state.get("max_retry", 2),
        "token_usage": {},
        "summary_cache": {},
        "warnings": [],
        "human_review_flags": [],
        "raw_findings": [],
        "completed_agents": [],
    }


# ================================================================
# 2. query_generation_node
# ================================================================



# 1. 프롬프트 개선: 페르소나 주입 및 조사 카테고리 세분화
_QUERY_PROMPT = """\
당신은 10년 차 배터리 산업 전문 수석 애널리스트입니다. 
단순한 뉴스 검색을 넘어, 기업의 실질적인 경쟁력과 리스크를 파악할 수 있는 고품질 리서치 쿼리를 생성하세요.

[분석 환경]
- 현재 시점: {current_date}
- 목표: {goal}
- 대상 기업: {companies}
- 보고서 주제: {topic}

[요구사항]
- **SWOT 균형**: 강점/약점/기회/위협 각 축당 최소 3개씩, 총 12개 이상의 쿼리 생성.
- **심층 조사**: 단순 근황보다는 '재무 건전성', '특허 및 기술 로드맵', '공급망(LFP/하이니켈)', 'IRA/CRMA 정책 대응' 등 전문 영역을 포함할 것.
- **최신성**: 반드시 2025년 하반기 실적과 2026년 실시간 동향을 타겟팅할 것.
- **비교 분석**: 양사의 시장 점유율 역전 가능성이나 기술 격차를 직접 대조하는 쿼리 포함.

JSON 배열 형식으로만 출력하세요:
["쿼리1", "쿼리2", ...]
"""

def get_dynamic_fallback_queries(companies: List[str]) -> List[str]:
    """현재 연도(2026년)를 반영한 동적 Fallback 쿼리 생성"""
    curr_year = datetime.now().year # 2026
    c1, c2 = (companies[0], companies[1]) if len(companies) >= 2 else ("LGES", "CATL")
    
    return [
        f"{c1} {curr_year} 1분기 영업이익률 및 재무 건전성 분석",
        f"{c2} 유럽 LFP 배터리 공장 가동 현황 및 2026 점유율 전망",
        f"{c1} vs {c2} 차세대 전고체 배터리 특허 및 샘플 공급 현황",
        f"2026년 미국 IRA 보조금 정책 변화가 {c1} 북미 사업에 미치는 영향",
        f"{c2}의 헝가리 및 독일 생산 거점 효율성 및 물류 리스크",
        f"전기차 캐즘 돌파를 위한 {c1}의 ESS 사업 비중 확대 전략",
        f"{c2} 나트륨 이온 배터리 상용화 수준과 저가형 시장 지배력",
        f"{c1} 하이니켈 NCMA 배터리 수율 및 주요 고객사 이탈 여부",
        f"글로벌 완성차 업체(OEM)의 배터리 내재화가 {c1}, {c2}에 미치는 위협",
        f"2026년 배터리 리사이클링 시장 규모 및 {c1}의 합작법인(JV) 현황",
        f"{c2} 광산 지분 확보를 통한 원자재 수직 계열화 현황",
        f"리튬/니켈 가격 변동에 따른 {c1} vs {c2} 원가 경쟁력 비교"
    ]

def query_generation_node(state: ResearchGraphState) -> Dict:
    """LLM → 전문가적 관점의 SWOT 쿼리 생성 (최소 12개 보장)."""
    llm = _get_llm()
    target_companies = state.get("target_companies", ["LGES", "CATL"])
    companies_str = ", ".join(target_companies)
    
    # 현재 날짜 반영하여 최신성 강조
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    prompt = _QUERY_PROMPT.format(
        current_date=current_date,
        goal=state.get("goal", "상세 비교 분석"),
        companies=companies_str,
        topic=state.get("report_topic", "배터리 산업 분석"),
    )

    # 갭(Missing Topics) 보완 로직 강화
    missing = state.get("missing_topics", [])
    if missing:
        prompt += f"\n\n[중요] 이전 조사에서 다음 내용이 부족했습니다. 이를 보완할 초정밀 쿼리를 추가하세요:\n{missing}"

    try:
        response = llm.invoke(prompt)
        raw = response.content.strip()
        # JSON 배열 추출 정교화
        match = re.search(r"\[\s*?\".*?\"\s*?\]", raw, re.DOTALL)
        queries: List[str] = json.loads(match.group(0)) if match else []
    except Exception as e:
        print(f"[Query Gen Error] 파싱 실패: {e}")
        queries = []

    if len(queries) < 12:
        print(f"[Query Gen] 생성된 쿼리 부족({len(queries)}개). 동적 Fallback 쿼리를 주입합니다.")
        fallback = get_dynamic_fallback_queries(target_companies)
        queries = list(set(queries + fallback))[:12]

    return {"query_set": queries}


# ================================================================
# 3. strategy_routing_node
# ================================================================

_WEB_KEYWORDS = {"최신", "2026", "2025", "뉴스", "발표", "출시", "최근", "어제", "today", "news", "IRA", "CRMA", "policy"}
_VDB_KEYWORDS = {"전략", "IR", "사업보고서", "기술", "연구", "특허", "실적", "재무", "annual", "report" ,"JV", "yield"}
_MARKET_KEYWORDS = {"시장", "산업", "동향", "캐즘", "점유율", "tam", "cagr", "전망", "규모", "트렌드", "market", "industry"}
_LGES_KEYWORDS = {"lges", "lg에너지", "엘지에너지", "lgエネ"}
_CATL_KEYWORDS = {"catl", "닝더스다이", "寧德時代"}


def _classify_query(query: str) -> tuple:
    """(route, company_filter) 반환.

    company_filter: None(필터 없음) | "LGES" | "CATL" | "Market"
    """
    q_lower = query.lower()
    has_web = any(k in q_lower for k in _WEB_KEYWORDS)
    has_vdb = any(k in q_lower for k in _VDB_KEYWORDS)

    if has_web and not has_vdb:
        route = "web"
    else:
        route = "both"

    # company_filter 결정
    is_lges = any(k in q_lower for k in _LGES_KEYWORDS)
    is_catl = any(k in q_lower for k in _CATL_KEYWORDS)
    is_market = any(k in q_lower for k in _MARKET_KEYWORDS)

    if is_lges and not is_catl:
        company_filter = "LGES"
    elif is_catl and not is_lges:
        company_filter = "CATL"
    elif is_market and not is_lges and not is_catl:
        company_filter = "Market"
    else:
        company_filter = None  # 필터 없이 전체 검색

    return route, company_filter


def strategy_routing_node(state: ResearchGraphState) -> Dict:
    """쿼리 단위 map — 각 query에 route + company_filter 부여."""
    search_plan = []
    for query in state.get("query_set", []):
        route, company_filter = _classify_query(query)
        search_plan.append({"query": query, "route": route, "company_filter": company_filter})
    return {"search_plan": search_plan}


# ================================================================
# 4. vectordb_retrieval_node
# ================================================================

def vectordb_retrieval_node(state: ResearchGraphState) -> Dict:
    """search_plan에서 vectordb / both 쿼리를 필터링하여 VectorDB 검색.

    company_filter가 있으면 Chroma where 필터 적용
    (예: {"company": "LGES"} | {"company": "Market"})
    """
    plan = state.get("search_plan", [])
    target_queries = [p for p in plan if p["route"] in ("vectordb", "both")]

    docs = []
    for item in target_queries:
        company_filter = item.get("company_filter")
        where = {"company": company_filter} if company_filter else None
        results = vectordb_search(item["query"], n_results=5, where=where)
        for r in results:
            docs.append(
                {
                    "content": r["content"],
                    "metadata": r.get("metadata", {}),
                    "source_type": "vector_db",
                    "query": item["query"],
                    "distance": r.get("distance"),
                }
            )

    # operator.add reducer: 이번 노드에서 **추가분만** 반환 (전체 누적은 그래프가 처리)
    return {"raw_documents": docs}


# ================================================================
# 5. web_retrieval_node
# ================================================================

def web_retrieval_node(state: ResearchGraphState) -> Dict:
    """search_plan에서 web / both 쿼리를 필터링하여 Tavily 검색."""
    plan = state.get("search_plan", [])
    target_queries = [p for p in plan if p["route"] in ("web", "both")]

    docs = []
    for item in target_queries:
        results = web_search(item["query"], max_results=5)
        for r in results:
            docs.append(
                {
                    "content": r.get("content", ""),
                    "url": r.get("url", ""),
                    "title": r.get("title", ""),
                    "published_date": r.get("published_date", ""),
                    "source_type": "web_search",
                    "query": item["query"],
                }
            )

    return {"raw_documents": docs}


# ================================================================
# 6. company_research_node
# ================================================================

_COMPANY_RESEARCH_PROMPT = """\
다음 기업에 대해 분석용 핵심 정보를 수집하세요.

기업: {company}
조사 목표: {goal}

제공된 문서들을 바탕으로 아래를 **유효한 JSON 한 덩어리**로만 출력하세요 (코드펜스·설명 문장 금지).
정보를 과도하게 압축하지 말고, 각 항목마다 2~3문장 분량의 맥락과 구체적 수치·날짜를 보존하십시오.

### `source` 필드 (매우 중요)
- 각 `items[]` 항목의 `source`에는 **아래 참고 문서 블록에 적힌 실제 출처 URL 전체**를 그대로 넣으십시오.
- `[출처 URL: ...]` 또는 `[출처: https://...]` 형태로 주어진 문자열에서 **스킴(https)부터 경로·쿼리까지** 복사합니다.
- **금지:** `"https://..."`, `"예시 URL"`, 도메인만 쓰기, 짧게 줄인 링크, 가짜·추측 URL.
- 웹 검색 문서면 `url` 필드 값을, 벡터DB 문서면 메타데이터에 있는 원문 파일/URL을 그대로 사용합니다. 해당 사실을 뒷받침한 **한 출처**를 택해 한 URL만 넣어도 됩니다.

JSON 스키마 예시 (값은 반드시 실제 내용·실제 URL로 채움):
{{
  "name": "{company}",
  "items": [
    {{"content": "…실제 핵심 사실 서술…", "category": "market", "source": "https://실제-도메인/경로?쿼리=값"}},
    {{"content": "…", "category": "strengths", "source": "https://다른-전체-URL"}}
  ]
}}

카테고리(각 항목 하나): strengths / weaknesses / opportunities / threats / market 중 선택.
항목은 최소 8개 이상.

참고 문서 (출처 URL은 각 블록 상단에 명시됨):
{documents}
"""


def _research_single_company(company: str, state: ResearchGraphState) -> Dict:
    """단일 기업 조사 수행."""
    llm = _get_llm()
    raw_docs = state.get("raw_documents", [])

    # 해당 기업 관련 문서 필터링
    company_docs = [
        d for d in raw_docs
        if company.upper() in (d.get("content", "") + d.get("query", "")).upper()
    ]
    if not company_docs:
        company_docs = raw_docs[:10]

    def _doc_source_line(doc: Dict) -> str:
        u = (doc.get("url") or "").strip()
        if u:
            return u
        meta = doc.get("metadata") or {}
        return (meta.get("source_url") or meta.get("url") or meta.get("source_file") or "unknown").strip()

    doc_text = "\n\n---\n\n".join(
        (
            f"[출처 URL — 이 문자열 전체를 해당 항목의 source에 복사]\n{_doc_source_line(d)}\n"
            f"[본문]\n{(d.get('content') or '')[:1200]}"
        )
        for d in company_docs[:10]
    )
    doc_text = doc_text.replace("\x00", "").replace("\u0000", "")

    prompt = _COMPANY_RESEARCH_PROMPT.format(
        company=company,
        goal=state.get("goal", ""),
        documents=doc_text,
    )

    response = llm.invoke(prompt)
    raw = response.content.strip()

    try:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(match.group(0)) if match else {}
    except Exception:
        data = {"name": company, "items": []}

    return data


def company_research_node(state: ResearchGraphState) -> Dict:
    """LGES → company_a, CATL → company_b 병렬 조사."""
    companies = state.get("target_companies", ["LGES", "CATL"])
    company_a_name = companies[0] if len(companies) > 0 else "LGES"
    company_b_name = companies[1] if len(companies) > 1 else "CATL"

    company_a = _research_single_company(company_a_name, state)
    company_b = _research_single_company(company_b_name, state)

    return {
        "company_a": company_a,
        "company_b": company_b,
        "completed_agents": ["company_research"],
    }


# ================================================================
# 7. comparative_research_node
# ================================================================

_COMPARATIVE_PROMPT = """\
LGES와 CATL의 동일 지표를 직접 비교하는 분석을 수행하세요.

비교 지표:
- 시장점유율 추이 (2024~2026)
- 매출 / 영업이익 비교
- 주요 고객사 및 JV 파트너
- 기술 역량 (에너지밀도, 사이클 수명, 원가)
- 지역별 생산 거점

제공된 문서들을 바탕으로 비교 분석을 수행하고, 아래 JSON 형식으로 정리하세요:
{{
  "comparison_items": [
    {{"metric": "시장점유율 2025", "lges": "...", "catl": "...", "source": "..."}},
    ...
  ]
}}

참고 문서:
{documents}
"""


def comparative_research_node(state: ResearchGraphState) -> Dict:
    """양사 동일 지표 비교 쿼리 검색 및 분석."""
    llm = _get_llm()
    raw_docs = state.get("raw_documents", [])
    doc_text = "\n\n---\n\n".join(
        d.get("content", "")[:600] for d in raw_docs[:10]
    )
    doc_text = doc_text.replace("\x00", "").replace("\u0000", "")

    prompt = _COMPARATIVE_PROMPT.format(documents=doc_text)
    response = llm.invoke(prompt)
    raw = response.content.strip()

    try:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        comparison = json.loads(match.group(0)) if match else {}
    except Exception:
        comparison = {"comparison_items": []}

    # comparison_items를 raw_findings에 추가
    finding: ResearchFinding = {
        "agent_name": "comparative_research",
        "source_type": "vector_db",
        "subtopic": "양사 비교 지표",
        "raw_content": json.dumps(comparison, ensure_ascii=False),
        "key_points": [
            item.get("metric", "") for item in comparison.get("comparison_items", [])
        ][:5],
        "sources": [],
    }

    return {
        "raw_findings": [finding],
        "completed_agents": ["comparative_research"],
    }


# ================================================================
# 8. merge_results_node
# ================================================================

def merge_results_node(state: ResearchGraphState) -> Dict:
    """raw_documents 통합, grouped_documents 구성, query_coverage 집계, token_usage 업데이트."""
    raw_docs = state.get("raw_documents", [])

    # query 기준으로 그루핑
    grouped: Dict[str, List[Dict]] = {}
    for i, doc in enumerate(raw_docs):
        query = doc.get("query", f"query_{i}")
        grouped.setdefault(query, []).append(doc)

    # query_coverage 집계
    query_coverage = {}
    for query, docs in grouped.items():
        distances = [d["distance"] for d in docs if d.get("distance") is not None]
        query_coverage[query] = {
            "count": len(docs),
            "avg_distance": round(sum(distances) / len(distances), 4) if distances else None,
            "min_distance": round(min(distances), 4) if distances else None,
            "has_vdb": any(d.get("source_type") == "vector_db" for d in docs),
            "has_web": any(d.get("source_type") == "web_search" for d in docs),
            "web_urls": [
                d.get("url", "")
                for d in docs
                if d.get("source_type") == "web_search" and d.get("url")
            ],
        }

    token_usage = update_token_usage(state)

    return {
        "grouped_documents": grouped,
        "query_coverage": query_coverage,
        "token_usage": token_usage,
    }


# ================================================================
# 9. validate_evidence_node
# ================================================================

_DATE_RE = re.compile(r"(202[56]|'2[56]|202[56]년)")

def _rule_filter(documents: List[Dict]):
    """1단계 Rule-based 필터."""
    passed, failed = [], []
    for doc in documents:
        content = doc.get("content", "")
        has_source = bool(doc.get("url") or doc.get("metadata", {}).get("source_file"))
        has_date = bool(_DATE_RE.search(content))
        long_enough = len(content) >= 100

        if has_source and has_date and long_enough:
            passed.append(doc)
        else:
            failed.append(doc)
    return passed, failed


def validate_evidence_node(state: ResearchGraphState) -> Dict:
    """Rule-based 필터만 사용 (LLM 호출 없음)."""
    raw_docs = state.get("raw_documents", [])
    validated, rejected = _rule_filter(raw_docs)
    print(f"[validate_evidence] 통과: {len(validated)}개, 탈락: {len(rejected)}개")
    return {
        "validated_evidence": validated,
        "rejected_evidence": rejected,
    }


# ================================================================
# 10. coverage_check_node
# ================================================================

_COVERAGE_MIN_DOCS = 20  # sufficient 판정 최소 문서 수


def coverage_check_node(state: ResearchGraphState) -> Dict:
    """총 문서 수 기준으로 sufficient/insufficient 판정 (LLM 호출 없음)."""
    validated = state.get("validated_evidence", [])
    retry_count = state.get("retry_count", 0)
    max_retry = state.get("max_retry", 2)
    warnings = list(state.get("warnings", []))

    if len(validated) >= _COVERAGE_MIN_DOCS:
        coverage_status = "sufficient"
        missing_topics = []
    else:
        coverage_status = "insufficient"
        missing_topics = [f"문서 수 부족: {len(validated)}개 (최소 {_COVERAGE_MIN_DOCS}개 필요)"]

    # max_retry 초과 시 강제 종료
    if coverage_status == "insufficient" and retry_count >= max_retry:
        coverage_status = "sufficient"
        warnings.append(
            f"max_retry({max_retry}) 초과로 강제 진행. "
            f"현재 문서 수: {len(validated)}"
        )

    print(f"[coverage_check] {coverage_status} (문서 수: {len(validated)}, retry: {retry_count}/{max_retry})")

    return {
        "coverage_status": coverage_status,
        "missing_topics": missing_topics,
        "evidence_quality_flags": [],
        "comparability_flags": [],
        "retry_count": retry_count + (1 if coverage_status == "insufficient" else 0),
        "warnings": warnings,
    }


# ================================================================
# 12. build_output_node
# ================================================================

_BUILD_PROMPT = """\
다음은 LGES와 CATL에 대한 리서치 결과입니다. 이를 바탕으로 최종 요약을 생성하세요.

[{company_a_name} 조사 결과]
{company_a_items}

[{company_b_name} 조사 결과]
{company_b_items}

[양사 비교 분석]
{comparison_items}

[검증된 증거 수]: {evidence_count}개

위 내용을 바탕으로 JSON 형식으로 출력하세요:
{{
  "summary": "전체 조사 결과 요약 (3~5문장, 실제 수치/사실 포함)",
  "key_findings": ["핵심 발견 1 (구체적 사실)", "핵심 발견 2", ...],
  "unresolved_gaps": ["추가 조사가 필요한 항목1", ...]
}}
"""


def _format_company_items(company: Dict) -> str:
    items = company.get("items", [])
    if not items:
        return "  (데이터 없음)"
    return "\n".join(
        f"  [{item.get('category','?')}] {item.get('content','')}"
        for item in items[:12]
    )


def _format_comparison_items(raw_findings: List[Dict]) -> str:
    for finding in raw_findings:
        if finding.get("agent_name") == "comparative_research":
            try:
                data = json.loads(finding.get("raw_content", "{}"))
                items = data.get("comparison_items", [])
                if items:
                    return "\n".join(
                        f"  [{item.get('metric','')}] LGES: {item.get('lges','')} / CATL: {item.get('catl','')}"
                        for item in items[:8]
                    )
            except Exception:
                pass
    return "  (비교 데이터 없음)"


def build_output_node(state: ResearchGraphState) -> Dict:
    """실제 리서치 결과 기반 요약 생성 + findings.json 저장."""
    llm = _get_llm()
    validated = state.get("validated_evidence", [])
    company_a = state.get("company_a", {"name": "LGES", "items": []})
    company_b = state.get("company_b", {"name": "CATL", "items": []})
    raw_findings = state.get("raw_findings", [])

    prompt = _BUILD_PROMPT.format(
        company_a_name=company_a.get("name", "LGES"),
        company_a_items=_format_company_items(company_a),
        company_b_name=company_b.get("name", "CATL"),
        company_b_items=_format_company_items(company_b),
        comparison_items=_format_comparison_items(raw_findings),
        evidence_count=len(validated),
    )

    try:
        response = llm.invoke(prompt)
        raw = response.content.strip()
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(match.group(0)) if match else {}
    except Exception:
        result = {}

    validated_ids = [f"ev_{i:04d}" for i in range(len(validated))]

    # findings.json 저장
    findings_path = RAW_DATA_DIR / "findings.json"
    all_web_sources = [
        {"query": q, "url": url}
        for q, info in state.get("query_coverage", {}).items()
        for url in info.get("web_urls", [])
        if url
    ]

    findings_data = {
        "summary": result.get("summary", ""),
        "key_findings": result.get("key_findings", []),
        "unresolved_gaps": result.get("unresolved_gaps", []),
        "validated_evidence_count": len(validated),
        "company_a": company_a,
        "company_b": company_b,
        "token_usage": state.get("token_usage", {}),
        "warnings": state.get("warnings", []),
        "raw_findings": raw_findings,
        "web_sources": all_web_sources,
    }

    try:
        findings_path.write_text(
            json.dumps(findings_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[build_output] findings.json 저장: {findings_path}")
    except Exception as e:
        print(f"[build_output] findings.json 저장 실패: {e}")

    return {
        "summary": result.get("summary", ""),
        "key_findings": result.get("key_findings", []),
        "validated_evidence_ids": validated_ids,
        "swot_candidate_ids": [],
        "comparison_item_ids": [],
        "unresolved_gaps": result.get("unresolved_gaps", []),
    }


# ================================================================
# 13. human_review_node
# ================================================================

def _coverage_symbol(info: Dict) -> str:
    """avg_distance 기준 커버리지 심볼 반환 (cosine distance 기준)."""
    avg = info.get("avg_distance")
    has_vdb = info.get("has_vdb", False)
    if avg is None or not has_vdb:
        return "✗"
    if avg < 0.35:
        return "✓"
    if avg < 0.65:
        return "△"
    return "✗"


def human_review_node(state: ResearchGraphState) -> Dict:
    """Human review interrupt — 실제 리서치 내용 표시 후 승인 요청.

    자동 파이프라인(`python -m src.run`)에서는 기본적으로 interrupt를 건너뜀.
    대화형 검토를 쓰려면 환경변수 ``SKIP_RESEARCH_HUMAN_REVIEW=0`` 설정.
    """
    skip = os.environ.get("SKIP_RESEARCH_HUMAN_REVIEW", "1").strip().lower() not in (
        "0",
        "false",
        "no",
    )
    if skip:
        print(
            "[human_review] 자동 모드: interrupt 생략 → deliver (대화형: SKIP_RESEARCH_HUMAN_REVIEW=0)",
            flush=True,
        )
        return {}

    company_a = state.get("company_a", {"name": "LGES", "items": []})
    company_b = state.get("company_b", {"name": "CATL", "items": []})
    raw_findings = state.get("raw_findings", [])
    warnings = state.get("warnings", [])
    query_coverage = state.get("query_coverage", {})

    lines = ["=" * 60, "=== Human Review: 리서치 결과 검토 ===", "=" * 60]

    # 요약
    lines += ["", "[요약]", state.get("summary", "(없음)")]

    # 핵심 발견
    key_findings = state.get("key_findings", [])
    if key_findings:
        lines += ["", "[핵심 발견]"]
        lines += [f"  • {f}" for f in key_findings]

    # 양사 비교
    comp_text = _format_comparison_items(raw_findings)
    lines += ["", "[양사 비교]", comp_text]

    # 쿼리별 커버리지 테이블
    if query_coverage:
        lines += ["", "[쿼리별 커버리지]"]
        gap_queries = []
        for query, info in query_coverage.items():
            sym = _coverage_symbol(info)
            avg = info.get("avg_distance")
            avg_str = f"avg={avg:.2f}" if avg is not None else "avg=N/A"
            count = info.get("count", 0)
            sources = []
            if info.get("has_vdb"):
                sources.append("VDB")
            if info.get("has_web"):
                sources.append("WEB")
            src_str = f"[{'+'.join(sources)}]" if sources else "[없음]"
            gap_marker = "  ← 갭" if sym == "✗" else ""
            lines.append(f"  {sym} {query:<40} {avg_str}  {count}건  {src_str}{gap_marker}")
            for url in info.get("web_urls", []):
                if url:
                    lines.append(f"       └ {url}")
            if sym == "✗":
                gap_queries.append(query)
    else:
        gap_queries = []

    # 미해결 과제 (기존 gaps + ✗ 쿼리 자동 추가)
    existing_gaps = list(state.get("unresolved_gaps", []))
    for q in gap_queries:
        if q not in existing_gaps:
            existing_gaps.append(q)

    if existing_gaps:
        lines += ["", "[미해결 갭]  (✗ 쿼리 자동 포함)"]
        lines += [f"  • {g}" for g in existing_gaps]

    # 증거 현황
    validated = state.get("validated_evidence", [])
    vdb_count = sum(1 for d in validated if d.get("source_type") == "vector_db")
    web_count = sum(1 for d in validated if d.get("source_type") == "web_search")
    lines += ["", f"[증거 현황]"]
    lines += [f"  검증 통과: {len(validated)}개  (VDB: {vdb_count}개 / WEB: {web_count}개)"]

    if warnings:
        lines += ["", "[경고]"]
        lines += [f"  ⚠ {w}" for w in warnings]

    lines += ["", "=" * 60, "계속 진행하려면 승인하세요.", "=" * 60]

    interrupt("\n".join(lines))
    return {"unresolved_gaps": existing_gaps}


# ================================================================
# 14. deliver_node  (bridge_node_1 역할)
# ================================================================

def deliver_node(state: ResearchGraphState) -> Dict:
    """company_a / company_b + raw_findings + query_coverage 추출 반환 (DataRefineGraph로 전달)."""
    return {
        "company_a": state.get("company_a", {"name": "LGES", "items": []}),
        "company_b": state.get("company_b", {"name": "CATL", "items": []}),
        "raw_findings": state.get("raw_findings", []),
        "query_coverage": state.get("query_coverage", {}),
        "completed_agents": ["deliver"],
    }
