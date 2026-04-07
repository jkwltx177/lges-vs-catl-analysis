"""Bridge nodes for explicit graph-to-graph field transfer."""

from __future__ import annotations

from typing import Dict

from ..state.state import AnalysisGraphState, DataRefineGraphState, ReportGraphState, ResearchGraphState


def bridge_node_1(state: ResearchGraphState) -> DataRefineGraphState:
    """Research -> Refine explicit field copy."""
    return {
        "company_a": state.get("company_a", {}),
        "company_b": state.get("company_b", {}),
        "raw_findings": state.get("raw_findings", []),
        "query_coverage": state.get("query_coverage", {}),
    }


def bridge_node_2(state: DataRefineGraphState) -> AnalysisGraphState:
    """Refine -> Analysis explicit field copy."""
    return {
        "market_context": state.get("market_context", {}),
        "company_a_portfolio": state.get("company_a_portfolio", {}),
        "company_b_portfolio": state.get("company_b_portfolio", {}),
        "company_a_swot": state.get("company_a_swot", {}),
        "company_b_swot": state.get("company_b_swot", {}),
        "raw_findings": state.get("raw_findings", []),
    }


def bridge_node_3(state: AnalysisGraphState) -> ReportGraphState:
    """Analysis -> Report explicit field copy."""
    return {
        "market_context": state.get("market_context", {}),
        "comparative_swot": state.get("comparative_swot", {}),
        "final_insight": state.get("final_insight", {}),
        "company_a_portfolio": state.get("company_a_portfolio", {}),
        "company_b_portfolio": state.get("company_b_portfolio", {}),
        "raw_findings": state.get("raw_findings", []),
    }
