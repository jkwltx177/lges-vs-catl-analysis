"""전체 파이프라인 실행 스크립트.

프로젝트 루트에서 실행:

    .venv/bin/python -m src.run
    .venv/bin/python -m src.run --report
    .venv/bin/python -m src.run --report -v

필수: `.env`에 `OPENAI_API_KEY` (Research·Refine·Analysis·Report LLM 호출)
선택: `TAVILY_API_KEY` 등은 조사 노드(웹 검색)에서 사용 — 없으면 해당 경로에서 오류 날 수 있음
Task.1 Human Review interrupt: 기본 `SKIP_RESEARCH_HUMAN_REVIEW=1`(자동 통과). 대화형 검토는 `=0`.
`-v` 로 단계별 필수 State 키 점검 로그 출력.
"""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from typing import Any, Dict, cast

# 프로젝트 루트를 모듈 경로에 (IDE/일부 환경에서 `python -m src.run` 보조)
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import src.core.env  # noqa: E402 — 프로젝트 루트 `.env` 선로드
from src.agents.full_pipeline_graph import (  # noqa: E402
    check_openai_config,
    run_full_pipeline_with_report,
    run_research_refine_analysis,
)
from src.state.state import ResearchGraphState

INITIAL_STATE: Dict[str, Any] = {
    "goal": "전기차 캐즘 시기 LGES와 CATL의 회복탄력성 및 SWOT 비교 분석",
    "target_companies": ["LGES", "CATL"],
    "report_topic": "2026 배터리 시장 전략 보고서",
    "max_retry": 2,
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="LGES vs CATL — Research → Refine → Analysis [→ Report]",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="분석 이후 보고서 생성(섹션 LLM·merge·report/final MD·PDF)까지 실행",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="단계별 진행 로그 출력",
    )
    args = parser.parse_args()

    ok, msg = check_openai_config()
    if not ok:
        print(msg, file=sys.stderr)
        return 1

    print("=" * 60)
    if args.report:
        print("[run] Research -> Refine -> Analysis -> Report")
    else:
        print("[run] Research -> Refine -> Analysis")
    print(f"      목표: {INITIAL_STATE['goal']}")
    print("=" * 60)

    try:
        if args.report:
            final_state = run_full_pipeline_with_report(
                cast(ResearchGraphState, INITIAL_STATE), thread_prefix="run", verbose=args.verbose
            )
            print("\n" + "=" * 60)
            print("[run] 최종 Report 결과")
            print("=" * 60)
            print("final_report_md_path:", final_state.get("final_report_md_path"))
            print(
                "final_report_pdf_path:",
                final_state.get("final_report_pdf_path") or "(없음 또는 PDF 실패)",
            )
            print("final_report_docs_md_path:", final_state.get("final_report_docs_md_path"))
            print(
                "final_report_docs_pdf_path:",
                final_state.get("final_report_docs_pdf_path") or "(없음 또는 PDF 실패)",
            )
            print(
                "report_file_path (PDF 우선, 실패 시 MD):",
                final_state.get("report_file_path") or "",
            )
            print("warnings:", final_state.get("warnings"))
            fr = final_state.get("final_report") or ""
            print("\n--- final_report 앞 800자 ---\n")
            print(fr[:800])
            return 0

        final_state = run_research_refine_analysis(
            cast(ResearchGraphState, INITIAL_STATE), thread_prefix="run", verbose=args.verbose
        )

        print("\n" + "=" * 60)
        print("[run] 최종 Analysis 결과 요약")
        print("=" * 60)
        print("최종 키:", sorted(final_state.keys()))
        fi = final_state.get("final_insight") or {}
        print("final_insight keys:", sorted(fi.keys()) if isinstance(fi, dict) else fi)
        print("comparative_swot 존재:", "comparative_swot" in final_state)
        return 0

    except Exception as e:
        print("\n[run] 오류 발생:", repr(e), file=sys.stderr)
        traceback.print_exc()
        return 1

    # import json
    # print("\n[comparative_swot 결과]")
    # print(json.dumps(final_state.get("comparative_swot", {}), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    raise SystemExit(main())
