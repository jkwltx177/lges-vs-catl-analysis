# 보고서 파이프라인 출력 점검
- 생성 시각: 2026-04-07 16:25:39
- Markdown: `/Users/hansang-yun/yoon/수업/수업-프로젝트/batery_project/lges-vs-catl-analysis/docs/lges_vs_catl_report_20260407_162539.md`
- PDF: **생성 실패** (WeasyPrint·폰트·의존성 확인)

---

## 1. 보고서 섹션 에이전트 (section0~6)

| 섹션 | 설명 | 글자수(공백 제외 근사) | 상태 | 표 포함 |
|------|------|----------------------|------|--------|
| `section0` | SUMMARY | 757 | 양호 | — |
| `section1` | 서론 — 시장 배경 | 1818 | 양호 | — |
| `section2` | 본론 — LGES | 1969 | 양호 | — |
| `section3` | 본론 — CATL | 1591 | 양호 | — |
| `section4` | 본론 — SWOT | 2134 | 양호 | 예 |
| `section5` | 결론 — 시사점·제언 | 1995 | 양호 | — |
| `section6` | 참고문헌 | 2364 | 양호 | — |

---

## 2. 분석 단계 입력 (bridge → Report)

- `raw_findings` 문서 수: **1**
- `query_coverage` (Task.1 임베딩·검색) 쿼리 수: **12**
- `market_context` 키 수: **6** (비어 있으면 ⚠️)
- `comparative_swot.comparative_summary` 길이: **0** 문자
- `final_insight.final_insights` 항목 수: **4**
- 포트폴리오 `core_services`: LGES **4**개, CATL **4**개

---

## 3. 권장 후속 조치

- PDF가 없으면 `report/final/*.md`와 `docs/*.md`를 편집기나 Pandoc으로 변환할 수 있습니다.
