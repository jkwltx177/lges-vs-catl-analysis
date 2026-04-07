# Task 2: 자료 정리 (Data Processing) 구현 명세서

## 개요
이 문서는 Task 2(자료 정리) 파이프라인의 설계 및 구현 내용을 상세히 설명합니다. 이 파이프라인은 Task 1(자료 조사)에서 수집된 방대한 날것의 데이터(`raw_findings`)를 분석 AI(Task 3)가 이해하기 쉬운 구조화된 데이터로 가공하는 역할을 담당합니다.

특히, 데이터 정제 과정에서 발생할 수 있는 **"과도한 정보 압축(Over-compression)"**과 **"출처(Source) 유실"**을 방지하기 위한 **Safe Output** 전략이 철저하게 반영되었습니다.

---

## 1. 파이프라인 흐름 및 State I/O
Task 2는 `DataRefineGraphState`를 기반으로 동작하며, 총 4개의 핵심 노드로 구성됩니다.

*   **입력 (Input):** Task 1 (조사 에이전트 그룹, `Coverage Check` 노드) → `bridge_node_1`을 거쳐 전달된 `DataRefineGraphState`
    *   **핵심 입력 State:** `raw_findings` (최소 800자 이상의 원문 데이터 리스트)
*   **출력 (Output):** 가공된 상태 정보를 Task 3 (분석 에이전트 그룹, `Parallel SWOT` 노드 등)으로 전달 (`bridge_node_2`를 통해 `AnalysisGraphState`로 주입)
    *   **핵심 출력 State:** `company_a_cleaned`, `company_b_cleaned`, `market_context`, `company_a_portfolio`, `company_b_portfolio`, `company_a_swot`, `company_b_swot`
*   **중요 원칙:** Task 2의 모든 노드는 기존의 `raw_findings`를 절대 수정하거나 삭제하지 않습니다. 정제된 데이터를 새로운 State 키에 **추가(Update)**만 수행하여, 최종 보고서 작성(Task 4) 시 원문 팩트 교차 검증이 가능하도록 완벽히 보존합니다.

---

## 2. 노드별 상세 명세

### 2.1. `clean_node` (데이터 정제 노드)
*   **역할:** `raw_findings`에서 중복된 내용을 병합하고, 명확한 문장 형태의 핵심 사실(Fact) 리스트로 변환합니다.
*   **사용 에이전트/프롬프트:** `clean_agent.py` (`create_clean_prompt`)
*   **입력 State:** `raw_findings` (from Task 1)
*   **출력 State:** `company_a_cleaned`, `company_b_cleaned` → (to `market_node`, `portfolio_node`, `swot_map_node`)
*   **Safe Output 전략:**
    *   단일 문장 요약으로 인한 디테일 유실을 막기 위해 **"2~3문장 분량의 명확한 맥락으로 정리할 것"**, **"수치, 날짜, 고유명사 절대 생략 금지"**를 프롬프트에 강제했습니다.
    *   State 구조(`RawItem`)에 `source` 필드를 전격 추가하여, 정제 후에도 해당 팩트가 어떤 에이전트/URL에서 왔는지 출처를 보존합니다.

### 2.2. `market_node` (시장 정보 추출 노드)
*   **역할:** 정제된 팩트 리스트에서 시장 및 산업 관련 내용(TAM, CAGR, 정책, 트렌드 등)을 추출하여 구조화된 JSON 객체로 매핑합니다.
*   **사용 에이전트/프롬프트:** `market_portfolio_agent.py` (`create_market_portfolio_prompt`)
*   **입력 State:** `company_a_cleaned`, `company_b_cleaned` (from `clean_node`)
*   **출력 State:** `market_context` → (to Task 3, `context_integration_node` / Task 4, `section1_node`)
*   **설계 반영 사항:** `design.md`의 Criteria를 충족하기 위해, 프롬프트에 명시적으로 캐즘 원인(고금리, 보조금 축소 등), OEM 대응 사례, IRA/CRMA 규제 내용 등을 필수 추출 항목으로 하드코딩하여 누락을 원천 차단했습니다.

### 2.3. `portfolio_node` (포트폴리오 추출 노드)
*   **역할:** 각 기업의 핵심 서비스, 제품, 신사업 전략을 추출하여 기업별 포트폴리오 객체로 구조화합니다.
*   **사용 에이전트/프롬프트:** `market_portfolio_agent.py` (`create_market_portfolio_prompt`)
*   **입력 State:** `company_a_cleaned`, `company_b_cleaned` (from `clean_node`)
*   **출력 State:** `company_a_portfolio`, `company_b_portfolio` → (to Task 3, `resilience_evaluation_node` / Task 4)
*   **설계 반영 사항:** LGES의 북미 JV, Physical AI, BaaS, CATL의 나트륨이온, ESS 전략, LRS 모델 등 `design.md`의 핵심 체크 항목이 누락되지 않도록 프롬프트에 직접 타겟팅했습니다.

### 2.4. `swot_map_node` (SWOT 팩트 매핑 노드)
*   **역할:** 정제된 팩트들을 해석이나 분석 없이, 순수하게 S, W, O, T 4개의 버킷으로 자동 분류(Routing)합니다.
*   **사용 에이전트/프롬프트:** `swot_classifier_agent.py` (`create_swot_classifier_prompt`)
*   **입력 State:** `company_a_cleaned`, `company_b_cleaned` (from `clean_node`)
*   **출력 State:** `company_a_swot`, `company_b_swot` → (to Task 3, `S/W/O/T Analysis nodes`)
*   **Safe Output & 설계 원칙:**
    *   **"절대 데이터를 해석하거나 새로운 의미를 부여하지 마십시오"**라는 강력한 제약을 걸어, Task 3의 분석 AI가 온전히 추론을 담당할 수 있도록 역할을 명확히 분리했습니다.
    *   팩트 매핑 시 `source` 필드를 무조건 복사(Copy)해 오도록 강제하여, Task 3과 Task 4에서 레퍼런스 유실 없이 근거 기반의 보고서 작성이 가능하도록 안전장치를 마련했습니다.

---

## 3. 요약 및 다음 단계 (To Team)
*   **👤 Role 1 (Task 1):** 외부 데이터를 수집하여 `raw_findings`에 충분히 쌓아 주시기만 하면 됩니다. 이후 정제 로직은 Task 2가 안전하게 처리합니다.
*   **👤 Role 3 (Task 3):** `clean_node`를 거쳐 S/W/O/T로 예쁘게 분류된 `company_a_swot`, `company_b_swot` 데이터를 바로 꺼내어 4개의 병렬 분석 에이전트 프롬프트에 주입하시면 됩니다. 팩트만 잘 분류되어 있으니 심층 비교 로직에만 집중하실 수 있습니다.
*   **👤 Role 4 (Task 4):** 보고서 작성 시, 분석된 결과뿐만 아니라 Task 1부터 훼손 없이 살아남은 `raw_findings` 원문과 Task 2에서 보존한 `source` 태그를 활용해 강력한 팩트 교차 검증과 정확한 레퍼런스(Reference) 섹션 자동 생성을 구현하실 수 있습니다.
