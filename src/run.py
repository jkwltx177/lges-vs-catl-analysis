"""전체 파이프라인 실행 스크립트.

실행:
    # Research → Refine → Analysis 만
    python -m src.run

    # 위 + 보고서(섹션 생성·merge·MD/PDF)
    python -m src.run --report
"""

from __future__ import annotations

import argparse

from dotenv import load_dotenv

load_dotenv()

from src.agents.full_pipeline_graph import (  # noqa: E402
    run_full_pipeline_with_report,
    run_research_refine_analysis,
)

INITIAL_STATE = {
    "goal": "전기차 캐즘 시기 LGES와 CATL의 회복탄력성 및 SWOT 비교 분석",
    "target_companies": ["LGES", "CATL"],
    "report_topic": "2024 배터리 시장 전략 보고서",
    "max_retry": 2,
}

CONFIG = {"configurable": {"thread_id": "res_001"}}


def main() -> None:
    parser = argparse.ArgumentParser(description="LGES vs CATL LangGraph 파이프라인")
    parser.add_argument(
        "--report",
        action="store_true",
        help="분석 이후 보고서 생성(섹션 LLM·merge·report/final MD·PDF)까지 실행",
    )
    args = parser.parse_args()

    print("=" * 60)
    if args.report:
        print("[run] Research -> Refine -> Analysis -> Report")
    else:
        print("[run] Research -> Refine -> Analysis")
    print(f"      목표: {INITIAL_STATE['goal']}")
    print("=" * 60)

    if args.report:
        final_state = run_full_pipeline_with_report(INITIAL_STATE, thread_prefix="run")
        print("\n" + "=" * 60)
        print("[run] 최종 Report 결과")
        print("=" * 60)
        print("final_report_md_path:", final_state.get("final_report_md_path"))
        print("final_report_pdf_path:", final_state.get("final_report_pdf_path") or "(없음 또는 PDF 실패)")
        print("warnings:", final_state.get("warnings"))
        fr = final_state.get("final_report") or ""
        print("\n--- final_report 앞 800자 ---\n")
        print(fr[:800])
        return

    final_state = run_research_refine_analysis(INITIAL_STATE, thread_prefix="run")

    print("\n" + "=" * 60)
    print("[run] 최종 Analysis 결과 요약")
    print("=" * 60)
    print("최종 키:", sorted(final_state.keys()))
    print("final_insight keys:", sorted((final_state.get("final_insight") or {}).keys()))
    print("comparative_swot 존재:", "comparative_swot" in final_state)


if __name__ == "__main__":
    main()
