# Task 2: 시행착오 및 트러블슈팅 기록 (Troubleshooting History)

본 문서는 Task 1과 Task 2를 통합하고 실행하는 과정에서 발생한 주요 에러들과 그 해결 과정을 기록합니다. 향후 유사한 문제 발생 시 참고 자료로 활용할 수 있습니다.

---

## 1. Pydantic 스키마(Structured Output) 검증 에러 (HTTP 400)

### 🚨 문제 발생
`portfolio_node` 실행 중 OpenAI API에서 다음과 같은 **HTTP 400 BadRequestError**가 발생하며 파이프라인이 중단되었습니다.

> `openai.BadRequestError: Error code: 400 - {'error': {'message': "Invalid schema for response_format 'PydanticPortfolioOutput': ... Extra required key 'revenue_contribution' supplied."`

### 🔍 원인 분석
- `src/nodes/data_processing_nodes.py`에서 정의한 `PydanticCompanyPortfolio` 내의 `revenue_contribution` 필드 타입을 `Dict[str, str]`로 지정해 두었습니다.
- LangChain의 `with_structured_output` (OpenAI 함수 호출 파서)은 내부적으로 Pydantic 모델을 JSON Schema로 변환하여 전송하는데, 임의의 Key-Value 쌍을 허용하는 파이썬의 `Dict` 타입을 OpenAI의 엄격한(Strict) 스키마 모드에서 정상적으로 검증(Validate)하지 못해 거부한 것입니다.

### 💡 해결 방법
임의의 딕셔너리 대신, OpenAI가 명확히 파싱할 수 있는 **문자열 리스트(`List[str]`)** 형태로 타입을 단순화하고 `description`에 예시를 명확히 주어 LLM이 원하는 대로 값을 넣도록 우회했습니다.

```python
# 수정 전
revenue_contribution: Dict[str, str] = Field(default_factory=dict)

# 수정 후
revenue_contribution: List[str] = Field(
    description="각 서비스별 매출 기여도 추정치 (예: 'BEV 배터리 62%')", 
    default_factory=list
)
```
수정 후 에러 없이 정상적으로 포트폴리오 데이터를 추출할 수 있었습니다.

---

## 2. OpenAI API 원문 JSON 파싱 에러 (Null Byte 문제)

### 🚨 문제 발생
Task 1의 `company_research_node`에서 LLM에 프롬프트를 전송할 때 다음과 같은 **HTTP 400 JSON Parsing Error**가 발생했습니다.

> `openai.BadRequestError: Error code: 400 - {'error': {'message': "We could not parse the JSON body of your request. (HINT: ... what was sent was not valid JSON."`

### 🔍 원인 분석
- VectorDB에 적재된 문서(`raw_documents`) 원문 텍스트 내에 눈에 보이지 않는 **Null Byte(`\x00` 또는 `\u0000`)** 문자가 포함되어 있었습니다. (특히 PDF 문서를 임베딩할 때 종종 발생)
- Python의 `json.dumps()`는 정상적으로 동작하지만, HTTP 페이로드로 전송받은 OpenAI의 백엔드 서버는 `\x00`가 포함된 문자열을 Invalid JSON으로 간주하고 즉시 400 에러를 반환해버립니다.

### 💡 해결 방법
`src/nodes/research_nodes.py`에서 문서를 조합하여 `doc_text` 문자열을 생성할 때, 해당 특수 문자들을 명시적으로 제거(Sanitize)하는 로직을 추가했습니다.

```python
# 수정 로직
doc_text = doc_text.replace("\x00", "").replace("\u0000", "")
prompt = _COMPANY_RESEARCH_PROMPT.format(documents=doc_text, ...)
```
위 코드를 추가한 후 null byte로 인한 파싱 에러가 즉각적으로 사라지고, LLM 호출이 정상적으로 진행되었습니다.

---

## 3. 요약
통합 파이프라인 과정에서는 **1) 강제되는 JSON 스키마의 엄격성**, **2) 원본 문서의 불순물(특수문자)** 이 가장 큰 장애물이 될 수 있습니다. 
Pydantic 스키마는 최대한 예측 가능하고 단순한 타입(`List`, `str`)으로 풀어서 작성하고, VectorDB 등 외부에서 가져오는 데이터는 반드시 Sanitize 과정을 거치도록 코딩하는 것이 좋습니다.