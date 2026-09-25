# 검증 로그 — 11. 사용자 매뉴얼 (`11-user-manual.md`)

- 대상 산출물: `docs/harness/11-user-manual.md` (v1.0)
- 검증 수행 에이전트: `11-docs-handoff-writer`
- 검증 일시: 2026-09-25
- 적용 규칙: ORCHESTRATOR.md 규칙 B(최소 2회 내부 검증), 규칙 C(이상 없음도 근거와 함께)

---

## 1차 검증 — 작성자 관점 (사실관계/출처 일치, 민감정보 혼입 여부)

| 점검 항목 | 방법 | 결과 |
|---|---|---|
| §3 라우트별 서술이 실제 검증된 응답과 일치하는가 | `docs/harness/08-full-system-test.md` §4-2 E2E-V01~V13 대조 | PASS — `/`, `/blog/<slug>/`, `/category/<slug>/`, `/tag/<slug>/`(한글 slug), `/feed.xml`, `/privacy-policy/`, `/terms/`, `/cookies/` 전부 실제 200/404 응답으로 확인된 항목만 서술 |
| 뉴스레터 성공/오류 메시지 문구 정확성 | `webapp/subscribers/forms.py`, `webapp/subscribers/templates/subscribers/subscribe_result.html` 원문 대조 | PASS — "구독해주셔서 감사합니다.", "요청이 너무 잦습니다. 잠시 후 다시 시도해주세요.", 필드별 오류 문구 전부 원문 그대로 인용, 각색 없음 |
| 이메일 열거 방지 설명(FAQ Q2)의 근거 | `docs/harness/09-security-audit.md` SEC-14(신규/기존(active)/기존(unsubscribed) 동일 200 응답) | PASS — 근거 명시, 사용자가 오작동으로 오인하지 않도록 "설계된 동작"임을 명확히 서술 |
| 콜드스타트 안내 문구 정확성 | `webapp/config/templates/partials/footer.html` 원문 대조 | PASS — 실제 템플릿 문구("⚡ 무료 인프라로 운영 중이라 오랜만에 방문하시면...") 그대로 인용, 04-ux-design.md 설계와 실제 구현 일치 확인 |
| 접근성 서술의 근거 | `webapp/config/templates/base.html`(skip-link, main 랜드마크), `webapp/config/static/js/cookie-consent.js`(Esc 키, localStorage) 코드 열람 | PASS — 코드에서 실제 구현 확인된 사항만 서술. 실제 브라우저/스크린리더 동적 검증 미수행 사실(08-full-system-test.md §2)은 §5 말미에 명시적으로 고지 |
| 뉴스레터 탈퇴 경로의 실제 존재 여부 | `webapp/legal/migrations/0002_create_legal_pages.py` 원문 확인, `contact_email` 관련 템플릿/코드 전수 검색(`Grep`) | **발견**: 개인정보처리방침의 "문의처" 섹션에 실제 연락처(이메일 등)가 화면에 렌더링되지 않음(`SiteSettings.contact_email` 관련 코드 미발견). §3.6/FAQ Q3에 이 사실을 투명하게 고지하는 문단을 반영 완료 |
| 운영자 전용 정보(관리자 URL, 09단계 보안 결함 ID, 인프라/시크릿) 혼입 여부 | 문서 전체 재검토 | PASS — `/cms-admin/`, `/django-admin/`, DEF-09-01~04, 인프라 벤더명, 백업 절차 등 전혀 언급하지 않음. 운영자 워크플로(Wagtail 어드민 사용법)도 의도적으로 제외 |
| REQ-018~020(검색/댓글/소셜공유) 미구현 사실 안내 | `docs/harness/02-planning.md` §4, `docs/harness/04-ux-design.md` §0 대조 | PASS — FAQ Q5로 "없어진 것이 아니라 v1 범위 밖"임을 명확히 안내 |

**1차 검증 결론**: 결함 0건(1건의 정보 격차 — 문의처 연락처 미노출 — 를 발견해 문서에 투명하게 반영 완료). 추가 수정 불필요.

---

## 2차 검증 — 독립 심사자 관점 ("이 문서만 받고 처음 방문한 독자/구독자가 추가 질문 없이 서비스를 이용할 수 있는가")

| 점검 항목 | 방법 | 결과 |
|---|---|---|
| 온보딩(§2)→화면별 사용법(§3)→FAQ(§4) 흐름만으로 초회 이용이 가능한가 | 신규 방문자 시나리오 재연(로그인 불필요 확인 → 홈/상세/카테고리/태그 탐색 → 뉴스레터 구독 시도 → 오류 상황 대응) | PASS — 추가 질문 없이 수행 가능 |
| 가장 혼란 소지가 큰 "뉴스레터 탈퇴" 안내의 충분성 | §3.6과 FAQ Q3 이중 배치, 한계(연락처 미노출) 명시 여부 재확인 | PASS — 한계까지 숨기지 않고 명시, "이 문제는 사용자 매뉴얼이 임의로 해결할 수 있는 사항이 아니다"라고 범위를 명확히 함 |
| 미검증 항목(실제 브라우저/스크린리더 동적 검증)을 과장 서술하지 않았는가 | §5 전체 문장 단위 재검토 | PASS — "설계서/코드 수준에서 확인"과 "실제 보조기기 환경 100% 확인은 아님"을 구분해 서술 |
| 운영자 전용 정보 노출 여부 재검색 | 문서 전체를 대상으로 어드민 URL/보안 결함 ID/인프라 벤더명 키워드 재검색 | PASS — 등장하지 않음, 정보 노출 사고 없음 |
| 접근성 이용 안내가 실제 접근성 기준 사용자에게 실질적으로 도움이 되는가 | 04-ux-design.md §5(WCAG 2.1 AA) 항목별(색상대비/키보드/스킵링크/대체텍스트/모션/언어) 대조 | PASS — 6개 항목 모두 실제 구현 확인 근거와 함께 서술됨 |

**2차 검증 결론**: 결함 0건. **PASS.**

---

## 최종 판정

- [x] **PASS** — `docs/harness/11-user-manual.md` v1.0 확정. 다른 3개 문서(`11-ops-handoff-runbook.md`/`11-admin-manual.md`/`11-api-reference.md`)의 확정과 별개로, 이 문서 자체는 완료 조건을 충족한다.
