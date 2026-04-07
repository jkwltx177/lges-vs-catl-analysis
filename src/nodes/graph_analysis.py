"""
LangGraph orchestration for Task 3 (Analysis phase) - LGES vs CATL project.

Constructs and manages the analysis workflow:
1. Parallel SWOT analysis (S, W, O, T)
2. Fan-in to context integration
3. Sequential: resilience evaluation → insight generation → cross-validation
4. Conditional branching: validation issues → human review OR dispatch
5. Final output
"""

from typing import Literal

from ..state.state import AnalysisGraphState

try:
    from langgraph.graph import StateGraph, START, END
except ImportError:
    # Fallback for different LangGraph versions
    START = "START"
    END = "END"
    from langgraph.graph import StateGraph

try:
    from langgraph.types import Send
except ImportError:
    # Fallback: Send may not be needed if not using dynamic routing
    Send = None

from .analysis_nodes import (
    strength_analysis_node,
    weakness_analysis_node,
    opportunity_analysis_node,
    threat_analysis_node,
    context_integration_node,
    resilience_evaluation_node,
    insight_node,
    cross_validation_node,
    human_review_node,
    dispatch_node,
)

def need_human_review(state: AnalysisGraphState) -> Literal["human_review_node", "dispatch_node"]:
    """
    Conditional routing: Determine if analysis requires human review before dispatch.
    
    State Structure References (확정):
        • validation_notes: state.final_insight.validation_notes (FinalInsight 내부)
        • consistency_flags: state.consistency_flags (AnalysisGraphState 최상위)
        • comparative_swot: state.comparative_swot (ComparativeSwotState = SWOT 데이터만, 라우팅 정보 없음)
    
    Review Conditions:
        ✗ validation_notes에 경고(⚠) 있음 → human_review_node
        ✗ consistency_flags 있음 (일관성 문제) → human_review_node
        ✓ 모두 정상 → dispatch_node
    
    Args:
        state: AnalysisGraphState (양사 SWOT 분석 완료, 최종 인사이트 생성됨)
    
    Returns:
        "human_review_node": 검증 경고 또는 일관성 문제 발견
        "dispatch_node": 모든 검증 통과, 다음 단계 진행
    """
    # ===== Read: final_insight (FinalInsight 타입) =====
    # validation_notes는 cross_validation_node에서 저장됨
    final_insight = state.get("final_insight", {})
    validation_notes = final_insight.get("validation_notes") or []
    
    # ===== Read: consistency_flags (AnalysisGraphState 최상위) =====
    # 라우팅/메타데이터용 필드 (SWOT 데이터가 아님)
    consistency_flags = state.get("consistency_flags", [])
    
    # ===== CONDITION 1: Check for validation warnings =====
    # validation_notes 내 "⚠" 문자열 = 검증 경고
    warnings_count = sum(1 for note in validation_notes if note.startswith("⚠"))
    if warnings_count > 0:
        return "human_review_node"
    
    # ===== CONDITION 2: Check for consistency issues =====
    # consistency_flags 존재 = 분석 일관성 문제 발생
    if consistency_flags:
        return "human_review_node"
    
    # ===== PASS: All validations OK =====
    return "dispatch_node"


# Alias for backward compatibility
def _route_validation_decision(state: AnalysisGraphState) -> Literal["human_review_node", "dispatch_node"]:
    """
    Legacy alias for need_human_review().
    Deprecated: Use need_human_review() directly.
    """
    return need_human_review(state)


# ============================================================================
# PARALLEL SWOT NODES SENDER
# ============================================================================

def _send_swot_nodes(state: AnalysisGraphState) -> list:
    """
    Create parallel tasks for all 4 SWOT analysis nodes.
    
    LangGraph implicitly waits for all parallel tasks to complete
    before proceeding to fan-in node (context_integration_node).
    
    Returns:
        List of Send() calls for parallel execution, or empty list if Send not available
    """
    if Send is None:
        # If Send not available, return empty list
        # (implicit parallel via add_edge from START will handle it)
        return []
    
    return [
        Send("strength_analysis_node", state),
        Send("weakness_analysis_node", state),
        Send("opportunity_analysis_node", state),
        Send("threat_analysis_node", state),
    ]


# ============================================================================
# GRAPH BUILDER
# ============================================================================

