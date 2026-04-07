"""
State definitions for the LGES vs CATL analysis pipeline.

Data flow:
  ResearchGraphState
    → bridge_node_1 →
  DataRefineGraphState
    → bridge_node_2 →
  AnalysisGraphState
    → bridge_node_3 →
  ReportGraphState
"""

import operator
from typing import Annotated, Dict, List, Optional, TypedDict


# ================================================================
# Shared Types
# ================================================================

class RawItem(TypedDict):
    content: str
    category: str  # strengths / weaknesses / opportunities / threats / market
    source: str    # 원문 출처 (URL 또는 Agent 이름)


class SWOTItem(TypedDict):
    content: str
    source: str
    is_fact: bool


class CompanySWOT(TypedDict):
    S: List[SWOTItem]
    W: List[SWOTItem]
    O: List[SWOTItem]
    T: List[SWOTItem]


class CompanyPortfolio(TypedDict):
    core_services: List[str]
    revenue_contribution: Dict[str, str] | List[str]  # Task2 output or normalized mapping
    diversification_type: str              # 수직 / 수평 / 비관련
    diversification_stage: str             # 투자 / 수익화
    core_competency: str


class MarketContext(TypedDict):
    TAM: Optional[str]
    SAM: Optional[str]
    CAGR: Optional[str]
    trend: Optional[str]
    company_a_position: Optional[str]
    company_b_position: Optional[str]


class CompanyRaw(TypedDict):
    name: str
    items: List[RawItem]


# ================================================================
# Research Finding  (raw 데이터 보존 — 절대 압축 금지)
# ================================================================

class ResearchFinding(TypedDict):
    agent_name: str        # 수집 에이전트 (LGES_Search, CATL_Search 등)
    source_type: str       # "web_search" | "vector_db"
    subtopic: str          # 담당 세부 주제
    raw_content: str       # 원문 데이터 (최소 800자)
    key_points: List[str]  # 에이전트 간 통신용 핵심 요약 (3~5개)
    sources: List[str]     # 출처 URL / 문헌 목록


# ================================================================
# Custom Reducer
# ================================================================

def merge_sections(old: Dict, new: Dict) -> Dict:
    """병렬 섹션 노드의 결과를 키 단위로 병합하는 커스텀 reducer.
    새 값이 있으면 덮어쓰고, 없으면 기존 값 보존."""
    return {**old, **new}


# ================================================================
# Graph State 1 — 조사 에이전트
# ================================================================

class ResearchGraphState(TypedDict, total=False):
    # 불변 입력
    goal: str
    target_companies: List[str]
    report_topic: str
    subtopics: List[str]         # Coordinator가 생성한 세부 조사 항목
    current_subtopic: str        # Send()로 개별 에이전트에 전달될 현재 주제

    # Query Generation 출력
    query_set: List[str]
    search_plan: List[Dict]  # [{"query", "route", "company_filter"}, ...]

    # Retrieval 출력 (병렬 노드가 동시에 쓰므로 operator.add로 누적)
    raw_documents: Annotated[List[Dict], operator.add]
    grouped_documents: Dict[str, List[Dict]]   # query_id → 문서 목록

    # Evidence Validation 출력
    validated_evidence: List[Dict]
    rejected_evidence: List[Dict]

    # Coverage Check 출력
    coverage_status: str           # "sufficient" | "insufficient"
    missing_topics: List[str]
    evidence_quality_flags: List[str]
    comparability_flags: List[str]

    # Company Research 출력 (병렬 — 교차 기록 금지)
    company_a: CompanyRaw          # LGES 에이전트 전용
    company_b: CompanyRaw          # CATL 에이전트 전용

    # 누적 필드 (operator.add — 덮어쓰기 금지)
    raw_findings: Annotated[List[ResearchFinding], operator.add]
    completed_agents: Annotated[List[str], operator.add]

    # Build Output 출력
    summary: str
    key_findings: List[str]
    validated_evidence_ids: List[str]
    comparison_item_ids: List[str]
    swot_candidate_ids: List[str]
    unresolved_gaps: List[str]

    # Query Coverage 필드
    query_coverage: Dict[str, Dict]    # {"쿼리 텍스트": {"count": 5, "avg_distance": 0.21, ...}}

    # Token / Cache 필드
    token_usage: Dict[str, int]        # {"raw_documents": 45000, "total": 60000}
    summary_cache: Dict[str, str]      # {"query_id_001": "요약 텍스트..."}

    # 제어 필드
    retry_count: int
    max_retry: int
    human_review_flags: List[str]
    warnings: List[str]


# ================================================================
# Graph State 2 — 자료 정리
# ================================================================

class DataRefineGraphState(TypedDict, total=False):
    # bridge_node_1에서 주입 (ResearchGraphState → DataRefineGraphState)
    company_a: CompanyRaw
    company_b: CompanyRaw
    raw_findings: Annotated[List[ResearchFinding], operator.add]

    # bridge_node_1에서 주입 (ResearchGraphState → DataRefineGraphState)
    query_coverage: Dict[str, Dict]    # 쿼리별 커버리지 (Research 단계에서 계산)

    # clean_node 출력
    company_a_cleaned: List[RawItem]
    company_b_cleaned: List[RawItem]

    # market_node 출력
    market_context: MarketContext

    # portfolio_node 출력
    company_a_portfolio: CompanyPortfolio
    company_b_portfolio: CompanyPortfolio

    # swot_map_node 출력 (사실만, 해석 금지)
    company_a_swot: CompanySWOT
    company_b_swot: CompanySWOT

    # 제어 필드
    retry_count: int
    max_retry: int
    human_review_flags: List[str]
    warnings: List[str]


