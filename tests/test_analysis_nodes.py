"""
Test suite for Task 3 analysis nodes.

Tests verify that each node function respects the latest AnalysisGraphState
contract and only writes its allowed keys.
"""

import unittest
from copy import deepcopy
from pathlib import Path
import os
import sys
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
os.environ["TASK3_DISABLE_LLM"] = "1"

from src.nodes.analysis_nodes import (
    context_integration_node,
    cross_validation_node,
    dispatch_node,
    human_review_node,
    insight_node,
    opportunity_analysis_node,
    resilience_evaluation_node,
    strength_analysis_node,
    threat_analysis_node,
    weakness_analysis_node,
)
from src.state.state import AnalysisGraphState


class MockDataFixtures:
    """Mock data fixtures aligned with the current Task 3 state contract."""

    @staticmethod
    def mock_market_context() -> Dict[str, str]:
        return {
            "TAM": "Global EV battery demand keeps expanding despite a temporary chasm.",
            "SAM": "Premium EV and ESS segments remain investable.",
            "CAGR": "Mid-teens growth expected after 2026 recovery.",
            "trend": "OEMs prioritize cost efficiency, localization, and resilient supply chains.",
            "company_a_position": "LGES is exposed to North America and JV-heavy expansion.",
            "company_b_position": "CATL holds domestic scale leadership and strong China OEM ties.",
        }

    @staticmethod
    def mock_portfolio(company: str) -> Dict[str, Any]:
        if company == "LGES":
            return {
                "core_services": ["Battery manufacturing", "Advanced R&D"],
                "revenue_contribution": {"BEV battery": "62%", "ESS": "14%"},
                "diversification_type": "vertical",
                "diversification_stage": "monetization",
                "core_competency": "North America localization and premium chemistry",
            }

        return {
            "core_services": ["Battery manufacturing", "Materials integration"],
            "revenue_contribution": {"BEV battery": "74%", "Energy storage": "11%"},
            "diversification_type": "vertical",
            "diversification_stage": "monetization",
            "core_competency": "Scale manufacturing and cost competitiveness",
        }

    @staticmethod
    def mock_company_swot(company: str) -> Dict[str, List[Dict[str, str]]]:
        if company == "LGES":
            return {
                "S": [
                    {
                        "point": "North America JV footprint with major OEMs",
                        "evidence": "Multiple production partnerships with automakers",
                        "source": "LGES IR",
                    }
                ],
                "W": [
                    {
                        "point": "Profitability pressure from slower EV demand recovery",
                        "evidence": "Utilization normalization remains incomplete",
                        "source": "Earnings summary",
                    }
                ],
                "O": [
                    {
                        "point": "Policy support for localized battery supply chains",
                        "evidence": "US incentives reward regional production",
                        "source": "Policy brief",
                    }
                ],
                "T": [
                    {
                        "point": "Raw material price swings can squeeze margins",
                        "evidence": "Lithium and nickel volatility remains elevated",
                        "source": "Commodity report",
                    }
                ],
            }

        return {
            "S": [
                {
                    "point": "Large-scale manufacturing lowers cost per kWh",
                    "evidence": "Industry-leading production volume",
                    "source": "CATL annual report",
                }
            ],
            "W": [
                {
                    "point": "Geographic concentration raises geopolitical exposure",
                    "evidence": "Revenue base remains China-heavy",
                    "source": "Industry analysis",
                }
            ],
            "O": [
                {
                    "point": "Energy storage demand expands adjacent battery markets",
                    "evidence": "Grid storage pipeline continues to grow",
                    "source": "Market outlook",
                }
            ],
            "T": [
                {
                    "point": "Trade barriers may limit overseas expansion speed",
                    "evidence": "Localization and tariff pressure continue",
                    "source": "Trade update",
                }
            ],
        }

    @staticmethod
    def mock_raw_findings() -> List[Dict[str, Any]]:
        return [
            {
                "agent_name": "LGES_Search",
                "source_type": "web_search",
                "subtopic": "portfolio",
                "raw_content": "LGES continues expanding North American manufacturing and JV capacity.",
                "key_points": ["LGES", "North America", "JV", "battery"],
                "sources": ["https://example.com/lges"],
            },
            {
                "agent_name": "CATL_Search",
                "source_type": "web_search",
                "subtopic": "scale",
                "raw_content": "CATL leverages large manufacturing scale and strong domestic customer ties.",
                "key_points": ["CATL", "scale", "EV", "battery"],
                "sources": ["https://example.com/catl"],
            },
        ]

    @staticmethod
    def empty_category_state() -> Dict[str, Any]:
        return {
            "lges_items": [],
            "catl_items": [],
            "comparative_points": [],
            "strategic_implications": [],
        }

    @staticmethod
    def clean_state() -> AnalysisGraphState:
        return AnalysisGraphState(
            market_context=MockDataFixtures.mock_market_context(),
            company_a_portfolio=MockDataFixtures.mock_portfolio("LGES"),
            company_b_portfolio=MockDataFixtures.mock_portfolio("CATL"),
            company_a_swot=MockDataFixtures.mock_company_swot("LGES"),
            company_b_swot=MockDataFixtures.mock_company_swot("CATL"),
            raw_findings=MockDataFixtures.mock_raw_findings(),
            swot_S=MockDataFixtures.empty_category_state(),
            swot_W=MockDataFixtures.empty_category_state(),
            swot_O=MockDataFixtures.empty_category_state(),
            swot_T=MockDataFixtures.empty_category_state(),
            comparative_swot={
                "lges_matrix": {"S": [], "W": [], "O": [], "T": []},
                "catl_matrix": {"S": [], "W": [], "O": [], "T": []},
            },
            final_insight={
                "resilience_evaluation": {
                    "total_score_lges": 0.0,
                    "total_score_catl": 0.0,
                    "winner": "Tie",
                    "evaluation_summary": "",
                    "evaluation_factors": [],
                },
                "key_differences": [],
                "strategic_winner": "Tie",
                "final_insights": [],
                "validation_notes": [],
            },
            consistency_flags=[],
        )

    @staticmethod
    def populated_state() -> AnalysisGraphState:
        state = deepcopy(MockDataFixtures.clean_state())
        state["swot_S"] = strength_analysis_node(state)["swot_S"]
        state["swot_W"] = weakness_analysis_node(state)["swot_W"]
        state["swot_O"] = opportunity_analysis_node(state)["swot_O"]
        state["swot_T"] = threat_analysis_node(state)["swot_T"]
        state["comparative_swot"] = context_integration_node(state)["comparative_swot"]
        state["final_insight"] = resilience_evaluation_node(state)["final_insight"]
        state["final_insight"] = insight_node(state)["final_insight"]
        return state


