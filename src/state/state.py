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
from typing import Annotated, Dict, List, Optional
from typing_extensions import TypedDict


# ================================================================
# Shared Types
# ================================================================

class RawItem(TypedDict):
    content: str
    category: str  # strengths / weaknesses / opportunities / threats / market


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
    revenue_contribution: Dict[str, str]   # e.g. {"BEV 배터리": "62%"}
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
    search_plan: List[str]

    # Retrieval 출력
    raw_documents: List[Dict]
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
# ANALYSIS SUB-TYPES (Task 3 세부 타입)
# ================================================================

class SwotItem(TypedDict):
    """개별 SWOT 항목 (기본 단위)."""
    point: str              # SWOT 내용
    evidence: str           # 근거/출처
    source: str             # 출처 명시


class EnrichedSwotItem(TypedDict, total=False):
    """SWOT 항목 + 전략적 맥락 (Task 3에서 생성)."""
    point: str
    evidence: str
    why_it_matters: str     # 왜 중요한가?
    impact: str             # 전략적 영향도


class ComparativePoint(TypedDict, total=False):
    """LGES vs CATL 비교 분석 포인트."""
    dimension: str                   # 비교 차원
    lges_position: str              # LGES 포지셔닝
    catl_position: str              # CATL 포지셔닝
    relative_advantage: str         # "LGES_leads" | "CATL_leads" | "balanced"


class ResilienceEvaluation(TypedDict, total=False):
    """EV 캐즘기 회복탄력성 평가 (final_insight 내부에 nested)."""
    total_score_lges: float         # 0-100
    total_score_catl: float         # 0-100
    winner: str                     # "LGES" | "CATL" | "Tie"
    evaluation_summary: str         # 요약
    evaluation_factors: List[str]   # 평가 요인


# ================================================================
# Analysis Sub-States (카테고리별 분석 결과)
# ================================================================

class CategoryAnalysisState(TypedDict, total=False):
    """단일 SWOT 카테고리 분석 상태 (S/W/O/T 별)."""
    lges_items: List[EnrichedSwotItem]          # LGES 해당 카테고리 항목 (enriched)
    catl_items: List[EnrichedSwotItem]          # CATL 해당 카테고리 항목 (enriched)
    comparative_points: List[ComparativePoint]  # 양사 비교 분석 포인트
    strategic_implications: List[str]           # 카테고리별 전략적 시사점


class ComparativeSwotState(TypedDict, total=False):
    """통합 SWOT 매트릭스 (S/W/O/T 모두 포함)."""
    lges_matrix: Dict[str, List[EnrichedSwotItem]]   # {"S": [...], "W": [...], ...}
    catl_matrix: Dict[str, List[EnrichedSwotItem]]
    comparative_summary: str                        # 비교 요약
    strategic_positioning: str                      # 전략적 포지셔닝


class FinalInsight(TypedDict, total=False):
    """최종 전략적 인사이트 (Task 3 최종 산출물)."""
    resilience_evaluation: ResilienceEvaluation     # 회복탄력성 평가
    key_differences: List[str]                      # LGES vs CATL 핵심 차이점
    strategic_winner: str                           # 전략적 우위 기업
    final_insights: List[str]                       # 최종 시사점 (4개)
    validation_notes: Optional[List[str]]           # 검증 노트 (optional)


# ================================================================
# Graph State 3 — 자료 분석
# ================================================================

class AnalysisGraphState(TypedDict, total=False):
    """Task 3 Analysis Phase의 그래프 상태.
    
    입력:
      - bridge_node_2에서 주입 (DataRefineGraphState → AnalysisGraphState)
      - company_a_swot, company_b_swot, market_context, portfolio, raw_findings
    
    출력 (6-field contract — dispatch_node에서 보장):
      - swot_S, swot_W, swot_O, swot_T (CategoryAnalysisState)
      - comparative_swot (ComparativeSwotState)
      - final_insight (FinalInsight)
    """
    
    # ===== 입력 필드 (bridge_node_2에서 주입) =====
    market_context: MarketContext
    company_a_portfolio: CompanyPortfolio
    company_b_portfolio: CompanyPortfolio
    company_a_swot: CompanySWOT
    company_b_swot: CompanySWOT
    raw_findings: Annotated[List[ResearchFinding], operator.add]

    # ===== 병렬 SWOT 분석 노드 출력 (교차 기록 금지) =====
    swot_S: CategoryAnalysisState   # Strength 분석
    swot_W: CategoryAnalysisState   # Weakness 분석
    swot_O: CategoryAnalysisState   # Opportunity 분석
    swot_T: CategoryAnalysisState   # Threat 분석

    # ===== 순차 분석 노드 출력 =====
    comparative_swot: ComparativeSwotState      # context_integration_node
    final_insight: FinalInsight                 # insight_node, cross_validation_node

    # ===== 내부 라우팅 필드 (최종 출력에 포함 안 됨) =====
    review_status: str                          # "approved" | "review_required"
    consistency_flags: List[str]                # 일관성 검증 플래그 (빈 리스트 = OK)

    # ===== 제어 필드 =====
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
    raw_findings: Annotated[List[ResearchFinding], operator.add]

    # 병렬 섹션 노드 출력 — merge_sections reducer로 키 단위 병합
    sections: Annotated[ReportSectionState, merge_sections]

    # merge_node 출력
    final_report: str

    # 제어 필드
    retry_count: int
    max_retry: int
    human_review_flags: List[str]
    warnings: List[str]
