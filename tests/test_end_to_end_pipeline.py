"""End-to-end mock test for Research -> Refine -> Analysis bridging."""

import unittest
from pathlib import Path
import os
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ["TASK3_DISABLE_LLM"] = "1"

from src.nodes.bridge_nodes import bridge_node_1, bridge_node_2
from src.nodes.graph_analysis import get_compiled_analysis_graph
from src.state.state import DataRefineGraphState, ResearchGraphState


class TestEndToEndPipeline(unittest.TestCase):
    def test_research_refine_analysis_mock_flow(self):
        research_state = ResearchGraphState(
            company_a={
                "name": "LGES",
                "items": [
                    {"content": "LGES North America expansion", "category": "market", "source": "report-a"}
                ],
            },
            company_b={
                "name": "CATL",
                "items": [
                    {"content": "CATL scale manufacturing", "category": "market", "source": "report-b"}
                ],
            },
            raw_findings=[
                {
                    "agent_name": "LGES_Search",
                    "source_type": "web_search",
                    "subtopic": "portfolio",
                    "raw_content": "LGES continues expanding North American battery production.",
                    "key_points": ["LGES", "North America", "battery"],
                    "sources": ["https://example.com/lges"],
                },
                {
                    "agent_name": "CATL_Search",
                    "source_type": "web_search",
                    "subtopic": "scale",
                    "raw_content": "CATL maintains manufacturing scale and strong domestic share.",
                    "key_points": ["CATL", "scale", "battery"],
                    "sources": ["https://example.com/catl"],
                },
            ],
            query_coverage={"mock query": {"count": 2}},
        )

        refine_input = bridge_node_1(research_state)
        self.assertEqual(set(refine_input.keys()), {"company_a", "company_b", "raw_findings", "query_coverage"})

        refine_state = DataRefineGraphState(
            **refine_input,
            market_context={
                "TAM": "Global EV battery market",
                "SAM": "Premium EV and ESS",
                "CAGR": "15%",
                "trend": "Localization and cost efficiency",
                "company_a_position": "North America focused",
                "company_b_position": "China scale leader",
            },
            company_a_portfolio={
                "core_services": ["Battery manufacturing", "R&D"],
                "revenue_contribution": {"BEV battery": "62%"},
                "diversification_type": "vertical",
                "diversification_stage": "monetization",
                "core_competency": "North America localization",
            },
            company_b_portfolio={
                "core_services": ["Battery manufacturing", "Materials integration"],
                "revenue_contribution": {"BEV battery": "74%"},
                "diversification_type": "vertical",
                "diversification_stage": "monetization",
                "core_competency": "Scale manufacturing",
            },
            company_a_swot={
                "S": [{"content": "North America JV footprint", "source": "report-a", "is_fact": True}],
                "W": [{"content": "Profitability pressure", "source": "report-a", "is_fact": True}],
                "O": [{"content": "IRA localization upside", "source": "report-a", "is_fact": True}],
                "T": [{"content": "Raw material volatility", "source": "report-a", "is_fact": True}],
            },
            company_b_swot={
                "S": [{"content": "Scale manufacturing", "source": "report-b", "is_fact": True}],
                "W": [{"content": "Geographic concentration", "source": "report-b", "is_fact": True}],
                "O": [{"content": "ESS expansion", "source": "report-b", "is_fact": True}],
                "T": [{"content": "Trade barriers", "source": "report-b", "is_fact": True}],
            },
        )

        analysis_input = bridge_node_2(refine_state)
        self.assertEqual(
            set(analysis_input.keys()),
            {
                "market_context",
                "company_a_portfolio",
                "company_b_portfolio",
                "company_a_swot",
                "company_b_swot",
                "raw_findings",
            },
        )

        graph = get_compiled_analysis_graph()
        final_state = graph.invoke(analysis_input)

        expected_keys = {"swot_S", "swot_W", "swot_O", "swot_T", "comparative_swot", "final_insight"}
        self.assertTrue(expected_keys.issubset(set(final_state.keys())))
        self.assertIn("comparative_swot", final_state)
        self.assertIn("final_insight", final_state)
        self.assertIn("resilience_evaluation", final_state["final_insight"])
        self.assertIn("key_differences", final_state["final_insight"])
        self.assertIn("final_insights", final_state["final_insight"])


if __name__ == "__main__":
    unittest.main()
