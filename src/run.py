"""전체 Research Agent 실행 스크립트.

실행:
    python -m src.run
"""

from dotenv import load_dotenv

load_dotenv()

from src.agents.research_graph import graph as research_graph  # noqa: E402
from src.agents.data_refine_graph import graph as refine_graph  # noqa: E402

INITIAL_STATE = {
    "goal": "전기차 캐즘 시기 LGES와 CATL의 회복탄력성 및 SWOT 비교 분석",
    "target_companies": ["LGES", "CATL"],
    "report_topic": "2024 배터리 시장 전략 보고서",
    "max_retry": 2,
}

CONFIG = {"configurable": {"thread_id": "res_001"}}

def main():
    print("=" * 60)
    print("[run] Research Agent 가동 (Task 1)")
    print(f"      목표: {INITIAL_STATE['goal']}")
    print("=" * 60)

    final_research_state = None
    for event in research_graph.stream(INITIAL_STATE, config=CONFIG):
        for node_name, output in event.items():
            print(f"\n▶ [Task 1: {node_name}] 완료")
            final_research_state = output

    if final_research_state is None:
        print("Research Graph execution failed.")
        return

    print("\n" + "=" * 60)
    print("[run] Data Refine Agent 가동 (Task 2)")
    print("=" * 60)

    # deliver 노드에서 나온 출력으로 판단되나, interrupt가 걸렸으므로 상태를 get_state()로 확실히 가져옵니다.
    current_state = research_graph.get_state(CONFIG).values
    
    # Task 1의 결과물 추출 (bridge_node_1 역할)
    refine_input = {
        "company_a": current_state.get("company_a", {}),
        "company_b": current_state.get("company_b", {}),
        "raw_findings": current_state.get("raw_findings", [])
    }

    import json
    for event in refine_graph.stream(refine_input, config={"configurable": {"thread_id": "refine_001"}}):
        for node_name, output in event.items():
            print(f"\n▶ [Task 2: {node_name}] 완료")
            # 내용물 확인을 위한 출력 추가
            print(json.dumps(output, indent=2, ensure_ascii=False))

    print("\n" + "=" * 60)
    print("[run] 전체 워크플로우 (Task 1 -> Task 2) 테스트 완료")
    print("=" * 60)


if __name__ == "__main__":
    main()
