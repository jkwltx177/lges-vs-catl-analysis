"""전체 Research -> Refine -> Analysis 실행 스크립트.

실행:
    python -m src.run
"""

from dotenv import load_dotenv

load_dotenv()

from src.agents.full_pipeline_graph import run_research_refine_analysis  # noqa: E402

INITIAL_STATE = {
    "goal": "전기차 캐즘 시기 LGES와 CATL의 회복탄력성 및 SWOT 비교 분석",
    "target_companies": ["LGES", "CATL"],
    "report_topic": "2024 배터리 시장 전략 보고서",
    "max_retry": 2,
}

CONFIG = {"configurable": {"thread_id": "res_001"}}

def main():
    print("=" * 60)
    print("[run] Research -> Refine -> Analysis 파이프라인 가동")
    print(f"      목표: {INITIAL_STATE['goal']}")
    print("=" * 60)

    final_state = run_research_refine_analysis(INITIAL_STATE, thread_prefix="run")

    print("\n" + "=" * 60)
    print("[run] 최종 Analysis 결과 요약")
    print("=" * 60)
    print("최종 키:", sorted(final_state.keys()))
    print("final_insight keys:", sorted(final_state.get("final_insight", {}).keys()))
    print("comparative_swot 존재:", "comparative_swot" in final_state)


if __name__ == "__main__":
    main()