class TestSWOTAnalysisNodes(unittest.TestCase):
    """Test individual SWOT category analysis nodes."""

    def test_strength_analysis_node_returns_only_swot_S(self):
        result = strength_analysis_node(MockDataFixtures.clean_state())
        self.assertEqual(set(result.keys()), {"swot_S"})
        swot_s_data = result["swot_S"]
        self.assertIn("lges_items", swot_s_data)
        self.assertIn("catl_items", swot_s_data)
        self.assertIn("comparative_points", swot_s_data)
        self.assertIn("strategic_implications", swot_s_data)
        self.assertGreater(len(swot_s_data["lges_items"]), 0)
        self.assertGreater(len(swot_s_data["catl_items"]), 0)

    def test_weakness_analysis_node_returns_only_swot_W(self):
        result = weakness_analysis_node(MockDataFixtures.clean_state())
        self.assertEqual(set(result.keys()), {"swot_W"})
        self.assertIn("lges_items", result["swot_W"])
        self.assertIn("catl_items", result["swot_W"])

    def test_opportunity_analysis_node_returns_only_swot_O(self):
        result = opportunity_analysis_node(MockDataFixtures.clean_state())
        self.assertEqual(set(result.keys()), {"swot_O"})
        self.assertIn("lges_items", result["swot_O"])
        self.assertIn("catl_items", result["swot_O"])

    def test_threat_analysis_node_returns_only_swot_T(self):
        result = threat_analysis_node(MockDataFixtures.clean_state())
        self.assertEqual(set(result.keys()), {"swot_T"})
        self.assertIn("lges_items", result["swot_T"])
        self.assertIn("catl_items", result["swot_T"])