# ================================================================
# Analysis Sub-Types
# ================================================================

class SwotItem(TypedDict):
    """개별 SWOT 항목 (기본 단위)."""
    point: str
    evidence: str
    source: str


class EnrichedSwotItem(TypedDict, total=False):
    """SWOT 항목 + 전략적 맥락."""
    point: str
    evidence: str
    why_it_matters: str
    impact: str


class ComparativePoint(TypedDict, total=False):
    """LGES vs CATL 비교 분석 포인트."""
    dimension: str
    lges_position: str
    catl_position: str
    relative_advantage: str


class ResilienceEvaluation(TypedDict, total=False):
    """EV 캐즘기 회복탄력성 평가."""
    total_score_lges: float
    total_score_catl: float
    winner: str
    evaluation_summary: str
    evaluation_factors: List[str]


# ================================================================
# Analysis Sub-States
# ================================================================

class CategoryAnalysisState(TypedDict, total=False):
    lges_items: List[EnrichedSwotItem]
    catl_items: List[EnrichedSwotItem]
    comparative_points: List[ComparativePoint]
    strategic_implications: List[str]  # 카테고리별 전략적 시사점


class ComparativeSwotState(TypedDict, total=False):
    lges_matrix: Dict[str, List[EnrichedSwotItem]]
    catl_matrix: Dict[str, List[EnrichedSwotItem]]
    comparative_summary: str
    strategic_positioning: str
    consistency_flags: List[str]


class FinalInsight(TypedDict, total=False):
    key_differences: List[str]
    resilience_evaluation: ResilienceEvaluation
    strategic_winner: str
    final_insights: List[str]
    validation_notes: Optional[List[str]]


# ================================================================
# Graph State 3 — 자료 분석
# ================================================================

class AnalysisGraphState(TypedDict, total=False):
    # bridge_node_2에서 주입 (DataRefineGraphState → AnalysisGraphState)
    market_context: MarketContext
    company_a_portfolio: CompanyPortfolio
    company_b_portfolio: CompanyPortfolio
    company_a_swot: CompanySWOT
    company_b_swot: CompanySWOT
    # Task.1 기업 조사 JSON + Task.2 정제 항목 — 참고문헌 URL 추출용 (보고서 section6·부록)
    company_a: CompanyRaw
    company_b: CompanyRaw
    company_a_cleaned: List[RawItem]
    company_b_cleaned: List[RawItem]
    raw_findings: Annotated[List[ResearchFinding], operator.add]
    # Task.1 조사 쿼리 커버리지 (Refine에서 전달 — 보고서 부록용)
    query_coverage: Dict[str, Dict]

    # 병렬 SWOT 분석 에이전트 출력 (교차 기록 금지)
    swot_S: CategoryAnalysisState   # Strength 분석 에이전트 전용
    swot_W: CategoryAnalysisState   # Weakness 분석 에이전트 전용
    swot_O: CategoryAnalysisState   # Opportunity 분석 에이전트 전용
    swot_T: CategoryAnalysisState   # Threat 분석 에이전트 전용

    # context_integration_node / insight_node 출력
    comparative_swot: ComparativeSwotState
    final_insight: FinalInsight

    # 내부 라우팅 필드
    review_status: str
    consistency_flags: List[str]

    # 제어 필드
    retry_count: int
    max_retry: int
    human_review_flags: List[str]
    warnings: List[str]


# ================================================================
# Graph State 4 — 보고서 생성
# ================================================================

class ReportSectionState(TypedDict, total=False):
    section0: str   # SUMMARY (마지막 작성)
    section1: str   # 시장 배경 및 산업 환경 변화
    section2: str   # LGES 기업 분석
    section3: str   # CATL 기업 분석
    section4: str   # Comparative SWOT 분석
    section5: str   # 종합 시사점 및 전략적 제언
    section6: str   # REFERENCE


class ReportGraphState(TypedDict, total=False):
    # bridge_node_3에서 주입 (AnalysisGraphState → ReportGraphState)
    market_context: MarketContext
    comparative_swot: ComparativeSwotState
    final_insight: FinalInsight
    company_a_portfolio: CompanyPortfolio
    company_b_portfolio: CompanyPortfolio
    company_a: CompanyRaw
    company_b: CompanyRaw
    company_a_cleaned: List[RawItem]
    company_b_cleaned: List[RawItem]
    company_a_swot: CompanySWOT
    company_b_swot: CompanySWOT
    raw_findings: Annotated[List[ResearchFinding], operator.add]
    query_coverage: Dict[str, Dict]  # Task.1 → Report 부록

    # 보고서 메타 (선택 — 없으면 merge 시점 기본값)
    report_title: str              # 표지 제목 (기본: 프로젝트 정식 제목)
    report_date: str               # YYYY-MM-DD, 없으면 merge 실행일

    # 병렬 섹션 노드 출력 — merge_sections reducer로 키 단위 병합
    sections: Annotated[ReportSectionState, merge_sections]

    # merge_node 출력
    final_report: str
    final_report_md_path: str      # 저장된 .md 경로 (report/final/)
    final_report_pdf_path: str      # 저장된 .pdf 경로 (실패 시 빈 문자열 가능)
    final_report_docs_md_path: str   # docs/ 동일 stem .md
    final_report_docs_pdf_path: str   # docs/ 동일 stem .pdf (실패 시 빈 문자열)
    report_file_path: str  # startup-invest-agent와 동일: PDF 성공 시 PDF, 실패 시 MD (주로 report/final 기준)

    # 제어 필드
    retry_count: int
    max_retry: int
    human_review_flags: List[str]
    warnings: List[str]
