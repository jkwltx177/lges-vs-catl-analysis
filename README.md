# EV Battery Strategy Analysis: LGES vs CATL

본 프로젝트는 전기차 시장 정체기(캐즘) 상황에서 **LG Energy Solution (LGES)**과 **CATL**의 전략적 회복탄력성 및 포트폴리오 다각화 전략을 비교 분석하여 객관적 근거를 바탕으로 SWOT 분석과 시사점을 도출하는 AI Agent 기반의 분석 프로젝트입니다.

---

## 📂 디렉토리 구조 및 설명

이 디렉토리는 AI Agent Workflow 설계 산출물(Task 1~4 및 State 설계)을 완벽히 반영하여 팀원들이 직관적으로 파악하고 효율적으로 협업할 수 있도록 구성되었습니다. 
모든 빈 폴더에는 `.gitkeep` 파일이 포함되어 있어 즉시 GitHub에 커밋할 수 있습니다.

```text
lges-vs-catl-analysis/
├── data/                    # 데이터 저장소
│   ├── raw/                 # 수집된 원본 데이터 (IR 자료, 웹 검색 결과, 산업 보고서 등)
│   ├── processed/           # 노드를 거쳐 정제된 중간 데이터 (SWOT 매핑, 요약 데이터 등)
│   └── vectordb/            # BGE-M3 임베딩이 저장되는 로컬 VectorDB 공간
├── src/                     # AI Agent 및 Workflow 소스 코드
│   ├── state/               # GraphState 정의 (Sub-State 및 통합 GraphState의 TypedDict 등)
│   ├── agents/              # 각 역할별 LLM 에이전트 프롬프트 및 시스템 지시문
│   ├── nodes/               # Graph Workflow의 각 노드 함수 (조사, 정제, 분석, 작성 노드)
│   ├── tools/               # 웹 검색, VectorDB 검색 등 에이전트 도구 (BGE-M3 기반 Retrieval 등)
│   └── core/                # 환경 설정 및 초기화 (LLM 설정, VectorDB 초기화 등)
├── notebooks/               # 실험 및 테스트용 Jupyter Notebooks (.ipynb)
├── report/                  # 최종 및 중간 산출물(보고서)
│   ├── sections/            # 각 에이전트가 병렬로 생성한 섹션별 초안 (섹션 1~6)
│   └── final/               # 병합된 최종 결과물 (PDF, MD, 최종 보고서)
├── docs/                    # 설계 산출물 및 프로젝트 기획 문서 보관
└── tests/                   # 노드, 에이전트 로직, State 변경 등을 검증하는 테스트 코드
```

---

## 🚀 에이전트 워크플로우 매핑 가이드

본 프로젝트는 4단계의 주요 Task로 나뉘어 동작하며, 소스 코드 및 디렉토리 매핑은 다음과 같습니다.

### **Task.1 자료 조사 (Research)**
- **경로:** `src/nodes/`, `src/tools/`
- **역할:** BGE-M3 임베딩 모델을 활용한 VectorDB 검색 및 병렬 Web 검색 (`Query Generation` → `VectorDB/Web Retrieval` → `Coverage Check`)
- **데이터 흐름:** `data/raw/` 및 `data/vectordb/` 활용

### **Task.2 자료 정리 (Refinement)**
- **경로:** `src/nodes/`, `src/agents/`
- **역할:** 조사 에이전트가 수집한 데이터를 S/W/O/T 카테고리로 매핑하고, 기업 포트폴리오 및 시장 컨텍스트로 정제 (`clean_node`, `swot_map_node`)
- **데이터 흐름:** 정제된 데이터를 `data/processed/`에 저장

### **Task.3 자료 분석 (Analysis)**
- **경로:** `src/nodes/`, `src/agents/`
- **역할:** S/W/O/T 별 병렬 분석, EV 캐즘기 전략적 회복탄력성 평가 및 핵심 시사점(Insight) 도출 (`resilience_evaluation_node`, `insight_node`)

### **Task.4 보고서 작성 (Report)**
- **경로:** `report/sections/`, `report/final/`
- **역할:** 분석된 결과를 기반으로 섹션 0~6까지의 보고서를 병렬로 작성하고, 최종적으로 `report/final/`에 하나의 결과물로 병합(`merge_node`)

---

## 📝 State 설계 연동 규칙

`src/state/` 디렉토리에는 시스템 전반의 상태를 관리하는 `GraphState`가 정의되어야 합니다.
설계 문서에 따라 모든 원문 데이터(raw_findings)는 누락 없이 보존되어야 하며, 파이프라인 전반에서 `operator.add`를 통해 누적되어 보고서 작성에 활용되도록 개발합니다.