#!/usr/bin/env python3
"""
앞단(조사·정제·분석) 없이 보고서 Task.4만 미리 돌려보기.

  # 레이아웃만 (LLM/API 없음) — 제목·작성일·요약·목차·참고문헌 순서·MD/PDF 저장 확인
  PYTHONPATH=. python scripts/run_report_debug.py --merge-only

  # 전체 그래프 + 스텁 LLM (API 키 없이 섹션 문단 스텁)
  PYTHONPATH=. python scripts/run_report_debug.py --stub

  # 전체 그래프 + .env 의 OPENAI_API_KEY 로 실제 생성
  PYTHONPATH=. python scripts/run_report_debug.py

프로젝트 루트에서 실행하는 것을 권장합니다.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# 프로젝트 루트를 path에 (스크립트 직접 실행 시)
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _mock_raw_findings():
    from src.state.state import ResearchFinding

    long = (
        "LG Energy Solution(LGES)은 북미·유럽 EV 배터리 수요 대응을 위해 "
        "현지 JV 및 캐파 확대를 진행 중이며, IRA·FEOC 규정에 맞춘 공급망 재편이 핵심 이슈다. "
        "CATL은 LFP·CTP·나트륨이온 등 제품 라인을 넓히고 ESS·해외 OEM 수주를 병행한다. "
        "글로벌 EV 수요 둔화(캐즘)와 금리·보조금·충전 인프라 변수가 동시에 작용하고 있다. " * 12
    )
    rf: ResearchFinding = {
        "agent_name": "Debug_Mock",
        "source_type": "vector_db",
        "subtopic": "EV 캐즘·IRA·양사 전략",
        "raw_content": long,
        "key_points": [
            "캐즘·금리·보조금·인프라",
            "IRA/FEOC·CRMA 맥락",
            "LGES 북미 JV·CATL LFP/ESS",
        ],
        "sources": [
            "https://www.example.com/reports/ev-battery-2025",
            "https://www.example.com/news/lges-na",
        ],
    }
    return [rf]


def build_mock_analysis_state():
    """분석 단계가 끝난 것처럼 최소 필드를 채운 AnalysisGraphState."""
    from src.state.state import (
        AnalysisGraphState,
        CompanyPortfolio,
        ComparativeSwotState,
        FinalInsight,
        MarketContext,
        ResilienceEvaluation,
    )

    market: MarketContext = {
        "TAM": "약 XXX GWh (예시)",
        "SAM": "글로벌 EV 배터리 셀 시장",
        "CAGR": "2024–2030E 약 10–15% (예시)",
        "trend": "EV 수요 정체·캐즘, 지역별 IRA·보조금·공급망 규제 강화",
        "company_a_position": "북미·유럽 프리미엄 OEM·합작 중심",
        "company_b_position": "글로벌 점유 확대·원가·규모, ESS·LFP 확장",
    }

    pa: CompanyPortfolio = {
        "core_services": ["NCM 프리미엄 셀", "원통형·파우치", "에너지 저장(ESS)"],
        "revenue_contribution": {"BEV 배터리": "62% (예시)", "ESS": "8% (예시)"},
        "diversification_type": "수직·수평 혼합",
        "diversification_stage": "투자~수익화 병행",
        "core_competency": "품질·OEM 관계·북미 현지화",
    }
    pb: CompanyPortfolio = {
        "core_services": ["LFP·NMC", "CTP", "나트륨이온(선택)", "ESS 패키지"],
        "revenue_contribution": {"EV 배터리": "약 70%+ (예시)", "ESS": "증가 추세"},
        "diversification_type": "수직 계열화·규모의 경제",
        "diversification_stage": "수익화·글로벌 확장",
        "core_competency": "원가·캐파·제품 조합",
    }

    comp: ComparativeSwotState = {
        "comparative_summary": "LGES는 OEM·규제 대응, CATL은 규모·원가 중심(디버그).",
        "strategic_positioning": "캐즘·IRA 환경에서 현지화 vs 규모 효율.",
        "consistency_flags": [],
        "lges_matrix": {},
        "catl_matrix": {},
    }

    resilience: ResilienceEvaluation = {
        "total_score_lges": 7.0,
        "total_score_catl": 7.5,
        "winner": "n/a",
        "evaluation_summary": "디버그용 회복탄력성 요약",
        "evaluation_factors": ["규제", "포트폴리오"],
    }

    insight: FinalInsight = {
        "key_differences": ["공급망·규제 대응 vs 규모·원가"],
        "resilience_evaluation": resilience,
        "strategic_winner": "(분석 목적상 우열 단정 지양 — 디버그 목 데이터)",
        "final_insights": [
            "캐즘기에는 수익성·현금흐름·포트폴리오 균형이 핵심",
            "규제(IRA/FEOC)에 맞는 공급망·현지 생산이 경쟁력을 가른다",
        ],
    }

    state: AnalysisGraphState = {
        "market_context": market,
        "company_a_portfolio": pa,
        "company_b_portfolio": pb,
        "comparative_swot": comp,
        "final_insight": insight,
        "raw_findings": _mock_raw_findings(),
    }
    return state


def _mock_prefilled_sections():
    """merge-only용: LLM 없이 섹션 문자열만 채움."""
    return {
        "section0": (
            "- **LGES (한 줄):** 북미·유럽 OEM·규제 대응·프리미엄 포지셔닝.\n"
            "- **CATL (한 줄):** 규모·원가·LFP/ESS·글로벌 확장.\n"
            "- **결론:** 캐즘·규제 환경에서 공급망·포트폴리오 균형이 승부처.(디버그 더미)"
        ),
        "section1": "### 2.1 캐즘 배경\n고금리·보조금·인프라 등 **3가지 이상** 요인(디버그).\n\n### 2.3 IRA·CRMA\n예시 문장.",
        "section2": "### LGES\n북미 JV·Physical AI·BaaS/재활용 언급 예시(디버그).",
        "section3": "### CATL\n나트륨이온·ESS·LRS·수직계열화 예시(디버그).",
        "section4": "| 구분 | LGES | CATL |\n| --- | --- | --- |\n| 예시 | A | B |",
        "section5": "### 승부처\n2026년 이후 전망·국내 산업 제언 예시(디버그).",
        "section6": "- 기관(2025). 예시 보고서. https://www.example.com/ref\n- 웹(2025-01-01). 예시 기사. https://www.example.com/news",
    }


def run_merge_only():
    from src.nodes.report.bridge import bridge_from_analysis
    from src.nodes.report.merge_node import merge_node

    initial = bridge_from_analysis(build_mock_analysis_state())
    initial["sections"] = _mock_prefilled_sections()
    initial["report_title"] = "[디버그] LGES vs CATL 보고서"
    initial["report_date"] = "2026-04-07"
    return merge_node(initial)


def run_full_graph(*, stub: bool):
    from src.core.report_workflow import run_report_from_analysis

    if stub:
        os.environ["OPENAI_API_KEY"] = ""
    return run_report_from_analysis(build_mock_analysis_state())


def main() -> int:
    parser = argparse.ArgumentParser(description="보고서 파이프라인 단독 디버그")
    parser.add_argument(
        "--merge-only",
        action="store_true",
        help="merge_node만 실행(LLM 없음). 레이아웃·MD/PDF 경로 확인용",
    )
    parser.add_argument(
        "--stub",
        action="store_true",
        help="전체 그래프를 OPENAI_API_KEY 없이 스텁 LLM으로 실행",
    )
    args = parser.parse_args()

    from dotenv import load_dotenv

    load_dotenv(_ROOT / ".env")

    if args.merge_only:
        out = run_merge_only()
        print("=== merge-only ===")
        print("final_report_md_path:", out.get("final_report_md_path"))
        print("final_report_pdf_path:", out.get("final_report_pdf_path") or "(PDF 실패 또는 미생성)")
        print("warnings:", out.get("warnings"))
        print("\n--- final_report 앞 1200자 ---\n")
        print((out.get("final_report") or "")[:1200])
        return 0

    if args.stub:
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ["OPENAI_API_KEY"] = ""

    result = run_full_graph(stub=args.stub)
    print("=== report graph ===")
    print("stub_mode:", bool(args.stub))
    print("final_report_md_path:", result.get("final_report_md_path"))
    print("final_report_pdf_path:", result.get("final_report_pdf_path") or "(PDF 실패 또는 미생성)")
    print("warnings:", result.get("warnings"))
    print("\n--- final_report 앞 1500자 ---\n")
    print((result.get("final_report") or "")[:1500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
