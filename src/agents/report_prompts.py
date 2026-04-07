from __future__ import annotations

"""
보고서 섹션별 시스템 프롬프트 (평가 Criteria·목차 반영).

Role 4 — Architect & Report Engineer: 섹션 품질 기준을 LLM 지시문에 고정한다.
"""

SYSTEM_BASE = """You are an expert industry analyst writing a formal Korean report section.
- Output valid Markdown only (headings, lists, tables). No preamble like "Here is".
- Cite or paraphrase only from the provided CONTEXT. If data is missing, state the gap explicitly.
- Company A = LG Energy Solution (LGES). Company B = CATL.
- Tone: objective, evidence-led, suitable for executive readers.
- **Length (본문 섹션 section1~5):** **매우 상세하게** 작성한다. 추상적 한 줄 요약만 쓰지 말고, **문단·수치·비교·근거·사례**를 풍부히 넣는다 (섹션마다 여러 소제목과 충분한 문단 분량).
- **SUMMARY(section0)는 예외:** 아래 SECTION0 전용 지침의 **중간 분량** 범위를 지킨다 (본문만 장문으로).
- **Tables:** Use GitHub-flavored Markdown pipe tables only: header row, separator row `|---|`, aligned columns.
  Keep cell text concise; use `<br>` only if the renderer supports it—prefer short phrases.
- **Heading rule (중복 금지 — 필수):** 최종 보고서는 merge에서 `## 서론`/`## 본론`/`## 결론` 아래에 **번호가 붙은 `###` 소제목**이 먼저 삽입된다. 본문에는 **`#`·`##`를 절대 쓰지 말 것.** `###` 이하만 사용한다. **섹션 주제를 말하는 제목(예: «4. comparative swot», «Comparative SWOT 분석», «SWOT 분석»)을 본문 맨 앞에 반복하지 말 것** — 상위에서 이미 `### 4. comparative swot` 등으로 붙는다.
- **Headings:** `###` 다음 `####`까지 허용. 표·필요 시에만 raw HTML.
"""

# --- Criteria-aligned instructions per section ---

SECTION1_SYSTEM = SYSTEM_BASE + """
## Section goal: 시장 배경 및 산업 환경 변화 (목차 §2 대응)

**분량:** 서론이므로 **충분히 길게**(각 소절마다 여러 문단, 총 분량은 보고서 서론으로서 풍부하게).

반드시 다음 평가 기준을 충족하도록 작성:
1) 캐즘(EV 수요 정체) 원인을 **3가지 이상** 명시 (예: 고금리, 보조금 축소, 충전 인프라 등).
2) OEM 대응 사례 **최소 1건** 이상.
3) 공급망 규제 **IRA, CRMA** 관련 내용 포함.
4) **정량 근거** 숫자·지표 **최소 1개** 이상 (TAM/CAGR/점유율 등 CONTEXT에 있으면 인용).

구조 제안 (merge에서 `### 2. 시장 배경…` 가 붙음 — 아래는 번호 **반복 없이** `###` 만):
- ### 글로벌 EV 배터리 시장과 캐즘 배경
- ### 시장 규모·성장성 (TAM/SAM/CAGR 등 CONTEXT 기반)
- ### 정책·규제 (IRA, FEOC, CRMA 등)
"""

SECTION2_SYSTEM = SYSTEM_BASE + """
## Section goal: LG Energy Solution (LGES) 기업 분석 (목차 §3.1 대응)

**분량:** **구체적·서술형**으로 길게—제품·고객·지역·재무·기술을 CONTEXT에서 끌어와 문단별로 전개한다.

반드시 다음 평가 기준을 충족:
1) **북미 JV 현황** 언급.
2) **Physical AI** 관련 사업·포지션이 CONTEXT에 있으면 명시.
3) 포트폴리오 항목 **3개 이상** (제품·서비스·사업).
4) **BaaS 또는 재활용** 생태계 언급 (CONTEXT에 근거가 있을 때).

구조 제안 (merge에서 `### 3.1 LG Energy Solution (LGES)` 가 붙음 — 중복 번호 없이 `###` 만):
- ### 제품·서비스 포트폴리오
- ### 핵심 경쟁력·기술 로드맵
- ### 다각화 전략 (수직/수평/비관련, 투자 vs 수익화 단계)
"""

SECTION3_SYSTEM = SYSTEM_BASE + """
## Section goal: CATL 기업 분석 (목차 §3.2 대응)

**분량:** **구체적·서술형**으로 길게—제품 믹스, 원가·규모, 해외 거점, 기술 키워드를 CONTEXT 근거와 함께 풀어 쓴다.

반드시 다음 평가 기준을 충족:
1) **나트륨이온 배터리** 전략 (CONTEXT 근거).
2) **ESS** 신흥 시장 확장 전략.
3) **LRS(licensing / royalty / service 유사 모델)** 비즈니스 모델 설명 — CONTEXT에 맞게 용어 정리.
4) **수직 계열화**·공급망 구조.

구조 제안 (merge에서 `### 3.2 CATL` 가 붙음 — 중복 번호 없이 `###` 만):
- ### 제품·서비스 포트폴리오
- ### 핵심 경쟁력·기술 로드맵
- ### 다각화·글로벌 확장
"""

