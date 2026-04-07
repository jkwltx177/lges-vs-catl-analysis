"""
Task.4 보고서 LangGraph — 실행 순서:

  sections_parallel_123 (section1~3 병렬)
    → section4 → section5 → section0 (SUMMARY) → section6 (REFERENCE) → merge → END

분석 단계 이후에는 `bridge_from_analysis`로 초기 State를 만든 뒤 `invoke` 한다.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.nodes.report.bridge import bridge_from_analysis
from src.nodes.report.merge_node import merge_node
from src.nodes.report.section_nodes import (
    section0_node,
    section4_node,
    section5_node,
    section6_node,
    sections_parallel_123_node,
)
from src.state.state import AnalysisGraphState, ReportGraphState


def build_report_graph():
    """Compiles the report-only subgraph (expects ReportGraphState-shaped input)."""
    g = StateGraph(ReportGraphState)
    g.add_node("sections_parallel_123", sections_parallel_123_node)
    g.add_node("section4", section4_node)
    g.add_node("section5", section5_node)
    g.add_node("section0", section0_node)
    g.add_node("section6", section6_node)
    g.add_node("merge", merge_node)

    g.add_edge(START, "sections_parallel_123")
    g.add_edge("sections_parallel_123", "section4")
    g.add_edge("section4", "section5")
    g.add_edge("section5", "section0")
    g.add_edge("section0", "section6")
    g.add_edge("section6", "merge")
    g.add_edge("merge", END)
    return g.compile()


def run_report_from_analysis(state: AnalysisGraphState) -> ReportGraphState:
    """AnalysisGraphState → bridge → 보고서 그래프 실행 → 최종 dict."""
    graph = build_report_graph()
    initial: ReportGraphState = bridge_from_analysis(state)
    result = graph.invoke(initial)
    return result


def run_report_from_report_state(initial: ReportGraphState) -> ReportGraphState:
    """이미 ReportGraphState인 경우 (테스트·수동 주입)."""
    graph = build_report_graph()
    return graph.invoke(initial)
