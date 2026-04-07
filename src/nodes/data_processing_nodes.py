"""
Data Processing Nodes for Task 2.
이 모듈은 조사 단계(Task 1)에서 넘어온 데이터를 정제하고 구조화하는 노드들을 포함합니다.
"""

from typing import Dict, Any
from src.state.state import DataRefineGraphState

def clean_node(state: DataRefineGraphState) -> Dict[str, Any]:
    """
    수집된 날것의 데이터(raw_findings)에서 중복을 제거하고 명확한 문장 형태의 RawItem 리스트로 변환합니다.
    """
    print("--- [Node] Running clean_node ---")
    raw_findings = state.get("raw_findings", [])
    
    # TODO: clean_agent를 호출하여 raw_findings를 정제하는 로직 구현
    # 예: 중복 제거, 핵심 내용 추출
    
    # 임시 반환 구조 (실제로는 LLM 결과를 파싱하여 반환)
    company_a_cleaned = []
    company_b_cleaned = []
    
    return {
        "company_a_cleaned": company_a_cleaned,
        "company_b_cleaned": company_b_cleaned
    }

def market_node(state: DataRefineGraphState) -> Dict[str, Any]:
    """
    정제된 데이터 중 시장/산업 관련 내용을 뽑아 MarketContext 객체로 매핑합니다.
    """
    print("--- [Node] Running market_node ---")
    # TODO: market_portfolio_agent를 호출하여 시장 상황 추출 로직 구현
    
    # 임시 반환 구조
    market_context = {
        "TAM": None,
        "SAM": None,
        "CAGR": None,
        "trend": "EV 수요 둔화(캐즘), 보조금 축소 등 (예시)",
        "company_a_position": None,
        "company_b_position": None
    }
    
    return {"market_context": market_context}

def portfolio_node(state: DataRefineGraphState) -> Dict[str, Any]:
    """
    각 기업의 제품, 서비스, 신사업 전략을 CompanyPortfolio 객체로 구조화합니다.
    """
    print("--- [Node] Running portfolio_node ---")
    company_a_cleaned = state.get("company_a_cleaned", [])
    company_b_cleaned = state.get("company_b_cleaned", [])
    
    # TODO: market_portfolio_agent를 호출하여 포트폴리오 추출 로직 구현
    
    company_a_portfolio = {
        "core_services": [],
        "revenue_contribution": {},
        "diversification_type": "미정",
        "diversification_stage": "미정",
        "core_competency": "미정"
    }
    
    company_b_portfolio = {
        "core_services": [],
        "revenue_contribution": {},
        "diversification_type": "미정",
        "diversification_stage": "미정",
        "core_competency": "미정"
    }
    
    return {
        "company_a_portfolio": company_a_portfolio,
        "company_b_portfolio": company_b_portfolio
    }

def swot_map_node(state: DataRefineGraphState) -> Dict[str, Any]:
    """
    정제된 개별 팩트(RawItem)를 CompanySWOT 객체의 S, W, O, T 리스트에 각각 '분류'만 수행하여 넣습니다.
    분석이나 해석은 절대 수행하지 않습니다.
    """
    print("--- [Node] Running swot_map_node ---")
    company_a_cleaned = state.get("company_a_cleaned", [])
    company_b_cleaned = state.get("company_b_cleaned", [])
    
    # TODO: swot_classifier_agent를 호출하여 S/W/O/T 분류 로직 구현
    
    company_a_swot = {"S": [], "W": [], "O": [], "T": []}
    company_b_swot = {"S": [], "W": [], "O": [], "T": []}
    
    return {
        "company_a_swot": company_a_swot,
        "company_b_swot": company_b_swot
    }
