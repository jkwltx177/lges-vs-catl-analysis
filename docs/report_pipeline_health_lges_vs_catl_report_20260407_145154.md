# 보고서 파이프라인 출력 점검
- 생성 시각: 2026-04-07 14:51:54
- Markdown: `/Users/daeun/ai-service/lges-vs-catl-analysis/docs/lges_vs_catl_report_20260407_145154.md`
- PDF: **생성 실패** (WeasyPrint·폰트·의존성 확인)

---

## 1. 보고서 섹션 에이전트 (section0~6)

| 섹션 | 설명 | 글자수(공백 제외 근사) | 상태 | 표 포함 |
|------|------|----------------------|------|--------|
| `section0` | SUMMARY | 939 | 양호 | — |
| `section1` | 서론 — 시장 배경 | 1183 | 양호 | — |
| `section2` | 본론 — LGES | 685 | 양호 | — |
| `section3` | 본론 — CATL | 718 | 양호 | — |
| `section4` | 본론 — SWOT | 983 | 양호 | 예 |
| `section5` | 결론 — 시사점·제언 | 1401 | 양호 | — |
| `section6` | 참고문헌 | 181 | 양호 | — |

---

## 2. 분석 단계 입력 (bridge → Report)

- `raw_findings` 문서 수: **1**
- `market_context` 키 수: **6** (비어 있으면 ⚠️)
- `comparative_swot.comparative_summary` 길이: **0** 문자
- `final_insight.final_insights` 항목 수: **4**
- 포트폴리오 `core_services`: LGES **3**개, CATL **3**개

---

## 3. 권장 후속 조치

- PDF가 없으면 `report/final/*.md`와 `docs/*.md`를 편집기나 Pandoc으로 변환할 수 있습니다.
