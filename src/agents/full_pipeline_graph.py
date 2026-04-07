"""Top-level orchestration for Research -> Refine -> Analysis."""

from __future__ import annotations

from typing import Any, Dict

from ..nodes.bridge_nodes import bridge_node_1, bridge_node_2


def run_research_refine_analysis(initial_state: Dict[str, Any], thread_prefix: str = "e2e") -> Dict[str, Any]:
    """Run the three role graphs sequentially with explicit bridge transfers."""
    from .data_refine_graph import graph as refine_graph
    from .research_graph import graph as research_graph
    from ..nodes.graph_analysis import get_compiled_analysis_graph

    research_config = {"configurable": {"thread_id": f"{thread_prefix}_research"}}
    refine_config = {"configurable": {"thread_id": f"{thread_prefix}_refine"}}
    analysis_config = {"configurable": {"thread_id": f"{thread_prefix}_analysis"}}

    research_graph.invoke(initial_state, config=research_config)
    research_state = research_graph.get_state(research_config).values
    refine_input = bridge_node_1(research_state)

    refine_graph.invoke(refine_input, config=refine_config)
    refine_state = refine_graph.get_state(refine_config).values
    analysis_input = bridge_node_2(refine_state)

    analysis_graph = get_compiled_analysis_graph()
    return analysis_graph.invoke(analysis_input, config=analysis_config)


def run_full_pipeline_with_report(initial_state: Dict[str, Any], thread_prefix: str = "e2e") -> Dict[str, Any]:
    """Research → Refine → Analysis → Report(섹션·merge·MD/PDF)."""
    from src.core.report_workflow import run_report_from_report_state
    from src.nodes.report.bridge import bridge_from_analysis

    analysis = run_research_refine_analysis(initial_state, thread_prefix=thread_prefix)
    report_input = bridge_from_analysis(analysis)
    return run_report_from_report_state(report_input)
