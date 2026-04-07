"""
Data Processing Nodes for Task 2.
이 모듈은 조사 단계(Task 1)에서 넘어온 데이터를 정제하고 구조화하는 노드들을 포함합니다.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from src.state.state import DataRefineGraphState
from src.agents.clean_agent import create_clean_prompt
from src.agents.market_portfolio_agent import create_market_portfolio_prompt
from src.agents.swot_classifier_agent import create_swot_classifier_prompt

# Pydantic Models for Structured Output
class PydanticRawItem(BaseModel):
    content: str = Field(description="정제된 핵심 사실 내용 (원문의 구체적 수치와 맥락이 보존된 형태)")
    category: str = Field(description="'strengths', 'weaknesses', 'opportunities', 'threats', 'market' 중 하나")
    source: str = Field(description="해당 사실이 발췌된 원문의 출처 (URL 등) 또는 에이전트 이름", default="")

class PydanticCleanOutput(BaseModel):
    company_a_cleaned: List[PydanticRawItem]
    company_b_cleaned: List[PydanticRawItem]

class PydanticMarketContext(BaseModel):
    TAM: Optional[str]
    SAM: Optional[str]
    CAGR: Optional[str]
    trend: Optional[str]
    company_a_position: Optional[str]
    company_b_position: Optional[str]

class PydanticCompanyPortfolio(BaseModel):
    core_services: List[str]
    revenue_contribution: List[str] = Field(description="각 서비스별 매출 기여도 추정치 (예: 'BEV 배터리 62%')", default_factory=list)
    diversification_type: str
    diversification_stage: str
    core_competency: str

class PydanticPortfolioOutput(BaseModel):
    company_a_portfolio: PydanticCompanyPortfolio
    company_b_portfolio: PydanticCompanyPortfolio

class PydanticSWOTItem(BaseModel):
    content: str
    source: str
    is_fact: bool

class PydanticCompanySWOT(BaseModel):
    S: List[PydanticSWOTItem]
    W: List[PydanticSWOTItem]
    O: List[PydanticSWOTItem]
    T: List[PydanticSWOTItem]

class PydanticSWOTOutput(BaseModel):
    company_a_swot: PydanticCompanySWOT
    company_b_swot: PydanticCompanySWOT

def clean_node(state: DataRefineGraphState) -> Dict[str, Any]:
    """
    수집된 날것의 데이터(raw_findings) 및 Task 1에서 생성된 company_a, company_b의 초기 추출 결과에서 
    중복을 제거하고 명확한 문장 형태의 RawItem 리스트로 변환합니다.
    """
    print("--- [Node] Running clean_node ---")
    raw_findings = state.get("raw_findings", [])
    company_a_init = state.get("company_a", {}).get("items", [])
    company_b_init = state.get("company_b", {}).get("items", [])
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    structured_llm = llm.with_structured_output(PydanticCleanOutput)
    
    prompt = create_clean_prompt()
    
    # 원문 데이터 및 Task 1 1차 추출 결과 조합
    findings_text = "=== Task 1 Research Findings ===\n" + "\n\n".join([f"Agent: {f.get('agent_name')}\nSubtopic: {f.get('subtopic')}\nSources: {', '.join(f.get('sources', []))}\nContent: {f.get('raw_content')}" for f in raw_findings])
    findings_text += f"\n\n=== LGES Task 1 Initial Items ===\n{company_a_init}"
    findings_text += f"\n\n=== CATL Task 1 Initial Items ===\n{company_b_init}"
    
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"다음 조사 결과를 정제하여 LGES와 CATL 각각의 핵심 사실 리스트로 만들어주세요:\n\n{findings_text}")
    ]
    
    result = structured_llm.invoke(messages)
    
    return {
        "company_a_cleaned": [item.model_dump() for item in result.company_a_cleaned],
        "company_b_cleaned": [item.model_dump() for item in result.company_b_cleaned]
    }

def market_node(state: DataRefineGraphState) -> Dict[str, Any]:
    """
    정제된 데이터 중 시장/산업 관련 내용을 뽑아 MarketContext 객체로 매핑합니다.
    """
    print("--- [Node] Running market_node ---")
    company_a_cleaned = state.get("company_a_cleaned", [])
    company_b_cleaned = state.get("company_b_cleaned", [])
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    structured_llm = llm.with_structured_output(PydanticMarketContext)
    
    prompt = create_market_portfolio_prompt()
    
    findings_text = f"LGES Data: {company_a_cleaned}\n\nCATL Data: {company_b_cleaned}"
    
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"다음 데이터를 바탕으로 시장 컨텍스트(MarketContext) 객체를 추출해주세요:\n\n{findings_text}")
    ]
    
    result = structured_llm.invoke(messages)
    
    return {"market_context": result.model_dump()}

def portfolio_node(state: DataRefineGraphState) -> Dict[str, Any]:
    """
    각 기업의 제품, 서비스, 신사업 전략을 CompanyPortfolio 객체로 구조화합니다.
    """
    print("--- [Node] Running portfolio_node ---")
    company_a_cleaned = state.get("company_a_cleaned", [])
    company_b_cleaned = state.get("company_b_cleaned", [])
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    structured_llm = llm.with_structured_output(PydanticPortfolioOutput)
    
    prompt = create_market_portfolio_prompt()
    
    findings_text = f"LGES Data: {company_a_cleaned}\n\nCATL Data: {company_b_cleaned}"
    
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"다음 데이터를 바탕으로 LGES와 CATL 각각의 포트폴리오를 추출해주세요:\n\n{findings_text}")
    ]
    
    result = structured_llm.invoke(messages)
    
    return {
        "company_a_portfolio": result.company_a_portfolio.model_dump(),
        "company_b_portfolio": result.company_b_portfolio.model_dump()
    }

def swot_map_node(state: DataRefineGraphState) -> Dict[str, Any]:
    """
    정제된 개별 팩트(RawItem)를 CompanySWOT 객체의 S, W, O, T 리스트에 각각 '분류'만 수행하여 넣습니다.
    분석이나 해석은 절대 수행하지 않습니다.
    """
    print("--- [Node] Running swot_map_node ---")
    company_a_cleaned = state.get("company_a_cleaned", [])
    company_b_cleaned = state.get("company_b_cleaned", [])
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    structured_llm = llm.with_structured_output(PydanticSWOTOutput)
    
    prompt = create_swot_classifier_prompt()
    
    findings_text = f"LGES 팩트: {company_a_cleaned}\n\nCATL 팩트: {company_b_cleaned}"
    
    messages = [
        SystemMessage(content=prompt),
        HumanMessage(content=f"다음 팩트들을 분석 없이 순수하게 S, W, O, T 버킷에 분류해주세요. is_fact는 무조건 true로 고정하고, source 필드에는 제공된 팩트의 'source' 정보를 그대로 옮겨 적으세요 (절대 생략 금지):\n\n{findings_text}")
    ]
    
    result = structured_llm.invoke(messages)
    
    return {
        "company_a_swot": result.company_a_swot.model_dump(),
        "company_b_swot": result.company_b_swot.model_dump()
    }
