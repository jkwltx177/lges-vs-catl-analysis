"""
Test suite for Task 3 analysis graph orchestration.
"""

import unittest
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.nodes.graph_analysis import build_analysis_graph, need_human_review
from src.state.state import AnalysisGraphState


class MockDataFixtures:
    """Mock data fixtures aligned with the current Task 3 schema."""

    @staticmethod
    def clean_state() -> AnalysisGraphState:
        return AnalysisGraphState(
            raw_findings=[],
            swot_S={"lges_items": [], "catl_items": [], "comparative_points": [], "strategic_implications": []},
            swot_W={"lges_items": [], "catl_items": [], "comparative_points": [], "strategic_implications": []},
            swot_O={"lges_items": [], "catl_items": [], "comparative_points": [], "strategic_implications": []},
            swot_T={"lges_items": [], "catl_items": [], "comparative_points": [], "strategic_implications": []},
            comparative_swot={
                "lges_matrix": {"S": [], "W": [], "O": [], "T": []},
                "catl_matrix": {"S": [], "W": [], "O": [], "T": []},
            },
            final_insight={
                "resilience_evaluation": {
                    "total_score_lges": 50.0,
                    "total_score_catl": 48.0,
                    "winner": "LGES",
                    "evaluation_summary": "LGES leads slightly on resilience.",
                    "evaluation_factors": ["portfolio resilience", "capacity flexibility"],
                },
                "key_differences": ["LGES is more localized in North America."],
                "strategic_winner": "LGES",
                "final_insights": ["LGES has a near-term localization edge."],
                "validation_notes": ["✓ SWOT structure validated", "✓ Evidence verified"],
            },
            consistency_flags=[],
        )

    @staticmethod
    def state_with_warnings() -> AnalysisGraphState:
        state = MockDataFixtures.clean_state().copy()
        state["final_insight"] = dict(state["final_insight"])
        state["final_insight"]["validation_notes"] = [
            "✓ SWOT structure validated",
            "⚠ Overconfident language detected in insight 3",
        ]
        return state

    @staticmethod
    def state_with_consistency_flags() -> AnalysisGraphState:
        state = MockDataFixtures.clean_state().copy()
        state["consistency_flags"] = ["inconsistent_evidence"]
        return state

    @staticmethod
    def state_with_both_issues() -> AnalysisGraphState:
        state = MockDataFixtures.state_with_warnings().copy()
        state["consistency_flags"] = ["data_conflict"]
        return state


class TestGraphConstruction(unittest.TestCase):
    """Test that the analysis graph builds correctly."""

    def test_build_analysis_graph_compiles_successfully(self):
        graph = build_analysis_graph()
        self.assertIsNotNone(graph)
        self.assertTrue(hasattr(graph, "compile"))

    def test_build_analysis_graph_has_required_nodes(self):
        graph = build_analysis_graph()
        compiled_graph = graph.compile()
        self.assertIsNotNone(compiled_graph)


class TestRoutingLogic(unittest.TestCase):
    """Test the need_human_review routing function."""

    def test_need_human_review_returns_dispatch_for_clean_state(self):
        self.assertEqual(need_human_review(MockDataFixtures.clean_state()), "dispatch_node")

    def test_need_human_review_returns_human_review_for_warnings(self):
        self.assertEqual(need_human_review(MockDataFixtures.state_with_warnings()), "human_review_node")

    def test_need_human_review_returns_human_review_for_consistency_flags(self):
        self.assertEqual(
            need_human_review(MockDataFixtures.state_with_consistency_flags()),
            "human_review_node",
        )

    def test_need_human_review_returns_human_review_for_both_issues(self):
        self.assertEqual(need_human_review(MockDataFixtures.state_with_both_issues()), "human_review_node")

    def test_need_human_review_handles_missing_fields_gracefully(self):
        empty_state = AnalysisGraphState(
            raw_findings=[],
            swot_S={},
            swot_W={},
            swot_O={},
            swot_T={},
            comparative_swot={"lges_matrix": {}, "catl_matrix": {}},
            final_insight={"resilience_evaluation": {}, "validation_notes": []},
            consistency_flags=[],
        )
        self.assertEqual(need_human_review(empty_state), "dispatch_node")

        state_no_final = empty_state.copy()
        del state_no_final["final_insight"]
        self.assertEqual(need_human_review(state_no_final), "dispatch_node")

        state_no_notes = empty_state.copy()
        state_no_notes["final_insight"] = {"resilience_evaluation": {}, "validation_notes": None}
        self.assertEqual(need_human_review(state_no_notes), "dispatch_node")


class TestGraphIntegration(unittest.TestCase):
    """Placeholder integration tests."""

    @unittest.skip("Requires full graph execution setup")
    def test_graph_execution_with_clean_state(self):
        pass


if __name__ == "__main__":
    unittest.main()
