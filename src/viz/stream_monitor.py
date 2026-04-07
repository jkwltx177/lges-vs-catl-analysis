"""
Rich 기반 실시간 스트림 시각화.

독립 실행 (그래프 구조 시각화):
    python -m src.viz.stream_monitor

파이프라인에서 사용:
    python -m src.run --monitor
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from rich import box
from rich.console import Console
from rich.panel import Panel

console = Console()

NODE_STYLE: Dict[str, Tuple[str, str]] = {
    "initialize":              ("green",    "🟢"),
    "query_generation":        ("cyan",     "🔵"),
    "strategy_routing":        ("blue",     "🔵"),
    "vectordb_retrieval":      ("magenta",  "🟣"),
    "web_retrieval":           ("magenta",  "🟣"),
    "company_research":        ("yellow",   "🟡"),
    "comparative_research":    ("yellow",   "🟡"),
    "merge_results":           ("yellow",   "🟡"),
    "validate_evidence":       ("yellow",   "🟡"),
    "coverage_check":          ("yellow",   "🟡"),
    "build_output":            ("green",    "🟢"),
    "human_review":            ("red",      "🔴"),
    "human_review_node":       ("red",      "🔴"),
    "deliver":                 ("green",    "🟢"),
    "dispatch_node":           ("green",    "🟢"),
    "strength_analysis_node":  ("cyan",     "🔵"),
    "weakness_analysis_node":  ("cyan",     "🔵"),
    "opportunity_analysis_node": ("cyan",   "🔵"),
    "threat_analysis_node":    ("cyan",     "🔵"),
    "context_integration_node": ("yellow",  "🟡"),
    "resilience_evaluation_node": ("yellow","🟡"),
    "insight_node":            ("yellow",   "🟡"),
    "cross_validation_node":   ("yellow",   "🟡"),
    "__interrupt__":           ("red bold", "⛔"),
}


class RichMonitor:
    """노드 완료 이벤트를 Rich 패널로 출력."""

    def __init__(self) -> None:
        self.completed_nodes: List[Tuple[str, dict]] = []
        self.console = console

    def on_node_complete(self, node_name: str, output: dict) -> None:
        style, icon = NODE_STYLE.get(node_name, ("white", "⬜"))
        self.completed_nodes.append((node_name, output))
        panel = self._make_node_panel(node_name, output, style, icon)
        self.console.print(panel)

    def _make_node_panel(self, node_name: str, output: dict, style: str, icon: str) -> Panel:
        lines = self._extract_metrics(node_name, output)
        content = "\n".join(lines) if lines else "(출력 없음)"
        return Panel(
            content,
            title=f"[{style}]{icon} {node_name}[/{style}]",
            border_style=style,
            box=box.ROUNDED,
        )

    def _extract_metrics(self, node_name: str, output: dict) -> List[str]:
        """각 노드별 핵심 수치만 추출."""
        lines: List[str] = []

        if node_name == "vectordb_retrieval":
            docs = [d for d in output.get("raw_documents", []) if d.get("source_type") == "vector_db"]
            dists = [d["distance"] for d in docs if d.get("distance") is not None]
            lines.append(f"VDB 청크: {len(docs)}개")
            if dists:
                lines.append(f"거리 min={min(dists):.3f}  avg={sum(dists)/len(dists):.3f}")

        elif node_name == "web_retrieval":
            docs = [d for d in output.get("raw_documents", []) if d.get("source_type") == "web_search"]
            lines.append(f"웹 문서: {len(docs)}개")

        elif node_name == "merge_results":
            grouped  = output.get("grouped_documents", {})
            coverage = output.get("query_coverage", {})
            counts   = [len(v) for v in grouped.values()]
            if counts:
                lines.append(f"쿼리 {len(grouped)}개  총 {sum(counts)}건")
            gap = sum(
                1 for v in coverage.values()
                if v.get("avg_distance") is None or v.get("avg_distance", 1) >= 0.65
            )
            lines.append(f"갭 쿼리: {gap}/{len(coverage)}개")

        elif node_name == "validate_evidence":
            v = len(output.get("validated_evidence", []))
            r = len(output.get("rejected_evidence", []))
            if v + r:
                lines.append(f"통과: {v}개  탈락: {r}개  ({v/(v+r)*100:.0f}%)")
            else:
                lines.append("문서 없음")

        elif node_name == "coverage_check":
            lines.append(
                f"상태: {output.get('coverage_status', '-')}  "
                f"retry: {output.get('retry_count', '-')}"
            )

        elif node_name == "build_output":
            lines.append(f"key_findings: {len(output.get('key_findings', []))}개")

        elif node_name in ("insight_node", "dispatch_node"):
            fi = output.get("final_insight", {})
            if fi:
                lines.append(f"winner: {fi.get('strategic_winner', '-')}")

        elif node_name == "resilience_evaluation_node":
            fi = output.get("final_insight", {})
            re = fi.get("resilience_evaluation", {}) if fi else {}
            if re:
                lines.append(f"LGES: {re.get('total_score_lges', '-')}  CATL: {re.get('total_score_catl', '-')}")

        elif node_name == "cross_validation_node":
            fi = output.get("final_insight", {})
            notes = fi.get("validation_notes", []) if fi else []
            warnings = [n for n in notes if str(n).startswith("⚠")]
            lines.append(f"경고: {len(warnings)}개  전체: {len(notes)}개")

        return lines


# ============================================================================
# Graph visualization helpers
# ============================================================================

def draw_graph_ascii(graph: object, title: str = "Graph Structure") -> None:
    """그래프 ASCII 다이어그램 출력."""
    console.print(Panel(
        graph.get_graph().draw_ascii(),  # type: ignore[attr-defined]
        title=f"[bold cyan]{title}[/bold cyan]",
        border_style="cyan",
    ))


def draw_graph_mermaid(graph: object, save_path: str | None = None) -> None:
    """Mermaid 다이어그램 출력 (+ 파일 저장 옵션)."""
    mermaid_str = graph.get_graph().draw_mermaid()  # type: ignore[attr-defined]
    console.print(Panel(mermaid_str, title="[bold]Mermaid Diagram[/bold]"))
    if save_path:
        with open(save_path, "w") as f:
            f.write(mermaid_str)
        console.print(f"[green]저장: {save_path}[/green]")


# ============================================================================
# 독립 실행: 그래프 구조 시각화
# ============================================================================

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    from src.agents.research_graph import graph as research_graph
    from src.nodes.graph_analysis import get_compiled_analysis_graph

    analysis_graph = get_compiled_analysis_graph()

    draw_graph_ascii(research_graph, "Research Graph")
    draw_graph_mermaid(research_graph, save_path="report/research_graph.mmd")
    draw_graph_ascii(analysis_graph, "Analysis Graph")
