"""Section writers — section1~3는 병렬(스레드)로 실행 가능한 단일 노드에서 호출."""

from __future__ import annotations

import concurrent.futures
import re
from typing import Dict, Tuple

from langchain_core.messages import HumanMessage, SystemMessage

from src.agents import report_prompts as P
from src.core.llm import get_chat_model
from src.nodes.report.context import build_report_context
from src.state.state import ReportGraphState

def _sanitize_for_chat_api(text: str, *, max_chars: int = 100_000) -> str:
    """OpenAI 요청 JSON 직렬화 실패(400 invalid JSON body) 방지: 제어 문자 제거·길이 상한."""
    if not isinstance(text, str):
        text = str(text)
    text = text.encode("utf-8", errors="replace").decode("utf-8")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    if len(text) > max_chars:
        text = (
            text[:max_chars]
            + "\n\n[CONTEXT가 길어 일부만 전송했습니다. raw_findings는 merge/레퍼런스 단계에서 활용됩니다.]"
        )
    return text


_SECTION_SPECS: Dict[str, Tuple[str, str, str]] = {
    "section1": (P.SECTION1_SYSTEM, "section1", "2. 시장 배경 및 산업 환경 변화"),
    "section2": (P.SECTION2_SYSTEM, "section2", "3.1 LG Energy Solution (LGES) 분석"),
    "section3": (P.SECTION3_SYSTEM, "section3", "3.2 CATL 분석"),
    "section4": (P.SECTION4_SYSTEM, "section4", "4. Comparative SWOT 분석"),
    "section5": (P.SECTION5_SYSTEM, "section5", "5. 종합 시사점 및 전략적 제언"),
    "section0": (P.SECTION0_SYSTEM, "section0", "1. SUMMARY"),
    "section6": (P.SECTION6_SYSTEM, "section6", "6. REFERENCE"),
}


def _invoke_section(state: ReportGraphState, section_key: str) -> str:
    system, mode, title = _SECTION_SPECS[section_key]
    ctx = build_report_context(state, mode=mode)
    human = P.human_message_template(title, ctx)
    system = _sanitize_for_chat_api(system, max_chars=50_000)
    human = _sanitize_for_chat_api(human, max_chars=120_000)
    llm = get_chat_model()
    msg = llm.invoke([SystemMessage(content=system), HumanMessage(content=human)])
    return getattr(msg, "content", str(msg))


def section1_node(state: ReportGraphState) -> dict:
    return {"sections": {"section1": _invoke_section(state, "section1")}}


def section2_node(state: ReportGraphState) -> dict:
    return {"sections": {"section2": _invoke_section(state, "section2")}}


def section3_node(state: ReportGraphState) -> dict:
    return {"sections": {"section3": _invoke_section(state, "section3")}}


def sections_parallel_123_node(state: ReportGraphState) -> dict:
    """Task.4: section1·2·3 병렬 생성 후 `sections`에 키 단위 병합."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        f1 = pool.submit(_invoke_section, state, "section1")
        f2 = pool.submit(_invoke_section, state, "section2")
        f3 = pool.submit(_invoke_section, state, "section3")
        s1 = f1.result()
        s2 = f2.result()
        s3 = f3.result()
    return {"sections": {"section1": s1, "section2": s2, "section3": s3}}


def section4_node(state: ReportGraphState) -> dict:
    return {"sections": {"section4": _invoke_section(state, "section4")}}


def section5_node(state: ReportGraphState) -> dict:
    return {"sections": {"section5": _invoke_section(state, "section5")}}


def section0_node(state: ReportGraphState) -> dict:
    """SUMMARY — section4·5 및 병렬 본문이 `sections`에 있어야 품질이 나온다."""
    return {"sections": {"section0": _invoke_section(state, "section0")}}


def section6_node(state: ReportGraphState) -> dict:
    return {"sections": {"section6": _invoke_section(state, "section6")}}
