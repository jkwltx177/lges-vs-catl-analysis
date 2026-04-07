"""Data Refine Agent StateGraph 조립 + compile.

사용 예:
    from src.agents.data_refine_graph import graph

    result = graph.invoke({
        "company_a": company_a_raw,
        "company_b": company_b_raw,
        "raw_findings": raw_findings_list,
    }, config={"configurable": {"thread_id": "refine_01"}})
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.nodes.data_processing_nodes import (
    clean_node,
    market_node,
    portfolio_node,
    swot_map_node,
)
from src.state.state import DataRefineGraphState

# ----------------------------------------------------------------
# Graph 조립
# ----------------------------------------------------------------

builder = StateGraph(DataRefineGraphState)

# 노드 등록
builder.add_node("clean_node", clean_node)
builder.add_node("market_node", market_node)
builder.add_node("portfolio_node", portfolio_node)
builder.add_node("swot_map_node", swot_map_node)

# ----------------------------------------------------------------
# 엣지 연결
# ----------------------------------------------------------------

builder.add_edge(START, "clean_node")

# clean_node 이후 병렬 처리
builder.add_edge("clean_node", "market_node")
builder.add_edge("clean_node", "portfolio_node")
builder.add_edge("clean_node", "swot_map_node")

builder.add_edge("market_node", END)
builder.add_edge("portfolio_node", END)
builder.add_edge("swot_map_node", END)

# ----------------------------------------------------------------
# Compile
# ----------------------------------------------------------------

graph = builder.compile(checkpointer=MemorySaver())