def build_analysis_graph() -> StateGraph:
    """
    Build and compile the analysis workflow graph.
    
    Architecture:
        1. START → parallel SWOT nodes (4 parallel tasks)
        2. Implicit convergence → context_integration_node (fan-in)
        3. Sequential pipeline:
           context_integration → resilience_evaluation → insight → cross_validation
        4. Conditional branching:
           - validation_notes has warnings → human_review_node
           - no warnings → dispatch_node
        5. dispatch_node → END
        6. human_review_node → END (for now, in future may loop back)
    
    Returns:
        Compiled StateGraph ready for execution
    """
    # Create graph
    graph = StateGraph(AnalysisGraphState)
    
    # ====================================================================
    # ADD NODES
    # ====================================================================
    
    # Parallel SWOT nodes
    graph.add_node("strength_analysis_node", strength_analysis_node)
    graph.add_node("weakness_analysis_node", weakness_analysis_node)
    graph.add_node("opportunity_analysis_node", opportunity_analysis_node)
    graph.add_node("threat_analysis_node", threat_analysis_node)
    
    # Sequential nodes
    graph.add_node("context_integration_node", context_integration_node)
    graph.add_node("resilience_evaluation_node", resilience_evaluation_node)
    graph.add_node("insight_node", insight_node)
    graph.add_node("cross_validation_node", cross_validation_node)
    
    # Review & dispatch nodes
    graph.add_node("human_review_node", human_review_node)
    graph.add_node("dispatch_node", dispatch_node)
    
    # ====================================================================
    # ADD EDGES
    # ====================================================================
    
    # START → Parallel SWOT nodes
    graph.add_edge(START, "strength_analysis_node")
    graph.add_edge(START, "weakness_analysis_node")
    graph.add_edge(START, "opportunity_analysis_node")
    graph.add_edge(START, "threat_analysis_node")
    
    # Implicit convergence: All 4 SWOT nodes → context_integration_node
    # (LangGraph automatically waits for all parallel predecessor nodes)
    graph.add_edge("strength_analysis_node", "context_integration_node")
    graph.add_edge("weakness_analysis_node", "context_integration_node")
    graph.add_edge("opportunity_analysis_node", "context_integration_node")
    graph.add_edge("threat_analysis_node", "context_integration_node")
    
    # Sequential pipeline
    graph.add_edge("context_integration_node", "resilience_evaluation_node")
    graph.add_edge("resilience_evaluation_node", "insight_node")
    graph.add_edge("insight_node", "cross_validation_node")
    
    # Conditional branching: based on validation results
    try:
        # LangGraph 1.0+
        graph.add_conditional_edges(
            "cross_validation_node",
            need_human_review,
            {
                "human_review_node": "human_review_node",
                "dispatch_node": "dispatch_node"
            }
        )
    except AttributeError:
        # Older version fallback
        graph.add_conditional_edges(
            "cross_validation_node",
            need_human_review
        )
    
    # Terminal nodes → END
    graph.add_edge("dispatch_node", END)
    graph.add_edge("human_review_node", END)
    
    return graph


def build_analysis_graph_with_virtual_start() -> StateGraph:
    """
    Alternative builder with explicit virtual start node.
    
    Same graph as build_analysis_graph() but uses an explicit
    virtual START node to make parallel fan-out more explicit.
    
    Returns:
        Compiled StateGraph ready for execution
    """
    graph = StateGraph(AnalysisGraphState)
    
    # Virtual start node that sends to all 4 SWOT nodes
    def _start_swot_parallel(state: AnalysisGraphState):
        """Virtual start: sends to all 4 SWOT nodes in parallel."""
        return _send_swot_nodes(state)
    
    # Add nodes
    graph.add_node("_start_parallel", _start_swot_parallel)
    
    graph.add_node("strength_analysis_node", strength_analysis_node)
    graph.add_node("weakness_analysis_node", weakness_analysis_node)
    graph.add_node("opportunity_analysis_node", opportunity_analysis_node)
    graph.add_node("threat_analysis_node", threat_analysis_node)
    
    graph.add_node("context_integration_node", context_integration_node)
    graph.add_node("resilience_evaluation_node", resilience_evaluation_node)
    graph.add_node("insight_node", insight_node)
    graph.add_node("cross_validation_node", cross_validation_node)
    
    graph.add_node("human_review_node", human_review_node)
    graph.add_node("dispatch_node", dispatch_node)
    
    # Add edges
    graph.add_edge(START, "_start_parallel")
    
    # Implicit convergence
    graph.add_edge("strength_analysis_node", "context_integration_node")
    graph.add_edge("weakness_analysis_node", "context_integration_node")
    graph.add_edge("opportunity_analysis_node", "context_integration_node")
    graph.add_edge("threat_analysis_node", "context_integration_node")
    
    # Sequential
    graph.add_edge("context_integration_node", "resilience_evaluation_node")
    graph.add_edge("resilience_evaluation_node", "insight_node")
    graph.add_edge("insight_node", "cross_validation_node")
    
    # Conditional branching
    try:
        # LangGraph 1.0+
        graph.add_conditional_edges(
            "cross_validation_node",
            need_human_review,
            {
                "human_review_node": "human_review_node",
                "dispatch_node": "dispatch_node"
            }
        )
    except AttributeError:
        # Older version fallback
        graph.add_conditional_edges(
            "cross_validation_node",
            need_human_review
        )
    
    # Terminal
    graph.add_edge("dispatch_node", END)
    graph.add_edge("human_review_node", END)
    
    return graph


# ============================================================================
# GRAPH COMPILATION
# ============================================================================

def get_compiled_analysis_graph():
    """
    Build and compile the analysis graph for execution.
    
    Returns:
        Compiled graph (Runnable) ready for sync/async invocation
    """
    graph = build_analysis_graph()
    return graph.compile()


if __name__ == "__main__":
    # Example: Print graph structure for debugging
    graph = build_analysis_graph()
    compiled = graph.compile()
    
    print("✅ Analysis Graph Structure:")
    print(f"  Nodes: {list(graph.nodes.keys())}")
    print(f"\n✅ Sample execution:")
    print(f"  1. START → Parallel (S, W, O, T)")
    print(f"  2. → context_integration_node (implicit convergence)")
    print(f"  3. → resilience_evaluation_node")
    print(f"  4. → insight_node")
    print(f"  5. → cross_validation_node")
    print(f"  6. → [conditional] human_review_node OR dispatch_node")
    print(f"  7. → END")
