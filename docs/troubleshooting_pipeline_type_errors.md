# Troubleshooting: full_pipeline_graph.py 타입 에러 해결 보고서

## 1. 개요 (Overview)
`src/agents/full_pipeline_graph.py`에서 Pylance(Pyright) 타입 체크 도중 다수의 `reportArgumentType` 및 `reportReturnType` 에러가 발생했습니다. 이 에러들은 LangGraph의 `invoke` 함수 호출 시 전달되는 매개변수와 반환값의 형식이 선언된 형식과 일치하지 않아 발생한 문제입니다.

## 2. 문제점 (Problems)
주요 에러 메시지는 다음과 같았습니다:
- **인수 타입 불일치:** `Dict[str, Any]` 형식을 `ResearchGraphState | Command[Unknown] | None` 형식에 할당할 수 없음.
- **설정(Config) 타입 불일치:** `dict[str, dict[str, str]]` 형식을 `RunnableConfig | None` 형식에 할당할 수 없음.
- **반환 타입 불일치:** `ReportGraphState` 형식을 `Dict[str, Any]`에 반환하도록 할당할 수 없음.

## 3. 원인 분석 (Root Cause)
LangGraph는 그래프가 컴파일될 때 특정 `TypedDict` 상태(State)를 기반으로 타입 검사를 수행합니다. 
- 기존 코드에서는 범용적인 `Dict[str, Any]`를 사용하여 상태를 주고받았으나, LangGraph의 `invoke` 메서드는 컴파일 시 정의된 구체적인 `TypedDict` 형식을 요구합니다.
- `config` 매개변수 또한 단순한 딕셔너리가 아닌 `langchain_core.runnables.RunnableConfig` 형식을 명시적으로 요구하는 경우가 있어 타입 엔진에서 경고를 발생시켰습니다.

## 4. 해결 방법 (Solution)

### 4.1 구체적인 상태 타입(TypedDict) 도입
`src.state.state`에서 정의된 `ResearchGraphState`, `DataRefineGraphState`, `AnalysisGraphState`, `ReportGraphState`를 임포트하여 함수 시그니처와 변수 선언에 적용했습니다.

```python
# 수정 전
def run_research_refine_analysis(initial_state: Dict[str, Any]) -> Dict[str, Any]:

# 수정 후
def run_research_refine_analysis(initial_state: ResearchGraphState) -> AnalysisGraphState:
```

### 4.2 RunnableConfig 명시
그래프 실행 설정인 `config` 변수들에 `RunnableConfig` 타입을 명시적으로 지정하여 타입 엔진이 올바르게 인식하도록 수정했습니다.

```python
from langchain_core.runnables import RunnableConfig

research_config: RunnableConfig = {"configurable": {"thread_id": f"{thread_prefix}_research"}}
```

### 4.3 타입 캐스팅(cast) 사용
`graph.get_state(config).values`와 같이 동적으로 반환되는 값들에 대해 `typing.cast`를 사용하여 명확한 상태 타입을 부여했습니다.

```python
from typing import cast

research_state = cast(ResearchGraphState, research_graph.get_state(research_config).values)
```

## 5. 결과 (Result)
- **타입 안정성 확보:** IDE(VS Code 등)에서 각 상태의 필드에 대한 자동 완성 및 타입 체크가 정상적으로 작동합니다.
- **코드 가독성 향상:** 파이프라인의 각 단계에서 어떤 데이터가 오가는지 명확하게 파악할 수 있게 되었습니다.
- **검증 완료:** `pytest tests/` 명령어를 통해 기존의 모든 테스트 케이스가 정상적으로 통과됨을 확인했습니다.

---