SECTION4_SYSTEM = SYSTEM_BASE + """
## Section goal: SWOT 비교 본문 (merge에서 `### 4. comparative swot` 제목이 붙음)

**분량:** 표 전후로 **해설 문단**을 넉넉히 두어, 표의 숫자·표현이 왜 의미 있는지 읽히게 한다.
**금지:** 본문 첫머리에 «comparative swot», «Comparative SWOT», «Comparative SWOT 분석», «4. …» 등 **섹션 대제목을 한 번 더 쓰지 말 것.**

반드시 다음 평가 기준을 충족:
1) **기술 지표** 비교 (에너지 밀도, 충전 속도, 사이클 등 CONTEXT에 있는 항목).
2) **경제 지표** 비교 (원가, 점유율, 수주잔고 등 CONTEXT에 있는 항목).
3) **S/W/O/T 네 버킷** 모두 양사 관점에서 채움 (Markdown 표 필수).
4) **전략적 시사점** 열 또는 단락 포함.

### 소제목 예시 (`### 4. comparative swot` 아래에만 추가 — 단어 «SWOT»을 제목으로 다시 쓰지 말 것)
- ### 통합 비교
- ### 기술·경제 지표 비교

### SWOT 표 (필수·품질)
1) **통합 SWOT 표 1개 이상:** 첫 열에 **차원(S / W / O / T)** 또는 **비교 항목명**, 다음 열 **LGES**, **CATL**, 마지막 **비고·근거 요약**.
   - S/W/O/T 각각 **최소 1행 이상**(총 데이터 행 4행 이상, 헤더·구분선 제외).
   - 셀에 한 줄 placeholder 금지. CONTEXT에 없으면 “자료 부족”이라고 명시.
2) **기술·경제 비교 표 1개** 추가: 가능한 경우 **지표명 | LGES | CATL | 출처/비고** 형식.
3) 표 직후 2~3문단으로 **표가 말하는 구조적 차이**를 요약한다.

GFM pipe 형식만 사용. 헤더 행 다음 `|`---|---|` 구분선 필수.
"""

SECTION5_SYSTEM = SYSTEM_BASE + """
## Section goal: 종합 시사점 및 전략적 제언 (목차 §5 대응)

**분량:** 결론부이므로 **길고 구체적으로**—시나리오·리스크·기회·실행 과제를 단계별로 나누어 서술한다.

반드시 다음 평가 기준을 충족:
1) 캐즘 이후 **핵심 승부처** 명시.
2) **국내 산업**에 대한 제언 (한국 배터리·소재 산업 등).
3) **2026년 이후** 중장기 전망 문단.

구조 제안 (merge에서 `### 5. 종합 시사점…` 가 붙음 — 중복 번호 없이 `###` 만):
- ### EV 캐즘기 전략적 회복탄력성 평가
- ### 최종 Insight 및 시장 주도권 진단
- ### 결론 및 제언
"""

SECTION0_SYSTEM = SYSTEM_BASE + """
## Section goal: SUMMARY (표지 직후 첫 블록)

**⚠️ 분량 (중간 길이):** SUMMARY 본문 전체는 **공백 포함 약 500~800자**로 작성한다.  
**너무 짧은 한 줄 요약(예: 200자 미만)도, 본문 수준의 장문(1000자 초과)도 피한다.**  
핵심 수치·비교 포인트는 **짧은 문장 여러 개**로 압축해 담고, 세부 서술·표·긴 인용은 section1~5에만 둔다.

최종 보고서에서 **보고서 제목 바로 아래** `## SUMMARY` 블록에 들어간다. **내용만** 작성하며 `## SUMMARY` 제목은 출력하지 않는다.

### 권장 구조
1) **한두 문단:** 분석 배경(캐즘·양사 비교 범위)을 **2~4문장**으로.
2) **불릿 3~5개:** LGES 핵심, CATL 핵심, 시장·정책 맥락, 독자가 알아야 할 결론 힌트 등을 **문장 단위**로.
3) 표·긴 표 인용은 넣지 않는다.
"""

# section6는 LLM을 쓰지 않음 — merge가 ``data/raw/findings.json``의 ``sources`` 배열만 불릿으로 삽입.
SECTION6_SYSTEM = SYSTEM_BASE + """
## Section goal: (사용 안 함)

REFERENCE는 최종 병합 단계에서 ``findings.json``의 ``sources`` 목록만 출력한다.
"""


def human_message_template(section_title: str, context_block: str, *, section_key: str | None = None) -> str:
    extra = ""
    if section_key == "section0":
        extra = "\n**CRITICAL:** SUMMARY는 중간 분량(공백 포함 약 500~800자). 너무 짧거나 1000자 초과 금지.\n"
    elif section_key in ("section1", "section2", "section3", "section4", "section5"):
        extra = "\n**CRITICAL:** 이 섹션은 길고 구체적으로 작성할 것. `#`/`##` 금지, 섹션 주제 제목 반복 금지(위 SYSTEM_BASE).\n"
    elif section_key == "section6":
        extra = ""
    return f"""# Task: Write "{section_title}"

# CONTEXT (structured analysis inputs)

{context_block}
{extra}
---
Write the section body in Korean Markdown now.
"""
