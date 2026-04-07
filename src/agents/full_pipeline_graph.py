"""Top-level orchestration for Research -> Refine -> Analysis -> (optional) Report."""

from __future__ import annotations

import os
from typing import Any, Dict, List

from ..nodes.bridge_nodes import bridge_node_1, bridge_node_2


def _warn_missing(stage: str, state: Dict[str, Any], keys: List[str], *, verbose: bool) -> None:
    if not verbose:
        return
    missing = [k for k in keys if not state.get(k)]
    if missing:
        print(f"[pipeline] ⚠ {stage}: 비어 있거나 없는 키 — {missing}", flush=True)
    else:
        print(f"[pipeline] ✓ {stage}: 필수 키 존재 — {keys}", flush=True)


def run_research_refine_analysis(
    initial_state: Dict[str, Any],
    thread_prefix: str = "e2e",
    *,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Run the three role graphs sequentially with explicit bridge transfers."""
    from .data_refine_graph import graph as refine_graph
    from .research_graph import graph as research_graph
    from ..nodes.graph_analysis import get_compiled_analysis_graph

    research_config = {"configurable": {"thread_id": f"{thread_prefix}_research"}}
    refine_config = {"configurable": {"thread_id": f"{thread_prefix}_refine"}}
    analysis_config = {"configurable": {"thread_id": f"{thread_prefix}_analysis"}}

    if verbose:
        print("[pipeline] (1/3) Research 그래프 실행 중…", flush=True)
    research_graph.invoke(initial_state, config=research_config)
    research_state = research_graph.get_state(research_config).values
    _warn_missing(
        "Research→bridge",
        research_state,
        ["company_a", "company_b", "raw_findings"],
        verbose=verbose,
    )
    refine_input = bridge_node_1(research_state)

    if verbose:
        print("[pipeline] (2/3) Refine(자료 정리) 그래프 실행 중…", flush=True)
    refine_graph.invoke(refine_input, config=refine_config)
    refine_state = refine_graph.get_state(refine_config).values
    _warn_missing(
        "Refine→bridge",
        refine_state,
        [
            "market_context",
            "company_a_portfolio",
            "company_b_portfolio",
            "company_a_swot",
            "company_b_swot",
            "query_coverage",
        ],
        verbose=verbose,
    )
    analysis_input = bridge_node_2(refine_state)

    if verbose:
        print("[pipeline] (3/3) Analysis 그래프 실행 중…", flush=True)
    analysis_graph = get_compiled_analysis_graph()
    out = analysis_graph.invoke(analysis_input, config=analysis_config)
    _warn_missing(
        "Analysis→Report",
        out,
        ["comparative_swot", "final_insight"],
        verbose=verbose,
    )
    return out


def run_full_pipeline_with_report(
    initial_state: Dict[str, Any],
    thread_prefix: str = "e2e",
    *,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Research → Refine → Analysis → Report(섹션·merge·MD/PDF)."""
    from src.core.report_workflow import run_report_from_analysis

    analysis = run_research_refine_analysis(
        initial_state, thread_prefix=thread_prefix, verbose=verbose
    )
    if verbose:
        print("[pipeline] (4/4) Report 그래프 실행 중…", flush=True)
    return run_report_from_analysis(analysis)


def check_openai_config() -> tuple[bool, str]:
    """Research~Report 전 구간에서 사용하는 OPENAI_API_KEY (.env)."""
    import src.core.env  # noqa: F401

    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        return False, (
            "OPENAI_API_KEY가 설정되어 있지 않습니다.\n"
            "  프로젝트 루트에 `.env` 파일을 두고 다음 형식으로 넣어 주세요:\n"
            "  OPENAI_API_KEY=sk-...\n"
            "  (또는 셸에서 export OPENAI_API_KEY=... )\n"
        )
    if key.startswith("your_"):
        return False, "OPENAI_API_KEY가 placeholder(`your_...`)입니다. 실제 키로 바꿔 주세요.\n"
    return True, ""