class TestIntegrationNodes(unittest.TestCase):
    """Test integration and synthesis nodes."""

    def test_context_integration_node_returns_only_comparative_swot(self):
        result = context_integration_node(MockDataFixtures.populated_state())
        self.assertEqual(set(result.keys()), {"comparative_swot"})
        comp_swot = result["comparative_swot"]
        self.assertIn("lges_matrix", comp_swot)
        self.assertIn("catl_matrix", comp_swot)
        self.assertEqual(set(comp_swot["lges_matrix"].keys()), {"S", "W", "O", "T"})
        self.assertEqual(set(comp_swot["catl_matrix"].keys()), {"S", "W", "O", "T"})

    def test_resilience_evaluation_node_adds_to_final_insight_only(self):
        state = MockDataFixtures.populated_state()
        result = resilience_evaluation_node(state)
        self.assertEqual(set(result.keys()), {"final_insight"})
        resilience = result["final_insight"]["resilience_evaluation"]
        self.assertIn("total_score_lges", resilience)
        self.assertIn("total_score_catl", resilience)
        self.assertIn("winner", resilience)
        self.assertIn("evaluation_summary", resilience)
        self.assertIn("evaluation_factors", resilience)

    def test_insight_node_merges_final_insight(self):
        state = MockDataFixtures.populated_state()
        result = insight_node(state)
        self.assertEqual(set(result.keys()), {"final_insight"})
        final_insight = result["final_insight"]
        self.assertIn("key_differences", final_insight)
        self.assertIn("strategic_winner", final_insight)
        self.assertIn("final_insights", final_insight)
        self.assertGreater(len(final_insight["final_insights"]), 0)

    def test_cross_validation_node_adds_validation_notes(self):
        state = MockDataFixtures.populated_state()
        result = cross_validation_node(state)
        self.assertEqual(set(result.keys()), {"final_insight"})
        self.assertIn("validation_notes", result["final_insight"])
        self.assertIsInstance(result["final_insight"]["validation_notes"], list)

    def test_human_review_node_requests_review_when_warnings_exist(self):
        state = MockDataFixtures.populated_state()
        state["final_insight"]["validation_notes"] = ["⚠ Evidence gap detected"]
        result = human_review_node(state)
        self.assertEqual(result, {"review_status": "review_required"})

    def test_human_review_node_approves_complete_clean_analysis(self):
        state = MockDataFixtures.populated_state()
        state["final_insight"]["validation_notes"] = ["✓ SWOT matrix validation passed"]
        result = human_review_node(state)
        self.assertEqual(result, {"review_status": "approved"})


class TestStateContractValidation(unittest.TestCase):
    """Test that nodes respect state contract and don't modify raw_findings."""

    def test_raw_findings_not_modified_by_any_node(self):
        clean_state = MockDataFixtures.clean_state()
        original_raw = deepcopy(clean_state["raw_findings"])

        nodes = [
            strength_analysis_node,
            weakness_analysis_node,
            opportunity_analysis_node,
            threat_analysis_node,
            context_integration_node,
            resilience_evaluation_node,
            insight_node,
            cross_validation_node,
        ]

        for node_func in nodes:
            result = node_func(clean_state)
            self.assertNotIn("raw_findings", result)
            self.assertEqual(clean_state["raw_findings"], original_raw)

    def test_dispatch_node_returns_exactly_6_fields(self):
        populated_state = MockDataFixtures.populated_state()
        populated_state["final_insight"] = cross_validation_node(populated_state)["final_insight"]
        result = dispatch_node(populated_state)

        expected_fields = {"swot_S", "swot_W", "swot_O", "swot_T", "comparative_swot", "final_insight"}
        self.assertEqual(set(result.keys()), expected_fields)
        self.assertIsInstance(result["swot_S"], dict)
        self.assertIsInstance(result["swot_W"], dict)
        self.assertIsInstance(result["swot_O"], dict)
        self.assertIsInstance(result["swot_T"], dict)
        self.assertIsInstance(result["comparative_swot"], dict)
        self.assertIsInstance(result["final_insight"], dict)

    def test_no_prohibited_fields_in_any_node_output(self):
        clean_state = MockDataFixtures.clean_state()
        prohibited_fields = {
            "resilience_score",
            "validation_result",
            "preliminary_insight",
            "review_feedback",
            "warnings",
            "human_review_flags",
        }

        nodes = [
            strength_analysis_node,
            weakness_analysis_node,
            opportunity_analysis_node,
            threat_analysis_node,
            context_integration_node,
            resilience_evaluation_node,
            insight_node,
            cross_validation_node,
            dispatch_node,
        ]

        dispatch_ready_state = MockDataFixtures.populated_state()
        dispatch_ready_state["final_insight"] = cross_validation_node(dispatch_ready_state)["final_insight"]

        for node_func in nodes:
            node_input = dispatch_ready_state if node_func is dispatch_node else clean_state
            result = node_func(node_input)
            for field in prohibited_fields:
                self.assertNotIn(field, result, f"{node_func.__name__} returned prohibited field: {field}")


if __name__ == "__main__":
    unittest.main()
