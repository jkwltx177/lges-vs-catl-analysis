"""Research Agent StateGraph 조립 + compile.

사용 예:
    from src.agents.research_graph import graph

    result = graph.invoke({
        "goal": "LGES vs CATL SWOT 비교 분석",
        "target_companies": ["LGES", "CATL"],
        "report_topic": "EV 배터리 시장 경쟁력 분석",
        "max_retry": 2,
    }, config={"configurable": {"thread_id": "research_01"}})
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.nodes.research_nodes import (
    build_output_node,
    company_research_node,
    comparative_research_node,
    coverage_check_node,
    deliver_node,
    human_review_node,
    initialize_node,
    merge_results_node,
    query_generation_node,
    strategy_routing_node,
    validate_evidence_node,
    vectordb_retrieval_node,
    web_retrieval_node,
)
from src.state.state import ResearchGraphState

# ----------------------------------------------------------------
# Graph 조립
# ----------------------------------------------------------------

builder = StateGraph(ResearchGraphState)

# 노드 등록
builder.add_node("initialize", initialize_node)
builder.add_node("query_generation", query_generation_node)
builder.add_node("strategy_routing", strategy_routing_node)
builder.add_node("vectordb_retrieval", vectordb_retrieval_node)
builder.add_node("web_retrieval", web_retrieval_node)
builder.add_node("company_research", company_research_node)
builder.add_node("comparative_research", comparative_research_node)
builder.add_node("merge_results", merge_results_node)
builder.add_node("validate_evidence", validate_evidence_node)
builder.add_node("coverage_check", coverage_check_node)
builder.add_node("build_output", build_output_node)
builder.add_node("human_review", human_review_node)
builder.add_node("deliver", deliver_node)

# ----------------------------------------------------------------
# 엣지 연결
# ----------------------------------------------------------------

builder.add_edge(START, "initialize")
builder.add_edge("initialize", "query_generation")
builder.add_edge("query_generation", "strategy_routing")

# 검색 병렬 실행 (strategy_routing → vectordb & web 동시)
builder.add_edge("strategy_routing", "vectordb_retrieval")
builder.add_edge("strategy_routing", "web_retrieval")

# 두 검색 완료 후 company_research (Fan-out 후 Fan-in 패턴)
builder.add_edge("vectordb_retrieval", "company_research")
builder.add_edge("web_retrieval", "company_research")

builder.add_edge("company_research", "comparative_research")
builder.add_edge("comparative_research", "merge_results")
builder.add_edge("merge_results", "validate_evidence")
builder.add_edge("validate_evidence", "coverage_check")


# ----------------------------------------------------------------
# Coverage Check 조건부 엣지
# ----------------------------------------------------------------

def _coverage_router(state: ResearchGraphState) -> str:
    """coverage_status에 따라 다음 노드 결정."""
    if state.get("coverage_status") == "sufficient":
        return "build_output"
    # insufficient → 루프백 (retry_count는 coverage_check_node에서 이미 증가)
    return "query_generation"


builder.add_conditional_edges(
    "coverage_check",
    _coverage_router,
    {
        "build_output": "build_output",
        "query_generation": "query_generation",
    },
)

builder.add_edge("build_output", "human_review")
builder.add_edge("human_review", "deliver")
builder.add_edge("deliver", END)

# ----------------------------------------------------------------
# Compile
# ----------------------------------------------------------------

graph = builder.compile(checkpointer=MemorySaver())

# ----------------------------------------------------------------
# 간단 테스트 진입점
# ----------------------------------------------------------------

if __name__ == "__main__":
    print(graph.get_graph().draw_mermaid())
