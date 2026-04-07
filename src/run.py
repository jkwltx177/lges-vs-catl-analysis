"""전체 Research Agent 실행 스크립트.

실행:
    python -m src.run
"""

from dotenv import load_dotenv

load_dotenv()

from src.agents.research_graph import graph  # noqa: E402

INITIAL_STATE = {
    "goal": "전기차 캐즘 시기 LGES와 CATL의 회복탄력성 및 SWOT 비교 분석",
    "target_companies": ["LGES", "CATL"],
    "report_topic": "2024 배터리 시장 전략 보고서",
    "max_retry": 2,
}

CONFIG = {"configurable": {"thread_id": "res_001"}}


# ----------------------------------------------------------------
# 노드별 수치 요약 출력
# ----------------------------------------------------------------

# def _print_metrics(node_name: str, output: dict) -> None:
#     """노드 출력에서 주요 수치를 추출해 출력."""

#     if node_name == "vectordb_retrieval":
#         docs = output.get("raw_documents", [])
#         vdb_docs = [d for d in docs if d.get("source_type") == "vector_db"]
#         distances = [d["distance"] for d in vdb_docs if d.get("distance") is not None]
#         print(f"  검색 결과: {len(vdb_docs)}개 청크")
#         if distances:
#             print(f"  유사도 거리  min={min(distances):.4f}  max={max(distances):.4f}  avg={sum(distances)/len(distances):.4f}")
#         for d in vdb_docs:
#             meta = d.get("metadata", {})
#             print(f"  [{meta.get('company','?')} / {meta.get('chunk_type','?')}] q={d.get('query','')[:40]}")
#             print(f"    {d.get('content','')[:120].strip()}")

#     elif node_name == "web_retrieval":
#         docs = output.get("raw_documents", [])
#         web_docs = [d for d in docs if d.get("source_type") == "web_search"]
#         print(f"  검색 결과: {len(web_docs)}개 웹 문서")
#         for d in web_docs:
#             print(f"  [{d.get('published_date','?')}] {d.get('title','')[:60]}")
#             print(f"    {d.get('url','')}")
#             print(f"    {d.get('content','')[:120].strip()}")

#     elif node_name == "merge_results":
#         grouped = output.get("grouped_documents", {})
#         token_usage = output.get("token_usage", {})
#         coverage = output.get("query_coverage", {})
#         counts = [len(v) for v in grouped.values()]
#         if counts:
#             print(f"  쿼리 수: {len(grouped)}  총 문서: {sum(counts)}  쿼리당 평균: {sum(counts)/len(counts):.1f}")
#         else:
#             print("  문서 없음")
#         if coverage:
#             gap_count = sum(
#                 1 for v in coverage.values()
#                 if v.get("avg_distance") is None or v.get("avg_distance", 1) >= 0.65
#             )
#             print(f"  갭 쿼리: {gap_count}개 / 전체 {len(coverage)}개")
#         if token_usage:
#             print(f"  토큰 사용: {token_usage}")

#     elif node_name == "validate_evidence":
#         validated = output.get("validated_evidence", [])
#         rejected = output.get("rejected_evidence", [])
#         total = len(validated) + len(rejected)
#         rate = len(validated) / total * 100 if total else 0
#         print(f"  통과: {len(validated)}개  탈락: {len(rejected)}개  통과율: {rate:.1f}%")

#     elif node_name == "coverage_check":
#         status = output.get("coverage_status", "-")
#         missing = output.get("missing_topics", [])
#         retry = output.get("retry_count", "-")
#         print(f"  coverage: {status}  retry_count: {retry}")
#         if missing:
#             print(f"  누락 주제: {missing}")

#     elif node_name == "build_output":
#         print(f"  validated_evidence: {len(output.get('validated_evidence_ids', []))}개 ID 생성")
#         print(f"  key_findings: {len(output.get('key_findings', []))}개")
#         gaps = output.get("unresolved_gaps", [])
#         if gaps:
#             print(f"  미해결 과제: {gaps}")


# ----------------------------------------------------------------
# 메인
# ----------------------------------------------------------------

def main():
    print("=" * 60)
    print("[run] Research Agent 가동")
    print(f"      목표: {INITIAL_STATE['goal']}")
    print("=" * 60)

    for event in graph.stream(INITIAL_STATE, config=CONFIG):
        for node_name, output in event.items():
            print(f"\n▶ [{node_name}] 완료")
            if not isinstance(output, dict):
                for item in (output if isinstance(output, tuple) else (output,)):
                    msg = getattr(item, "value", item)
                    print(f"  {msg}")
                continue
            # _print_metrics(node_name, output)

            warnings = output.get("warnings") or []
            for w in warnings:
                print(f"  ⚠ {w}")

    print("\n" + "=" * 60)
    print("[run] 전체 완료")
    print("=" * 60)


if __name__ == "__main__":
    main()
