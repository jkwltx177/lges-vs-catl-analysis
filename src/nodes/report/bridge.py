"""AnalysisGraphState → ReportGraphState 명시적 주입 (bridge_node_3)."""

from __future__ import annotations

from src.state.state import AnalysisGraphState, ReportGraphState


def bridge_from_analysis(state: AnalysisGraphState) -> ReportGraphState:
    """
    Role 설계서: 다음 필드를 Report 단계로 넘긴다.
      market_context, comparative_swot, final_insight,
      company_a_portfolio, company_b_portfolio, raw_findings
    sections / final_report는 빈 값으로 초기화.
    """
    out: ReportGraphState = {
        "market_context": state.get("market_context") or {},
        "comparative_swot": state.get("comparative_swot") or {},
        "final_insight": state.get("final_insight") or {},
        "company_a_portfolio": state.get("company_a_portfolio") or {},
        "company_b_portfolio": state.get("company_b_portfolio") or {},
        "raw_findings": state.get("raw_findings") or [],
        "sections": {},
        "retry_count": state.get("retry_count", 0),
        "max_retry": state.get("max_retry", 3),
        "human_review_flags": state.get("human_review_flags") or [],
        "warnings": state.get("warnings") or [],
    }
    return out
