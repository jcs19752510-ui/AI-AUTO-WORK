# 09. 보안검증 결과서 (Security Audit Report)

> **최종 판정 갱신(규칙F 재작업 라운드 2 완료, 2026-09-18)**: 아래 §1~§10(원본, 2026-09-17 작성)은 **FAIL**로 판정했었다 — `DEF-09-01`(High, `/django-admin/login/` 무차별대입 방어 완전 우회)을 실측으로 발견했기 때문이다. 이후 규칙F 재작업 체인(3단계 설계 v1.3/DEC-040 → 5단계 WU-09 라운드 2/DEC-041 → 6단계 `unit-09-test.md` 재검증 PASS → 7단계 `feature-WU-09-integration-test.md` 재검증 PASS, 구독자 하드삭제 E2E까지 확인)이 순서대로 완료되었고, **이 문서 맨 아래 "재작업 라운드 2(DEF-09-01) 재검증" 절이 그 체인의 마지막 단계(9단계)로서, 하위 단계의 PASS 주장을 그대로 신뢰하지 않고 독립적으로 직접 재현**했다. 결론: **DEF-09-01 Fixed 확인, 신규 Critical/High 없음 → 최종 판정 PASS로 갱신**. 원본 §1~§10은 최초 발견 당시 기록 그대로 보존하며(수정하지 않음), 최신 판정 근거는 문서 맨 아래 라운드 2 절을 따른다.

## 1. 개요
- 테스트 대상: **전체 코드베이스(`webapp/` 전체) + 설계서(`docs/harness/03-system-design.md` §5) + 의사결정 로그(`decisions.md` DEC-001~038) + git 이력 전체**. WU-01~10(REQ-001~017 In-Scope) 전부를 대상으로 한 보안 관점 재검토.
- 테스트 유형: 보안
- 적용 Tier: **Standard** (08단계/DEC-036이 이미 Standard로 선언 — 결제/의료 등 규제 민감 영역 아님, 개인정보 처리 범위가 이메일 수집 정도로 제한적, AI/LLM 기능 없음. 다만 이 Tier 선언 자체가 "낮은 위험도"를 의미하지 않으며, 발견된 결함의 심각도 판정에는 영향을 주지 않는다 — 아래 §6 참고)
- 테스트 목적: OWASP Top 10 관점 취약점 점검, 의존성 취약점(CVE)/의존성 환각(slopsquatting) 점검, 인증/인가 우회·권한경계 점검, 민감정보 노출 점검, 개인정보 컴플라이언스·규제 민감 도메인(규칙I)·AI/LLM(규칙J) 반영 여부 점검, 설계서 보안 원칙과 실제 구현의 일치 여부 점검, 이번 세션 중 발생한 `.venv_wu09_it` git 사고(커밋 `3e594d7c`)의 시크릿 노출 여부 확정
- 관련 산출물: `docs/harness/decisions.md`(DEC-001~038, 특히 DEC-009/016/024/025/028~031/032~034), `docs/harness/traceability.md`, `docs/harness/03-system-design.md` §5(보안 설계 원칙), `docs/harness/08-full-system-test.md`(PASS, 신규 결함 0건), `docs/harness/units/unit-01~10-note.md`/`*-test.md`(Deferred 결함 재평가), `.claude/agents/09-security-auditor.md`
- 테스트 수행자(에이전트): `09-security-auditor`
- 테스트 일시: 2026-09-17

> **작업 대상 경로에 관한 안전 점검(투명성 기록)**: 이번 세션의 작업 지시는 프로젝트 루트를 `C:\big21\vibe-coding\AI-AUTO-WORK`로 명시했으나, 환경(cwd) 기본값은 이와 무관한 별개 프로젝트(`C:\big21\vibe-coding\STOCK-ANALYZER-KR`, 주식분석 서비스)를 가리키고 있었다. 작업 착수 전 `AI-AUTO-WORK/.claude/agents/09-security-auditor.md`, `docs/harness/decisions.md`(DEC-001~038) 등을 직접 열람해 지시 내용(Wagtail/Django 블로그, WU-01~10, DEC-009 등)과 실제 저장소 구조가 정확히 일치함을 확인한 뒤에만 절대경로 기준으로 작업을 진행했다 — 두 프로젝트를 혼동하거나 잘못된 대상에 조치를 취하지 않았음을 명시한다.

---

## 2. 테스트 범위 및 제외 범위

### In-Scope
- 인증/인가 우회 가능성, 권한 경계(수평/수직 권한 상승)
- 인젝션(SQL/커맨드/XSS 등), 입력 검증 누락
- 시크릿/자격증명 하드코딩 또는 로그 노출(이번 세션 `.venv_wu09_it` 사고 포함, git 이력 전체 대상)
- 의존성 취약점(CVE) — `requirements.txt` 9개 패키지 전수
- 의존성 환각(hallucinated dependency) 점검 — 전 패키지 실재/평판 확인
- 민감정보 저장/전송 시 암호화 여부
- 에러 메시지를 통한 정보 노출
- 설계서(03 §5)의 보안 원칙과 실제 구현의 불일치
- 개인정보 처리 컴플라이언스(수집 최소화/보관기간·파기절차/제3자 제공·위탁 고지)
- 오픈소스 의존성 라이선스 검토
- 외부 데이터/API 이용약관 준수
- 규제 민감 도메인 대응(규칙I) 반영 여부
- AI/LLM 기능 내장 대응(규칙J) 반영 여부

### Out-of-Scope 및 사유
- **실제 공격 실행(서비스/제3자에 실피해를 주는 방식)**: 수행하지 않음(에이전트 정의 필수 원칙). 재현은 정적 분석 + 로컬(`.harness-tmp/` 임시 venv, `django.test.Client`) 재현 범위 내로 제한했다.
- **실제 배포 환경(Render/Neon/R2/GitHub Actions) 네트워크 침투 테스트**: 아직 실제 클라우드 리소스가 발급되지 않았고(08단계와 동일 제약), 설령 발급되었더라도 실제 서비스 대상 공격은 금지 원칙에 위배된다. 10단계(배포테스트) 이후 별도 보안 스모크(예: 헤더 재확인) 권고.
- **REQ-018~020(WU-11, Could)/REQ-021~027(Out-of-Scope 확정)**: 08단계와 동일하게 이번 단계 대상 아님.
- **개별 WU 단위/통합 테스트의 기능적 재검증**: 06/07/08단계가 이미 PASS로 확정한 기능 동작(예: FAQ JSON-LD 필드 매핑)은 반복하지 않는다. 이번 단계는 "보안 관점"으로만 재검토한다.

---

## 3. 테스트 환경

### 3-1. 실행 환경
- OS/런타임: Windows 10 Pro 10.0.19045, Python 3.12.10(`py -3.12`).
- 정적 분석: `Read`/`Grep`/`Glob`로 `webapp/` 전체 소스, `docs/harness/*.md`, `.github/workflows/*.yml`, `.gitignore` 전수 확인.
- git 이력 분석: `git log --all`, `git show <commit> --stat`, `git show <commit>:<path>`로 커밋 `3e594d7c`(`.venv_wu09_it` 사고) 및 전체 이력에서 시크릿 패턴(AKIA/PEM 헤더/`postgres://user:pass@host` 등)을 검색.
- 로컬 동적 재현(신규 venv, 규칙K 준수): `webapp/.harness-tmp/venv_09_sec/`(Python 3.12, `webapp/requirements.txt` clean install) — `django.test.Client` 기반으로 `/cms-admin/login/`과 `/django-admin/login/`에 동일 IP로 각 11회 연속 POST를 보내 레이트리밋 동작 차이를 실측 재현(§6 DEF-09-01 근거). 검증 후 즉시 삭제(§7 Teardown 참고).
- 외부 확인: WebSearch로 Django 5.2.17/Wagtail 7.4.3의 최신 공식 보안 권고(CVE) 조회(2026-09-17).

### 3-2. 테스트 데이터
- 재현 스크립트 전용 인메모리 테스트 DB(`DiscoverRunner`가 자동 생성/파기하는 SQLite `:memory:` 계열 테스트 DB) — 슈퍼유저 1건(`reprosuper`, 더미 비밀번호)만 생성, 실제 운영 데이터 아님.
- git 이력에서 추출한 과거 커밋(`3e594d7c`)의 `webapp/db_wu09_integ_prodlike.sqlite3`를 저장소 밖 세션 스크래치패드(OS 임시 디렉터리)로 1회 추출해 `auth_user` 테이블만 조회 후 즉시 삭제 — 이 파일은 `.harness-tmp/` 대상이 아닌 **git 이력 안의 과거 blob**이므로 규칙K(저장소 내부 `.harness-tmp/`)가 아니라 "저장소 밖 세션 스크래치패드" 허용 범위를 사용했다(작업 지시 문구 그대로 적용).

### 3-3. 전제 조건 (Preconditions)
- 08단계(전체 풀테스트) PASS, 신규 결함 0건(`docs/harness/08-full-system-test.md` §9).
- 작업 시작 전 `bash automation/harness-janitor.sh --check`로 `.harness-tmp/` 잔여물 없음 확인(클린 상태, §7-0 참고).

---

## 4. 테스트 케이스 및 결과

### 4-1. 인증/인가 우회·권한 경계

| ID | 시나리오 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail | 비고 |
|----|----------|-----------|-----------|-----------|-----------|------|
| SEC-01 | Wagtail 어드민 로그인 레이트리밋(`/cms-admin/login/`) 실효성 | 동일 IP(`203.0.113.50`)로 11회 연속 잘못된 비밀번호 POST(`.harness-tmp/venv_09_sec`, `django.test.Client`) | 1~10회 200, 11회째 429 | `[200×10, 429]` | PASS | `core/admin_auth.py` 정상 동작 재확인(WU-09/08과 동일 결론) |
| SEC-02 | **Django 기본 어드민 로그인(`/django-admin/login/`)의 동일 레이트리밋 적용 여부** | 동일 IP·동일 계정으로 11회 연속 잘못된 비밀번호 POST | 429가 나와야 함(REQ-010/DEC-009/DEC-029가 "필수"로 요구하는 무차별대입 방어) | **11회 전부 200 — 429 없음** | **FAIL** | **DEF-09-01(High) — 아래 §6 상세.** `core/admin_auth.py`의 IP 레이트리밋이 `wagtailadmin_login` URL 이름에만 연결되어 있고, `config/urls.py`가 `path("django-admin/", admin.site.urls)`로 마운트한 Django 기본 관리자 로그인(별개 뷰, `django.contrib.admin.sites.AdminSite.login`)에는 전혀 적용되지 않음 |
| SEC-03 | 두 로그인 경로가 동일 자격증명 저장소(`auth_user`)를 공유하는지 | 코드 확인(`core/admin_auth.py`, Wagtail/Django 인증 백엔드 공통) + SEC-01/02 재현에서 동일 `reprosuper` 계정으로 둘 다 시도 | 동일 계정 | 동일 계정(같은 `auth_user` 행) — Wagtail 어드민 전체 콘텐츠 권한과 `subscribers.NewsletterSubscriber` 하드삭제(개인정보 파기절차, §5.6) 권한을 모두 통제하는 유일 계정 | 확인 | SEC-02가 실질적 전면 침해로 이어지는 근거 — DEC-009 docstring 자신이 "어드민 계정이 사이트 전체 콘텐츠에 대한 단일 장애점"이라고 명시한 그 계정과 동일함 |
| SEC-04 | `/django-admin/`가 실제로 필요한 기능인지(단순 제거 가능한 잔재인지) | `subscribers/admin.py` 확인 | 필요 없으면 라우트 자체 제거 권고, 필요하면 보호 권고 | `NewsletterSubscriberAdmin`이 §5.6 개인정보 파기절차(구독 취소 요청 시 운영자 하드 삭제)의 **유일한 실제 삭제 경로**로 등록되어 있음(`has_add_permission`/`has_change_permission` 모두 `False`, 목록/검색/삭제만 가능) | 확인 | 라우트 제거는 §5.6 요구사항과 충돌 — "보호"가 올바른 조치 방향(§8 권고 참고) |
| SEC-05 | 미배정 스태프의 어드민 접근 차단(수직 권한 상승) | 08단계 E2E-O07 결과 재확인(회귀 검증, 반복 실행 안 함) | 302/403 | 08단계에서 이미 PASS 확인(`wagtailadmin.access_admin` 게이트) | PASS | 필수 원칙(반복 검증 회피)에 따라 08단계 결과를 그대로 인용 |
| SEC-06 | Editors/Moderators 그룹의 Category 스니펫 권한(수평/수직 경계) | `core/migrations/0001_setup_editor_permissions.py`, DEC-028 재확인 | 그룹별 CRUD 권한이 명시적으로 부여되어 있어야 함 | 코드 확인 — Wagtail 코어 권한 자동부여 대상이 아닌 스니펫 권한을 이 마이그레이션이 명시적으로 `get_or_create`로 부여(WU-09 자체 발견·수정한 결함, DEC-028) | PASS | 6/7단계가 이미 `CategoryEditorPermissionTests`로 실측 확인, 반복 검증 회피 |
| SEC-07 | 세션 하이재킹/고정 방어 | `production.py` 확인 | `SESSION_COOKIE_SECURE=True`, `CSRF_COOKIE_SECURE=True`, Django 기본 세션 로그인 시 세션 키 재발급(`django.contrib.auth.login()` 표준 동작) | 확인(§5.5.2 코드 그대로), 세션 고정 방지는 Django `login()` 내장 동작(로그인 성공 시 `cycle_key()` 자동 호출)에 의존 — 커스텀 세션 로직 없음 | PASS | |
| SEC-08 | 비밀번호 정책 | `config/settings/base.py` `AUTH_PASSWORD_VALIDATORS` | 최소 4종 검증기 활성화 | `UserAttributeSimilarityValidator`/`MinimumLengthValidator`/`CommonPasswordValidator`/`NumericPasswordValidator` 전부 활성화, `ensure_superuser.py`가 부트스트랩 시에도 `validate_password()` 재사용(DEC-030) | PASS | |
| SEC-09 | 오픈 리다이렉트(뉴스레터 `next` 파라미터) | `subscribers/views.py::_safe_next` 코드 확인 | `/`로 시작하고 `//`로 시작하지 않는 경로만 허용 | 코드 확인, 화이트리스트 방식으로 외부 도메인 리다이렉트 차단 | PASS | |
| SEC-10 | CSRF가 레이트리밋을 무력화(우회)하는지 (DEC-031 재확인) | `core/admin_auth.py` docstring + DEC-031 실측 근거 재검토(반복 실행 안 함, 코드 검토로 논리 재확인) | CSRF 실패 요청은 자격증명을 전혀 시험하지 못하므로 카운터 미증가가 실질적 결함이 아니어야 함 | WU-09/6단계가 `Client(enforce_csrf_checks=True)`로 이미 실측 확인한 논리를 코드 검토로 재확인 — 유효 CSRF 없이는 어떤 자격증명도 시험 불가, 유효 CSRF를 가진 요청은 예외 없이 카운터를 통과함 | PASS(결함 아님, 기존 판단 유지) | 단, 이 논리는 `/cms-admin/login/`에만 적용됨 — `/django-admin/login/`은 카운터 자체가 없으므로 이 논리와 무관하게 SEC-02가 별도 결함 |

### 4-2. 인젝션 / 입력 검증

| ID | 시나리오 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail | 비고 |
|----|----------|-----------|-----------|-----------|-----------|------|
| SEC-11 | SQL Injection 표면 | `webapp/**/*.py` 전수 검색: `.raw(`, `cursor.execute`, `.extra(`, `RawSQL` | 0건이어야 함(ORM 전용, 03 §5.2) | 0건(No matches found) | PASS | 백업(`pg_dump`)은 애플리케이션 코드가 아닌 독립 CLI이므로 원칙 예외 아님(설계서 §5.2 명시와 일치) |
| SEC-12 | XSS — `\|safe`/`mark_safe`/`format_html` 전수 검색 | `webapp/**/*.py`, `webapp/**/*.html` 전수 grep | 사용처가 있다면 전부 근거와 함께 정당화되어야 함(03 §5.2 "예외 시 코드 리뷰에서 별도 근거 요구") | `\|safe` 템플릿 필터: 0건. `mark_safe` 사용처 2건 — (1) `legal/models.py::_add_heading_anchors`: 운영자(에디터)가 입력하고 Wagtail RichText 화이트리스트 필터를 통과한 HTML에 h2 앵커 id만 정규식으로 주입(방문자 입력 아님, 새 태그 신설 없음). (2) `core/templatetags/seo_tags.py::jsonld`: `json.dumps` 결과에 `<`/`>`/`&`만 유니코드 이스케이프(Django 내장 `json_script`와 동일 전략)해 `</script>` 조기종료·HTML 삽입을 차단한 뒤 JSON-LD `<script>` 블록에 삽입 | PASS | 둘 다 코드 리뷰로 근거 확인 완료, 방문자 제어 입력이 이스케이프 없이 렌더링되는 경로 없음 |
| SEC-13 | 이미지 업로드 검증(임의 파일 업로드/XSS-via-SVG) | `config/settings/base.py` `WAGTAILIMAGES_*` 확인 | 확장자 화이트리스트, 크기 상한, 디컴프레션 폭탄 방지 | `WAGTAILIMAGES_EXTENSIONS=["avif","gif","jpg","jpeg","png","webp"]`(**svg 명시적 배제** — XSS 위험 이미지 포맷 차단), `MAX_UPLOAD_SIZE=10MB`, `MAX_IMAGE_PIXELS=128M`(디컴프레션 폭탄 방지). Wagtail은 확장자뿐 아니라 실제 파일 콘텐츠(PIL 디코딩)로 검증하므로 확장자 위조만으로 우회 불가 | PASS | |
| SEC-14 | 뉴스레터 폼 입력 검증(이메일 열거/봇/XSS) | `subscribers/views.py`/`forms.py` 확인, 03 §5.3 계약과 대조 | 이메일 열거 방지(동일 성공 메시지), 허니팟, 레이트리밋, 서버사이드 `EmailField` 검증 | 코드 확인 — 신규/기존(active)/기존(unsubscribed) 3가지 분기 모두 동일 200 응답, `hp_field` 채워지면 200 위장 응답(미저장), IP 레이트리밋(10분 5회), 폼 ID/variant 파라미터도 화이트리스트로 제한(`_ALLOWED_FORM_IDS`/`_ALLOWED_VARIANTS`) | PASS | 6/7단계가 XSS형/SQLi형/빈값/null바이트 입력(TC-014~030)을 이미 실측 PASS — 반복 검증 회피, 이번 단계는 설계 계약 일치 여부만 재확인 |
| SEC-15 | 커맨드 인젝션(백업 워크플로 쉘 스크립트) | `.github/workflows/neon-db-backup.yml` 전수 검토 | 사용자 제어 값이 쉘 명령에 직접 보간되지 않아야 함 | 모든 값이 환경변수(`env:`) 경유로 전달되고 `set -euo pipefail` 적용, GitHub Secrets 값이 커맨드라인에 직접 문자열 보간되지 않음(변수 참조만 사용) | PASS | DEC-034(시크릿 공백값 경계, Low)는 이미 추적 중인 별도 이슈, §6에서 재확인만 |

### 4-3. 민감정보/에러 노출

| ID | 시나리오 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail | 비고 |
|----|----------|-----------|-----------|-----------|-----------|------|
| SEC-16 | `production.py` 시크릿 하드코딩 여부 | 파일 전문 검토 | 하드코딩된 시크릿 없이 전부 `os.environ`/`_require_env` 경유 | `SECRET_KEY`/`DATABASE_URL`/`R2_ACCESS_KEY_ID`/`R2_SECRET_ACCESS_KEY` 등 보안 필수값은 `_require_env`(누락 시 기동 실패)로, 나머지는 `os.environ.get`으로 처리 — 하드코딩 0건 | PASS | |
| SEC-17 | `DEBUG=False` 프로덕션 강제 여부 | `production.py`/`dev.py`/`wsgi.py`/`asgi.py`/`manage.py`/`render.yaml` 교차 확인 | production 경로에서 확실히 `DEBUG=False`여야 함 | `production.py`에 `DEBUG=False` 명시, `render.yaml`이 `DJANGO_SETTINGS_MODULE=config.settings.production`을 `value:`(항상 적용, `sync:false` 아님)로 고정 — 실제 배포 경로는 안전 | **PASS(조건부, DEF-09-03 참고)** | `wsgi.py`/`asgi.py`/`manage.py`가 `DJANGO_SETTINGS_MODULE` 미설정 시 **`config.settings.dev`(DEBUG=True, `ALLOWED_HOSTS=["*"]`)로 silently 폴백**하는 fail-open 패턴 발견 — render.yaml이 실제로 값을 고정하므로 즉각적 블로커는 아니나, 방어심층 원칙에 어긋나는 Low 결함으로 §6 DEF-09-03에 기록 |
| SEC-18 | 500 에러 스택트레이스 노출 | 08단계 SYS-16/17 결과 재확인(반복 실행 안 함) | `DEBUG=False`에서 스택트레이스 미노출, `500.html` 정상 렌더링 | 08단계에서 이미 PASS 확인(TemplateSyntaxError 없음, WU-04 DEF-001 수정분 회귀 없음) | PASS | 필수 원칙에 따라 08단계 결과 인용, 이번 단계 재실행 안 함 |
| SEC-19 | 전송 보안 헤더 | 08단계 SYS-19(`curl -D -`) 결과 재확인 | HSTS/X-Frame-Options/X-Content-Type-Options/Referrer-Policy | 08단계에서 전부 확인됨(`Strict-Transport-Security`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`, `Cross-Origin-Opener-Policy: same-origin`) | PASS | Content-Security-Policy(CSP) 헤더는 설계서(03 §5.5)가 요구하지 않아 결함으로 취급하지 않음 — §8에 향후 강화 권고로만 기록 |
| SEC-20 | 로그를 통한 민감정보 노출 | `core/monitoring.py`/`core/middleware.py`/Django 표준 로깅 설정(`LOGGING` 커스텀 오버라이드 여부) 확인 | 요청 로그에 비밀번호/토큰 등이 평문으로 기록되지 않아야 함 | 커스텀 `LOGGING` dict 없음(Django 기본 `django.utils.log.DEFAULT_LOGGING` 그대로 사용, production.py 주석이 이를 명시), `core/monitoring.py`는 요청 수/응답시간만 집계하고 요청 바디를 로깅하지 않음 | PASS | |
| SEC-21 | `.env`/시크릿의 저장소 커밋 여부(**현재 작업트리**) | `git ls-files`로 추적 중인 `.env*` 확인, `webapp/.gitignore`/루트 `.gitignore` 확인 | `.env` 추적 안 됨, `.env.example`만 추적(플레이스홀더) | `.env` 미추적 확인, `.env.example`은 전부 빈 값/설명 주석(§4-3 SEC-22와 함께 실측) | PASS | |
| SEC-22 | **`.venv_wu09_it` 사고(커밋 `3e594d7c`) 시크릿 노출 여부 — 명시적 요구사항** | `git show 3e594d7c --stat`/`--name-only`로 전체 변경 파일 목록 확보 → PIL/site-packages 등 순수 서드파티 라이브러리 소스는 제외하고 **프로젝트 고유 파일**만 별도 검토 → 프로젝트 고유 파일: `webapp/config/settings/it_test_prodlike_wu09_integ.py`, `webapp/db_wu09_integ_prodlike.sqlite3`, `webapp/render.yaml`, `webapp/build.sh`, `webapp/core/*`, `webapp/ADMIN_ACCESS_GUIDE.md` 등 → 각 파일 `git show 3e594d7c:<path>`로 전문 확인, sqlite DB는 임시 추출 후 `auth_user` 테이블 직접 쿼리 | 실제 시크릿(운영 자격증명)이 없어야 함 | **실제 시크릿 노출 없음.** ① `it_test_prodlike_wu09_integ.py`는 `production.py`를 상속하며 자체 시크릿 없음(환경변수 경유). ② `db_wu09_integ_prodlike.sqlite3`의 `auth_user`에는 `wu09itadmin`/`wu09-editor`/`wu09-plainstaff` 3개 계정만 존재하며 전부 `@example.com` 더미 이메일 + `pbkdf2_sha256$1000000$...` 형태의 정상 해시(솔트 포함, 1,000,000회 반복)된 **테스트 전용 비밀번호**로, 운영 계정이 아님. ③ git 전체 이력(`git log --all -p`)에서 AWS-style 키(`AKIA...`), PEM 개인키 헤더, 실제 자격증명이 포함된 `postgres://user:pass@host` 패턴을 검색한 결과 전부 `user:pass@localhost`류의 문서화된 더미 값뿐, 실제 값 0건 | **PASS(사고는 실재하나 시크릿 노출은 없음)** | **근본 원인**: 사고 당시(`3e594d7c` 커밋 시점) `webapp/.gitignore`가 `.venv/`(정확히 이 이름)와 `venv/`만 무시했고 `.venv_wu09_it`처럼 접미사가 붙은 이름은 매칭하지 않았음(직전 커밋 `f89dd903`에서 실측 확인). **이후 세션(DEC-035)이 이미 `.venv*/`/`*.sqlite3` 와일드카드로 `.gitignore`를 강화**해 동일 실수는 더 이상 재발하지 않으며, 해당 파일들은 이후 커밋(`e8900bf7`)에서 작업트리에서 제거됨(현재 작업트리에는 없음, 확인 완료). **잔존 리스크**는 §6 DEF-09-02(Low) 참고 — git 이력 자체(및 이미 push된 원격)에는 여전히 파일이 남아있음 |

### 4-4. 의존성 취약점 / 의존성 환각(slopsquatting) / 라이선스

| ID | 시나리오 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail | 비고 |
|----|----------|-----------|-----------|-----------|-----------|------|
| SEC-23 | `requirements.txt` 9개 패키지 실재성(hallucinated dependency) 확인 | 각 패키지명을 실제 지식/평판 기준으로 교차 확인 — Django, wagtail, `psycopg[binary]`, `dj-database-url`, `django-storages[s3]`, `boto3`, `gunicorn`, `uvicorn[standard]`, `whitenoise`, `python-dotenv` | 전부 PyPI에 실재하는 유명·고다운로드 패키지여야 하며 오타스쿼팅/최근 등록된 의심 패키지가 없어야 함 | 9개 전부 각 생태계에서 수백만~수억 다운로드 규모의 확립된 표준 패키지(Django/Wagtail 프레임워크 본체, psycopg3 공식 PostgreSQL 드라이버, boto3 AWS SDK 등)로, 이름 오타·유사 패키지 징후 없음. 5단계(WU-01, `unit-01-note.md`)가 `pip index versions`로 직접 실재를 재확인한 기록도 교차 확인됨 | PASS | 신규 패키지가 이번 08→09단계 사이 추가되지 않았음(08단계 §3-1 `pip freeze`와 정확히 동일 구성 재확인) |
| SEC-24 | Django 5.2.17 CVE 스캔 | WebSearch(2026-09-17) | 알려진 미패치 CVE가 없어야 함 | Django 공식 2026-08-04 보안 릴리스(5.2.17)가 CVE-2026-15307(High)/15337(Low)/15830(Moderate)/15920(Moderate)를 이미 패치한 **최신 5.2 LTS 버전**. 이 프로젝트가 핀한 버전(5.2.17)이 곧 그 패치 버전 자체이므로 대상 CVE 없음. 별도로 확인한 CVE-2026-1207(SQLi, RasterField/PostGIS 전용, 5.2.11에서 패치)도 이 프로젝트가 `django.contrib.gis`를 사용하지 않아 애초에 비대상이며, 버전 자체도 이보다 최신 | PASS | 출처: djangoproject.com 2026-08-04 보안 공지, django.readthedocs.io 보안 이력 |
| SEC-25 | Wagtail 7.4.3 CVE 스캔 | WebSearch(2026-09-17) | 알려진 미패치 CVE가 없어야 함 | CVE-2026-55468(Pages admin API 정보노출, CVSS 4.3 Medium)은 7.0.9/7.3.4/**7.4.3**/8.0rc2에서 패치 완료 — 이 프로젝트가 핀한 버전이 바로 그 패치 버전. CVE-2026-54261~54263(7.4.2에서 패치)도 7.4.3(그 다음 버전)에 이미 포함 | PASS | 출처: sentinelone.com CVE 데이터베이스, strix.ai CVE 상세 |
| SEC-26 | 나머지 패키지(psycopg/gunicorn/django-storages/boto3/uvicorn/whitenoise) CVE 스캔 | WebSearch(2026-09-17) | 고정 버전에 활성 CVE가 없어야 함 | 검색 결과 이 프로젝트의 핀 버전(psycopg 3.2.10/gunicorn 23.0.0/django-storages 1.14.6/boto3 1.35.36)을 직접 겨냥한 활성 CVE 미발견. django-storages의 과거 CVE-2024-39330은 1.14.4 이전 버전 대상이며 이 프로젝트는 그보다 최신인 1.14.6 사용 | PASS | 다만 CVE 데이터베이스는 계속 갱신되므로 10~12단계(배포) 직전 재스캔 권고(§8) |
| SEC-27 | 오픈소스 라이선스 충돌 검토 | 각 패키지 라이선스 확인(이미 DEC-006/DEC-008이 확인한 근거 + 나머지 패키지 라이선스 상식 교차 확인) | 무료/비영리 서비스(DEC-005)와 배포 목적에 충돌하는 강한 카피레프트(GPL/AGPL) 없어야 함 | Django/Wagtail/django-storages/uvicorn = BSD-3-Clause, boto3 = Apache-2.0, gunicorn/whitenoise/python-dotenv = MIT, psycopg = LGPL-3(동적 링크 방식의 Python 임포트이며 이 서비스는 소프트웨어 자체를 재배포하지 않고 SaaS로 운영하므로 LGPL의 카피레프트 조건이 문제되지 않음), dj-database-url = BSD | PASS | 강한 카피레프트(GPL/AGPL) 없음, 상용/무료 배포 목적과 충돌 없음 |

### 4-5. 개인정보 컴플라이언스 / 규제 민감 도메인(규칙I) / AI-LLM(규칙J) / 외부 API 이용약관

| ID | 시나리오 | 실행 절차 | 예상 결과 | 실제 결과 | Pass/Fail | 비고 |
|----|----------|-----------|-----------|-----------|-----------|------|
| SEC-28 | 수집 최소화 원칙 | `subscribers/models.py` 필드 목록 vs 03 §5.6 | 이메일/동의시각/동의버전/마스킹 IP만 | 코드 확인 — 그 외 필드(이름/전화번호 등) 없음 | PASS | |
| SEC-29 | 보관기간·파기절차 구현 여부(설계서 §5.6 vs 실제) | `legal/migrations/0002_create_legal_pages.py`(방침 문구) + `subscribers/admin.py`(삭제 경로) 대조 | 방침이 명시한 "탈퇴 요청 시 운영자 하드 삭제" 절차가 실제로 구현되어 있어야 함 | 방침 본문에 정확히 그 절차가 명시되어 있고, `NewsletterSubscriberAdmin`이 추가/수정을 막고 목록/검색/삭제만 허용해 방침과 실제 구현이 정합 | PASS | 단, 이 삭제 경로 자체가 SEC-02(DEF-09-01)로 보호받지 못하는 로그인 화면 뒤에 있다는 점이 리스크를 가중시킴(교차 참조) |
| SEC-30 | 제3자 제공/위탁 고지 | `legal/migrations/0002_create_legal_pages.py` 본문 vs 03 §5.6 | Render/Neon/Cloudflare/GitHub 4개 벤더, 위탁 업무, 국외이전 여부 명시 | 본문에 4개 벤더명·위탁업무(호스팅/DB/이미지·백업저장/백업실행)·"미국 소재, 국외 이전" 명시 확인 | PASS | 실제 법률 자문은 설계서도 대신하지 않는다고 명시(§5.6), 초안임을 본문에도 명시 |
| SEC-31 | 동의 흐름(체크박스 필수, 미동의 시 거부) | `subscribers/forms.py` 확인(반복 검증 회피, 6/7단계가 이미 TC로 실측 PASS) | 동의 미체크 시 400 | 6/7단계 결과 인용 | PASS | |
| SEC-32 | **규칙I(규제 민감 도메인) — REQ-015 면책 문구 실제 노출 여부** | `legal/migrations/0002_create_legal_pages.py` TERMS_BODY 전문 확인 + 08단계 E2E-V07(`/terms/` 200) 재인용 | "금융/투자, 의료/건강, 법률, 보험" 면책 문구가 실제 게시된 페이지 본문에 정확히 존재해야 함(사용자 수가 적다는 이유로 축소 판단 금지) | 본문에 정확히 일치하는 문구 확인: "본 사이트는 금융/투자, 의료/건강, 법률, 보험 등 전문적인 자격이나 인허가가 필요한 분야에 대해 전문가의 조언이나 추천을 제공하지 않습니다." + 카테고리를 운영자만 생성 가능하게 하는 운영 통제까지 명시. 08단계 E2E-V07이 `/terms/` 200을 이미 실측 확인 | **PASS — 반영 확인됨** | traceability.md REQ-015 행과 정합. 규칙I 대응 미반영이었다면 Critical로 취급했을 것이나, 실제로는 1~2단계부터 3/6/7/8단계까지 일관되게 반영·검증되어 있음 |
| SEC-33 | **규칙J(AI/LLM 기능) 반영 여부** | `webapp/**/*.py` 전수 검색: LLM/챗봇/프롬프트/OpenAI/Anthropic API 호출 여부, `requirements.txt` AI SDK 포함 여부, 03 §5.7/decisions.md DEC-036 재확인 | 서비스 자체에 LLM 기능이 없다면 N/A(해당 없음)이어야 하며, 그 판단 자체가 최신 상태인지 재확인 | 코드 전수 검색 결과 LLM/챗봇/생성형 AI 관련 코드 0건, `requirements.txt`에 AI SDK 없음. 03 §5.7 "규칙 J 확인"이 REQ-025 Out-of-Scope를 재확인했고, DEC-036(08단계 이후 Tier 선언 시점)도 "AI/LLM 생성 기능도 명시적으로 비해당 확인됨(REQ-025)"을 재확인 | **N/A(해당 없음) — 근거와 함께 확인 완료** | 규칙J는 "서비스 자체가 LLM 기능을 포함"할 때만 적용되는 항목이며, 이 서비스는 포함하지 않음을 코드 레벨로 재확인했으므로 프롬프트 인젝션/출력 새니타이즈 점검 자체가 대상이 아님 |
| SEC-34 | 외부 데이터/API 이용약관 준수 | `webapp/**/*.py` 전수 검색: `requests`/`urlopen`/`httpx`/외부 콘텐츠 크롤링 흔적 | 외부 콘텐츠 API/크롤링을 사용한다면 03단계가 확인한 이용약관(호출 빈도 등)대로 구현되어야 함 | 코드에 외부 데이터/콘텐츠 API 호출이나 크롤링 로직 0건. `boto3`(R2)와 GitHub Actions API 호출은 인프라 벤더 SDK 정상 사용(각자의 공식 S3 호환 API/Actions 표준 기능)이며 "외부 데이터/콘텐츠"가 아니라 자사 인프라 운용 목적 | **N/A(해당 없음)** | 이 서비스는 콘텐츠를 운영자가 직접 작성하는 CMS이며, 외부 제3자 콘텐츠/데이터를 수집·재가공하지 않음(01/02단계 확인과 일치) |

---

## 5. 커버리지

- **에이전트 정의(`.claude/agents/09-security-auditor.md`) 최소 점검 항목 13개 전부** §4-1~§4-5에서 각각 1개 이상의 SEC-ID로 커버했다(체크리스트 대조표):
  1. 인증/인가 우회·권한경계 → SEC-01~10
  2. 인젝션/입력검증 → SEC-11~15
  3. 시크릿/자격증명 하드코딩·로그노출 → SEC-16, SEC-20~22
  4. 의존성 취약점(CVE) → SEC-24~26
  5. 의존성 환각(hallucinated dependency) → SEC-23
  6. 민감정보 저장/전송 암호화 → SEC-07(세션 쿠키 Secure), production.py HTTPS 강제(08단계 SYS-18/19 인용)
  7. 에러 메시지 정보노출 → SEC-18
  8. 설계서 보안원칙 vs 구현 불일치 → 전 SEC 항목이 03 §5 각 하위절과 1:1 대조하는 방식으로 수행됨(표 "실행 절차" 열에 03 §번호 명시)
  9. 개인정보 컴플라이언스 → SEC-28~31
  10. 오픈소스 라이선스 → SEC-27
  11. 외부 API 이용약관 준수 → SEC-34
  12. 규칙I(규제 민감 도메인) → SEC-32
  13. 규칙J(AI/LLM) → SEC-33
- **git 이력 커버리지**: `git log --all`(전체 6개 커밋) 전수 확인, 특히 사고 커밋 `3e594d7c`는 `--stat`/`--name-only`/`show <path>`로 프로젝트 고유 파일 전부 개별 열람.
- **08단계 Deferred 결함 4건 재평가**: DEF-001(WU-02, Low)/DEF-001(WU-05, Medium)/DEF-WU08IT-01(Low)/DEF-001(WU-10, Low, DEC-034)을 보안 관점으로 재검토 — 아래 §6-3.
- **커버되지 않은 부분과 사유**: (1) 실제 배포된 Render/Neon/R2/GitHub Actions 환경에서의 실네트워크 보안 스캔(예: 실제 TLS 인증서 체인, 실제 R2 버킷 ACL 확인)은 리소스가 아직 발급되지 않아 이번에도 수행 불가 — 10단계 이후 실측 필요(§8). (2) 실제 브라우저 기반 클라이언트 사이드 취약점(예: `newsletter.js`/`cookie-consent.js`의 DOM XSS 가능성)은 08단계와 동일하게 MCP(Playwright) 미연동으로 `jsdom` 기반 6단계 결과를 인용하는 수준에 머묾 — 코드 리뷰로 `innerHTML` 직접 대입 없음(텍스트 노드/속성 조작 위주)을 확인했으나 실브라우저 동적 스캔은 아님.

---

## 6. 결함(Defect) 목록

| ID | 설명 | 재현 절차 | 심각도(Critical/High/Medium/Low) | 상태(Open/Fixed/Deferred) | 조치 내용 |
|----|------|-----------|-----------------------------------|----------------------------|-----------|
| **DEF-09-01** | **`/django-admin/login/`(Django 기본 관리자 로그인)이 `core/admin_auth.py`의 IP 기반 무차별대입 방어를 완전히 우회한다.** `config/urls.py`는 `path("cms-admin/login/", RateLimitedLoginView.as_view(), ...)`로 Wagtail 로그인 경로만 `RateLimitedLoginView`(레이트리밋 적용)로 교체했으나, 같은 파일의 `path("django-admin/", admin.site.urls)`는 Django 기본 `AdminSite.login`(별개 뷰, 레이트리밋 미적용)을 그대로 노출한다. 두 경로는 **동일한 `auth_user` 자격증명 저장소**를 공유하며, 이 계정은 Wagtail 콘텐츠 전체 권한뿐 아니라 `subscribers.NewsletterSubscriber`(개인정보 파기절차의 유일한 삭제 경로, §5.6)까지 통제한다 | §3-1/§4-1 SEC-02에 기술한 대로 `webapp/.harness-tmp/venv_09_sec/`(임시 venv)에서 `django.test.Client`로 동일 IP·동일 계정에 11회 연속 잘못된 비밀번호 POST를 보내 재현: `/cms-admin/login/` → `[200×10, 429]`(정상), `/django-admin/login/` → `[200×11]`(**429 없음, 무제한 시도 가능**). 코드 근거: `webapp/config/urls.py` 16~23행, `webapp/core/admin_auth.py` 전체(레이트리밋이 `RateLimitedLoginView.dispatch()`에만 걸려 있고 `admin.site.urls`의 뷰 체인에는 전혀 연결되지 않음) | **High** | Open | **조치 없이 보고** — 감사자는 서비스 코드를 직접 수정하지 않는다(규칙F). 근본 원인은 5단계(WU-09, `webapp/core/admin_auth.py`/`webapp/config/urls.py`)와 3단계(`03-system-design.md` §5.1/DEC-009/DEC-029가 "어드민 마운트 경로"를 Wagtail 경로 단수로만 전제하고 `django.contrib.admin`이 별도로 마운트되어 있다는 사실을 명시하지 않음)에 있음. 권고 조치안(택1, 5단계 재작업 시 선택): (a) `is_rate_limited()`를 재사용하는 경량 미들웨어/데코레이터를 `/django-admin/login/` 경로에도 적용, (b) `admin.site.login`을 오버라이드해 `RateLimitedLoginView`와 동일한 카운터 공유, (c) 로그인 폼이 필요 없도록 `/django-admin/`를 이미 인증된 세션에서만 접근 가능하게 하고 self-service 로그인 폼 자체를 제거(운영자는 이미 `/cms-admin/login/`에서 인증하므로 Django 세션이 공유되어 재로그인이 애초에 불필요함을 확인함) |
| **DEF-09-02** | `.venv_wu09_it` 사고(커밋 `3e594d7c`, 13,320개 파일, `origin/PROD_SCH`까지 push됨)의 잔존 리스크 — **실제 시크릿 노출은 없음(§4-3 SEC-22로 확정)**이나, (a) git 이력 자체와 이미 push된 원격에는 여전히 더미 테스트 계정 해시(`wu09itadmin` 등, pbkdf2 해시)와 13k 파일 블로트가 남아있고, (b) 재발 방지 안전망(DEC-035가 도입한 `automation/git-hooks/pre-commit.sample`)이 **`.git/hooks/pre-commit`으로 실제 설치되어 있지 않음**(파일 존재하지 않음, 확인 완료)을 발견, (c) `automation/harness-janitor.sh`의 "레거시 패턴" 파일시스템 스캔이 저장소 루트(`-maxdepth 1`)만 보고 `webapp/` 하위는 스캔하지 않아 향후 유사 사고 재발 시 1차 방어선(파일시스템 스캔)에서 놓칠 수 있음(단, `.gitignore` 자체가 이미 `.venv*/` 와일드카드로 강화되어 주 방어선은 유효함, git status 기반 §3 보조 점검은 depth 제한 없음) | `git show 3e594d7c --stat/--name-only`, `git show 3e594d7c:<path>`(§4-3 SEC-22), `ls -la .git/hooks/pre-commit`(존재하지 않음 확인), `automation/harness-janitor.sh` 소스 검토(`-maxdepth 1` 확인) | **Low** | Deferred(과거 발생, 재발 방지는 이미 부분 적용) | 조치 없이 보고. 권고(11단계/운영 결정 필요, §8): (a) git 이력 재작성(BFG/`git filter-repo`)으로 블로트/더미 해시 제거는 **사용자 결정 사항**(작업 지시가 이미 "복구는 사용자 결정으로 보류 중"이라고 명시 — 이 감사가 임의로 수행하지 않음), (b) `cp automation/git-hooks/pre-commit.sample .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit` 실행 권고(설치 자체는 상태 변경이 크지 않으나 이 역시 감사자가 임의로 실행하지 않고 권고만 함), (c) `harness-janitor.sh`의 레거시 패턴 스캔을 저장소 루트뿐 아니라 1단계 하위 프로젝트 디렉터리(`webapp/` 등)까지 확장 검토 |
| **DEF-09-03** | `webapp/config/wsgi.py`/`asgi.py`/`manage.py` 3곳 모두 `os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")`로, 환경변수가 설정되지 않으면 **DEBUG=True + ALLOWED_HOSTS=["*"]인 개발 설정으로 조용히 폴백**하는 fail-open 패턴. 현재 실배포 경로(`render.yaml`이 `DJANGO_SETTINGS_MODULE=config.settings.production`을 `sync:false`가 아닌 고정값으로 항상 주입)에서는 실제로 트리거되지 않으나, 방어심층 원칙에는 위배됨 | `webapp/config/wsgi.py`/`asgi.py`/`manage.py`의 `setdefault(...)` 3곳 확인, `render.yaml`의 `DJANGO_SETTINGS_MODULE` 값이 `sync: false`가 아니라 고정 `value:`임을 대조 확인(즉시 트리거 가능성 낮음을 근거로 함께 기록) | **Low** | Open | 조치 없이 보고. 권고: `setdefault` 대신 환경변수 미설정 시 즉시 예외를 던지는 fail-loud 패턴으로 전환(예: `os.environ["DJANGO_SETTINGS_MODULE"]` 직접 접근으로 `KeyError` 유도), 또는 최소한 `dev`가 아닌 안전한 기본값(예: 즉시 실패하는 더미 모듈)으로 변경 — 11단계 운영문서 또는 후속 개선 백로그로 이관 |
| DEF-09-04 | (재확인, 심각도 변화 없음) GH Actions "Verify required secrets are present" 스텝이 공백 문자로만 구성된 시크릿을 "설정됨"으로 오인 | 08단계/DEC-034/`feature-WU-10-integration-test.md` IT-08과 동일 — 이번 단계는 재실행 없이 코드 재확인만 수행, `set -euo pipefail` 방어선이 여전히 유효함을 재확인 | Low | Deferred(기존과 동일) | 조치 없이 보고 — 기존 결정(DEC-034) 유지. `[ -z "${value// }" ]`류 트리밍 보강은 여전히 권고사항으로 남음 |

**결함 0건이 아님 — 근거**: §4의 SEC-02(DEF-09-01)가 로컬 재현으로 실증된 High 심각도 결함이므로, "결함 없음"으로 판정할 수 없다.

### 6-1. DEF-09-01의 비즈니스 영향 판단(자의적 축소 금지 원칙 적용)
- 이 사이트는 1인 운영(가정 A1)이며 슈퍼유저 계정이 콘텐츠 전체·구독자 개인정보 삭제권을 통제하는 **단일 장애점**임을 설계서(DEC-009)가 스스로 인정하고 있다. "이용자 수가 적어서 괜찮다"는 논리는 이 결함의 공격 표면(무차별대입 방어 완전 우회) 자체와는 무관하다 — 공격자는 이 사이트의 트래픽 규모와 무관하게 인터넷 전역에서 자동화 스캐너로 `/django-admin/login/`을 발견하고 무제한 시도를 할 수 있다.
- 03-system-design.md §5.1은 이 방어를 "Should가 아니라 **필수**로 취급한다"고 명시했다. DEF-09-01은 그 필수 통제를 완전히 무력화하므로, Medium으로 축소하지 않고 **High**로 확정한다(단, 이 결함 자체가 즉시 데이터 유출로 이어지는 것은 아니며 — 추가로 실제 비밀번호를 추측해야 하고, `AUTH_PASSWORD_VALIDATORS`(SEC-08)가 최소한의 품질을 강제하므로 — Critical이 아니라 High로 판단했다).

### 6-2. 설계서 보안 원칙과 실제 구현의 불일치 (요약)
- 03 §5.1 "어드민 마운트 경로를 기본값(`/admin/`)에서 변경해 자동화된 무차별 대입 시도 노출을 줄인다"는 원칙이 Wagtail 경로에만 적용되고 `django.contrib.admin`(여전히 `/django-admin/`이라는 추측 가능한 경로에 노출)에는 적용되지 않아 **불일치**(DEF-09-01의 설계 근거).
- 그 외 §5.2(입력검증/출력처리)/§5.3(뉴스레터)/§5.4(시크릿)/§5.5(전송/저장)/§5.6(개인정보)/§5.7(규칙J)은 실제 구현과 전부 일치함을 §4에서 확인했다.

### 6-3. 08단계 Deferred 결함 4건의 보안 관점 재평가
| 기존 ID | 원 출처 | 심각도 | 09단계 보안 관점 재평가 |
|---|---|---|---|
| DEF-001(WU-02, Category 빈 이름 ORM레벨 미검증) | `feature-WU-02-integration-test.md` | Low | 보안 영향 없음(데이터 품질 이슈, 인젝션/권한 우회 경로 아님) — 등급 변화 없음 |
| DEF-001(WU-05, JSON-LD 다중 Site 도메인 노출) | `feature-WU-05-integration-test.md` | Medium | 정보노출이지만 공개적으로 게시하려는 자사 도메인 정보이며, 운영 절차(Site 신규 생성 금지)를 지키는 한 트리거 안 됨 — 기밀성 침해 아님, 등급 변화 없음 |
| DEF-WU08IT-01(정적자산 카운팅 혼입) | `feature-WU-08-integration-test.md` | Low | 사용량 대시보드 참고지표 오염일 뿐 권한/기밀성/무결성 영향 없음 — 등급 변화 없음 |
| DEF-001(WU-10, DEC-034, 시크릿 공백값 경계) | `feature-WU-10-integration-test.md` | Low | §4-2 SEC-15/§6 DEF-09-04에서 재확인 — `set -euo pipefail`이 조용한 성공을 여전히 차단함, 등급 변화 없음 |

**결론**: 08단계 Deferred 결함 4건은 이번 보안 감사로 등급이 상향되지 않았다. 신규로 **High 1건(DEF-09-01)**, **Low 2건(DEF-09-03/DEF-09-04 신규 관찰, DEF-09-02는 과거 사고의 잔존리스크)**을 발견했다.

---

## 7. 테스트 환경 정리(Teardown) 확인 — 규칙 K

### 7-0. 작업 시작 전 점검
```
$ bash automation/harness-janitor.sh --check
[janitor] 점검 대상 저장소: C:/big21/vibe-coding/AI-AUTO-WORK
[janitor] .harness-tmp/ 는 비어있거나 없습니다 — 이상 없음.
[janitor] 잔여 임시 아티팩트 없음 — 다음 단계 진행 가능.
EXIT:0
```

### 7-1. 이번 테스트에서 생성한 임시 아티팩트 목록
- `webapp/.harness-tmp/venv_09_sec/` — DEF-09-01 재현 전용 신규 venv(`webapp/requirements.txt` clean install)
- `webapp/.harness-tmp/repro_django_admin_bypass.py` — 재현 스크립트(§4-1 SEC-01/SEC-02 근거)
- 재현 스크립트가 내부적으로 생성한 `django.test.utils` 테스트 DB(인메모리/임시 SQLite, `DiscoverRunner`가 자동 생성·자동 파기 — 별도 파일로 남지 않음)
- `%TEMP%/incident_db.sqlite3`(Windows 사용자 임시 디렉터리, 저장소 밖) — `3e594d7c` 커밋의 `db_wu09_integ_prodlike.sqlite3`를 `auth_user` 조회 목적으로 1회 추출한 파일. 저장소 내부가 아니므로 규칙K의 `.harness-tmp/` 대상은 아니며, "저장소 밖 세션 스크래치패드" 허용 범위로 사용

### 7-2. 위 아티팩트를 전부 `.harness-tmp/` 하위(또는 저장소 밖 스크래치패드)에서만 생성했는가 (규칙 K 1번)
**[x] 예.** 저장소 내부 임시 아티팩트는 전부 `webapp/.harness-tmp/` 하위에만 생성했고, 저장소 밖으로 나간 유일한 파일(`incident_db.sqlite3`)도 저장소 경로가 아닌 OS 임시 디렉터리였다.

### 7-3. 정리(삭제) 완료 여부
- `webapp/.harness-tmp/venv_09_sec/` 삭제 완료(`rm -rf`).
- `webapp/.harness-tmp/repro_django_admin_bypass.py` 삭제 완료.
- 재현 스크립트 실행 중 `manage.py`가 생성했을 수 있는 `webapp/db.sqlite3`(dev 폴백 파일) — 확인 결과 생성되지 않음(재현 스크립트가 `DiscoverRunner`의 임시 테스트 DB만 사용했기 때문).
- `%TEMP%/incident_db.sqlite3` 삭제 완료(`rm -f`).

### 7-4. 정리 후 `git status` 실행 결과 (그대로 첨부)
```
On branch PROD_SCH
Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   docs/harness/decisions.md
	modified:   docs/harness/feature-WU-10-integration-test.md
	modified:   docs/harness/traceability.md

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	docs/harness/08-full-system-test.md
	docs/harness/verify-log_08-full-system-test.md
	docs/harness/verify-log_feature-WU-10-integration-test.md

no changes added to commit (use "git add" and/or "git commit -a")
```
**해석**: 이번 09단계 세션이 시작되기 이전부터 존재하던 08단계/WU-10 산출물(`decisions.md`, `feature-WU-10-integration-test.md`, `traceability.md`, `08-full-system-test.md`, `verify-log_*`)만 표시되며, `webapp/` 아래에는 어떤 변경/미추적 파일도 없다 — 이번 세션이 만든 모든 임시 아티팩트가 흔적 없이 삭제되었음을 직접 증명한다. (이번 09단계가 새로 작성한 `docs/harness/09-security-audit.md`/`docs/harness/verify-log_09-security-audit.md`는 이 명령 실행 시점 이후 작성되었으므로 위 스냅샷에는 아직 나타나지 않는다 — 정상.)

### 7-5. 이번 테스트 도중 강제 중단(TaskStop 등)이 있었는가
**[x] 없음.**

### 7-6. Teardown 재확인
```
$ bash automation/harness-janitor.sh --check
[janitor] 점검 대상 저장소: C:/big21/vibe-coding/AI-AUTO-WORK
[janitor] .harness-tmp/ 는 비어있거나 없습니다 — 이상 없음.
[janitor] 잔여 임시 아티팩트 없음 — 다음 단계 진행 가능.
EXIT:0
```

**위 7-1~7-6이 모두 완료·확인되었다 — 단, 규칙K(Teardown)와 별개로 §9에서 판정하듯 DEF-09-01(High)로 인해 이 결과서 자체는 PASS가 아니다(Teardown 완료는 PASS의 필요조건이지 충분조건이 아님).**

---

## 8. 리스크 및 잔존 이슈

1. **DEF-09-01(High)이 해소되기 전까지 배포(10~12단계) 진행 금지.** 5단계(WU-09)로 되돌려 재작업 후 이 09단계를 재검증해야 한다(규칙F).
2. **`.venv_wu09_it` 사고의 git 이력/원격 잔존**(DEF-09-02) — 이력 재작성 여부는 사용자 결정 사항. 결정 전까지는 원격 저장소에 더미 테스트 계정 해시와 13k 파일 블로트가 계속 남아있는 상태다(실 시크릿 노출은 없음을 재확인했으므로 Critical 승격 사유는 아님).
3. **pre-commit 훅 미설치**(DEF-09-02의 일부) — DEC-035가 설계한 안전망이 아직 실제로 작동하지 않는 상태.
4. **fail-open dev 설정 폴백**(DEF-09-03) — 현재는 `render.yaml`이 가려주지만, 향후 배포 플랫폼을 바꾸거나 `render.yaml` 없이 수동 기동하는 경로가 생기면 즉시 위험이 현실화된다.
5. **실제 배포 환경 네트워크 보안 스캔 미실시** — 08단계와 동일 사유(리소스 미발급)로 10단계 이후 실측 필요(TLS 인증서, R2 버킷 ACL 실제 값, GitHub Actions 실행 로그 등).
6. **Content-Security-Policy(CSP) 헤더 부재** — 설계서가 요구하지 않아 결함은 아니지만, `mark_safe` 사용처(§4-2 SEC-12)가 존재하는 이상 CSP를 방어심층 계층으로 추가하는 것을 향후(11단계 운영문서 또는 post-MVP) 검토 권고.
7. **의존성 CVE 스캔은 시점 스냅샷**(2026-09-17) — 10~12단계(실배포) 직전 재스캔 권고, 특히 boto3/psycopg/gunicorn은 자주 릴리스되는 패키지다.
8. 08단계가 이미 인계한 KPI 미확정 항목(트래픽/전환율/응답성능 실측치)은 보안 이슈가 아니므로 이 결과서의 판정에 영향 없음(08단계 결론 유지).

---

## 9. 결론 및 판정

- [ ] PASS
- [ ] CONDITIONAL PASS
- [x] **FAIL** — **사유: DEF-09-01(High, `/django-admin/login/` 무차별대입 방어 완전 우회) 발견. 에이전트 정의 필수 원칙("Critical/High 결함이 있으면 절대 PASS로 판정하지 않는다")에 따라 10단계(배포테스트)로 handoff 불가.**

**재작업 요청 사항(규칙F, 근본원인 단계로 소급)**:
1. **5단계(WU-09) 재작업 대상**: `webapp/core/admin_auth.py`, `webapp/config/urls.py` — `/django-admin/login/`에도 `/cms-admin/login/`과 동등한(또는 공유하는) IP 기반 레이트리밋을 적용할 것. §6 DEF-09-01의 권고 조치안 (a)/(b)/(c) 중 택1 후 근거를 `decisions.md`에 신규 DEC로 기록.
2. **3단계(설계서) 재작업 대상**: `03-system-design.md` §5.1 — "어드민 마운트 경로 변경"이 Wagtail 경로 단수만을 의미하지 않고, `django.contrib.admin`을 포함해 **로그인 폼을 제공하는 모든 경로**에 동일한 방어가 적용되어야 함을 명시적으로 기술할 것(규칙F-1: 근본원인 발생 단계 소급 — DEC-009가 이 전제를 명시하지 않은 것이 근본 원인).
3. 재작업 완료 후 6→7→8단계 관련 회귀(특히 어드민 라우팅 회귀를 확인해온 기존 TC들, 예: `unit-01-test.md` TC-006b, `feature-WU-03-integration-test.md` IT-G2 등)를 다시 통과시키고, 이 09단계 보안검증을 **재실행**해 DEF-09-01이 Fixed로 전환되었음을 SEC-02와 동일한 방법(레이트리밋 실측 재현)으로 재확인해야 한다.
4. DEF-09-02/03/04(Low)는 blocking은 아니나, 11단계(운영 문서화) 또는 후속 백로그에 반드시 승계할 것 — 특히 DEF-09-02의 git 이력 재작성 여부는 사용자 승인이 필요한 별도 결정 사항이다.

---

## 10. 내부 검증 (최소 2회)

- Tier: Standard → 결함 유무와 무관하게 2회 이상 검증 필수(1차에서 결함이 나왔으므로 원칙 그대로 적용, 예외 소멸 조항 해당 없음 — 애초에 Standard라 처음부터 예외 대상이 아니었음).
- 1차 검증 결과 요약: 에이전트 정의(`09-security-auditor.md`)가 요구하는 13개 최소 점검 항목 전부를 §4-1~§4-5로 커버했는지 체크리스트 방식으로 자가 재검토 — 누락 없음을 확인. 다만 자가 재검토 도중 §4-1 SEC-02(`/django-admin/` 레이트리밋 우회)를 발견해 결함 목록에 반영(v0→v1).
- 2차 검증 결과 요약: "내가 이 사이트를 노리는 공격자라면 어디를 먼저 찌를까"라는 역할전환 관점으로 재검토 — (1) 이미 발견한 DEF-09-01 외에 다른 제2의 인증 진입점(예: Django REST Framework API, GraphQL 엔드포인트)이 있는지 `config/urls.py`/`INSTALLED_APPS` 재확인 → 없음(REST/GraphQL 미도입 확인). (2) 오픈 리다이렉트/SSRF 추가 표면 재검토 → `_safe_next` 외 사용자 입력이 URL/네트워크 호출에 흘러드는 지점 없음 확인. (3) 세션 고정/쿠키 스코프 재검토 → Django 기본 동작에 의존, 커스텀 로직 없어 추가 결함 없음. (4) Teardown(§7)의 `git status`가 세션 시작 전 상태와 정확히 비교 가능한 형태로 첨부됐는지, DEF-09-01 재현 절차가 실제로 재현 가능한 수준(파일/라인 인용 + 실행 결과)으로 기록됐는지 재확인 → 충족. 결과: 1차에서 발견한 DEF-09-01(High) 외 신규 Critical/High 없음, 기존 발견한 Low 3건은 그대로 유지.
- 검증 로그 파일 경로: `docs/harness/verify-log_09-security-audit.md`

## 절차 흐름 (참고용 다이어그램)

```mermaid
flowchart TD
    A["08단계 PASS + 전체 코드베이스"] --> B["OWASP/의존성/인증인가/민감정보 점검"]
    B --> C["개인정보 컴플라이언스 + 규제도메인 REQ-ID 반영 점검"]
    C --> D{Critical/High 결함?}
    D -->|Yes| E["PASS 불가 → Fixed 요청 후 재검증"]
    E --> B
    D -->|No| F["내부검증 1차/2차: 공격자 관점 재검토"]
    F -->|결함| B
    F -->|PASS| G["09-security-audit.md 확정<br/>10단계로 handoff"]
```

**이번 실행 결과는 위 다이어그램의 `D -->|Yes| E` 분기에 해당한다 — DEF-09-01(High)로 인해 PASS 불가, 5단계(WU-09)/3단계로 회귀 후 재검증 필요.**

---

## 재작업 라운드 2(DEF-09-01) 재검증

> **재검증 경위**: 원본 9단계(위 §1~§10, 2026-09-17)가 **FAIL** 판정했다 — `DEF-09-01`(High): `/django-admin/login/`(Django 기본 관리자)에 무차별대입 방어가 전혀 없어 동일 IP로 11회 연속 로그인 실패를 보내도 전부 `200`(429 없음)이었다(§6, §9). 이후 규칙F 재작업 체인이 진행되어 3단계(`03-system-design.md` §5.1 v1.3, DEC-040)가 "두 진입점(Wagtail `/cms-admin/login/` + Django 기본 `/django-admin/login/`) 모두 동일 IP 카운터를 공유하며 방어"를 채택했고, 5단계(WU-09 재작업 라운드 2, DEC-041)가 `webapp/core/admin_auth.py`에 `RateLimitedAdminLoginView`를 신설하고 `webapp/config/urls.py`에 `django-admin/login/` 오버라이드를 추가했다고 주장했다. 6단계(`units/unit-09-test.md` "재작업 라운드 2 재검증" 절)와 7단계(`feature-WU-09-integration-test.md` "재작업 라운드 2(DEF-09-01) 재검증" 절, §5.6 구독자 하드삭제 E2E 포함)가 각각 PASS로 확정했다고 보고했다.
>
> **이 절은 5·6·7단계의 PASS 주장을 그대로 인용/신뢰하지 않고, 9단계가 처음부터 독립적으로 재현한 결과다.** 원본 §1~§10의 FAIL 판정과 재현 절차·근거는 위에 그대로 보존했으며, 이번 절은 그 아래에 append했다.
>
> **작업 대상 경로 재확인(투명성 기록, 원본 §1과 동일 절차 반복)**: 이번 재검증 세션도 작업 지시가 프로젝트 루트를 `C:\big21\vibe-coding\AI-AUTO-WORK`로 명시했으나 환경 기본 작업 디렉터리는 별개 프로젝트(`C:\big21\vibe-coding\STOCK-ANALYZER-KR`)를 가리키고 있었다. 착수 전 두 경로를 모두 직접 조회해, `AI-AUTO-WORK`에 이 지시가 요구하는 실제 산출물(`docs/harness/09-security-audit.md`, `decisions.md`의 DEC-039~041, `webapp/core/admin_auth.py`, `webapp/config/urls.py` 등)이 전부 실재함을 대조한 뒤에만 절대경로 기준으로 작업했다.

### R2-1. 입력 문서 재확인

- `docs/harness/09-security-audit.md`(원본 §4-1 SEC-02, §6 DEF-09-01, §9 FAIL 판정과 재현 절차) — 원 공격 시나리오: 동일 IP로 `/django-admin/login/`에 11회 연속 POST, 원본 결과 `[200×11]`.
- `docs/harness/decisions.md` DEC-039(결함 발견·재작업 범위 확정) / DEC-040(3단계, "두 진입점 모두 방어" 옵션 채택, 카운터 공유 근거) / DEC-041(5단계, `ADMIN_ACCESS_GUIDE.md` 갱신 범위 포함 여부·회귀 테스트 배치 판단) 전문을 재열람.
- `docs/harness/03-system-design.md` §5.1(v1.3, DEC-009/029/039/040) — 관리자 진입점 인벤토리, 채택 옵션(옵션2, 옵션1 기각 근거), 구현 지침 1~5.
- `docs/harness/units/unit-09-note.md` "재작업 라운드 2" 절(AC23~30), `units/unit-09-test.md` "재작업 라운드 2 재검증" 절(6단계 PASS, AC23~30 8/8 + 원본 AC1~22 회귀), `units/verify-log_unit-09-test.md` "재작업 라운드 2" 절(6단계 내부검증 2회).
- `docs/harness/feature-WU-09-integration-test.md` "재작업 라운드 2(DEF-09-01) 재검증" 절(7단계 PASS, IT-R2-01~09 + IT-R2-E2E-1~4 구독자 하드삭제 E2E + IT-R2-05/06 XFF·CSRF 경계), `docs/harness/verify-log_feature-WU-09-integration-test.md` 해당 절.

### R2-2. 실제 코드 변경분 직접 검토

`webapp/core/admin_auth.py`(133줄)와 `webapp/config/urls.py`(55줄) 전문을 직접 읽었다(요약 재기술 없이 원문 대조).

- `is_rate_limited(ip)`(기존 DEC-029 함수, 미변경)는 `cache.incr()` 기반으로 IP만을 캐시 키(`core:admin_login:ratelimit:{ip}`)로 사용해 URL을 구분하지 않는다 — 설계(DEC-040)가 요구한 "공유 카운터"가 코드 구조상 당연히 성립함을 확인(별도 구현이 필요 없는 재사용 방식이 맞음).
- 신설된 `RateLimitedAdminLoginView(View)`는 `dispatch()`에서 POST일 때만 `is_rate_limited(ip)`를 확인하고, 통과 시 `admin.site.login(request, *args, **kwargs)`에 그대로 위임한다(뷰 자체를 재구현하지 않음, 04-ux-design.md §0 원칙 준수).
- `config/urls.py`는 `path("django-admin/login/", RateLimitedAdminLoginView.as_view(), name="admin_login")`을 `path("django-admin/", admin.site.urls)`**보다 먼저** 등록한다(17~23행) — Django URL 리졸버는 등록 순서대로 첫 매치를 채택하므로, `admin.site.urls`가 내부적으로 여전히 등록하는 동일 리터럴 `login/` 서브라우트는 실제 요청에서는 도달 불가능하고(의도된 설계) `reverse("admin:login")`으로 계산되는 문자열(`django-admin/login/`)은 우리 오버라이드와 동일해 내부 리다이렉트가 깨지지 않음을 코드 레벨로 확인.

### R2-3. 독립 재현 — 원본 SEC-02 시나리오 그대로 재실행

로컬 동적 재현(신규 venv, 규칙K 준수): `webapp/.harness-tmp/venv_09_sec_round2/`(Python 3.13, `webapp/requirements.txt` clean install, `pip install` 성공). `django.test.Client`/`RequestFactory`/`django.test.override_settings`로 독립 스크립트(`.harness-tmp/independent_repro_round2.py`, 검증 직후 삭제)를 새로 작성해 5·6·7단계가 이미 작성해둔 테스트(`core/tests.py`)에 대한 신뢰 없이 별개로 재현했다. 추가로 `manage.py test core.tests.AdminLoginRateLimitTests core.tests.DjangoAdminLoginRateLimitTests core.tests.SharedAdminRateLimitCounterTests`(기존 15개 테스트)도 별도로 실행해 교차 확인했다.

| 시나리오 | 방법 | 기대값 | 실제 결과 | 판정 |
|---|---|---|---|---|
| **원본 SEC-02 재현**: 동일 IP `/django-admin/login/` 11회 연속 POST | 신선한 `Client()`, `REMOTE_ADDR` 고정, 매회 다른 오답 비밀번호 | 1~10회 `!=429`, 11번째 `429`(원본은 `[200×11]`이었음) | `[200,200,200,200,200,200,200,200,200,200,429]` | **PASS — DEF-09-01 Fixed 확인** |
| 기존 회귀 테스트 3클래스(15건) 독립 재실행 | `manage.py test`(dev, 신규 venv) | 전부 OK | `Ran 15 tests in 27.104s ... OK` | PASS |
| **카운터 분할 우회 시도**: `/cms-admin/login/` 6회 + `/django-admin/login/` 6회(동일 IP, 합계 12회) | 동일 `Client()` | 합산 10회 초과 시점(11번째 누적 요청)에서 `429`, 두 URL 어느 쪽이든 차단 | wagtail 6회 전부 200 → django 1~4회차 200 → django 5회차(누적 11) `429` → django 6회차(누적 12) `429` | **PASS — 예산 2배 우회 불가, 공유 카운터 확인** |
| **XFF leftmost 스푸핑(CSRF 무효 트래픽, 전체 미들웨어 스택)**: `X-Forwarded-For: <매회 변경>, 203.0.113.200`(rightmost 고정) | `override_settings(MIDDLEWARE=[XFF, ...전체 production 스택])`, `Client(enforce_csrf_checks=True)`, CSRF 토큰 없이 POST 15회 | 전부 `403`(CSRF 무효라 자격증명 시험 자체가 불가능, 429 여부는 무관) | `[403×15]` | PASS — 전역 `CsrfViewMiddleware`가 뷰 호출 전에 차단, 자격증명 추측 불가 |
| **XFF rightmost 자체도 매회 변경(엣지 부재 가정 대조군)** | 위와 동일 스택, `X-Forwarded-For` 값 자체를 매회 다르게 | 전부 `403`(위와 동일 이유) | `[403×15]` | PASS(참고용, 실배포는 Render 엣지가 rightmost를 통제한다는 03 §5.5.4 전제 하에 안전) |
| **XFF leftmost 스푸핑(유효 CSRF, 전체 미들웨어 스택)** — 신규 라우트에 대해 최초로 직접 확인(기존 `core/tests.py`의 XFF 테스트는 Wagtail 경로만 커버, §R2-6 참고) | 유효 CSRF 토큰 획득 후 `X-Forwarded-For: <매회 변경>, 203.0.113.201`(rightmost 고정)로 11회 POST | 1~10회 `!=429`, 11번째 `429`(leftmost 조작으로 예산 우회 불가) | `[200×10, 429]` | **PASS — 신규 라우트에서도 rightmost 기준 카운팅이 정확히 동작, 회귀 없음** |
| **고정창 만료 여부(영구 DoS 가능성 점검)** | `cache.incr()`이 최초 `cache.set()`의 TTL을 연장하는지 별도 프로브(5초 TTL)로 직접 확인 | TTL이 매 `incr()`마다 갱신되지 않고 최초 설정 시점 기준으로 고정 만료되어야 함(연장되면 공격자가 영구 잠금 가능) | 5초 경과 시점에 `cache.get()`이 `None`(만료), 이후 재요청 시 카운터가 1부터 재시작 — 반복 `incr()` 호출에도 TTL이 연장되지 않음을 직접 확인 | **PASS — 영구 잠금(자기서비스거부) 불가능, 창(15분)은 항상 고정 만료** |
| 정상 관리자 자기서비스거부(self-DoS) 트레이드오프 재확인 | 동일 IP에서 존재하지 않는 계정으로 11회 노이즈 발생시킨 뒤, 같은 IP로 실제 계정 로그인 시도 | `429`(IP 기준이므로 계정과 무관하게 차단 — 기존에 이미 승인된 트레이드오프, DEC-029) | `429` | **정보성(결함 아님)** — `core/admin_auth.py` 모듈 docstring(25~30행)과 `03 §5.1` v1.3이 이미 명시한 의도된 설계. 이번 라운드가 새로 만든 리스크가 아니라 기존에 Wagtail 쪽에만 있던 트레이드오프를 Django 기본 관리자 경로로 동일하게 확장 적용한 결과임을 재확인 |

**재현에 사용한 venv/스크립트는 규칙K에 따라 `webapp/.harness-tmp/` 하위에서만 생성했고, 검증 직후 삭제했다.** 삭제 후 `automation/harness-janitor.sh --check` 재실행 결과 `[janitor] 잔여 임시 아티팩트 없음 — 다음 단계 진행 가능.`(EXIT 0)을 확인했다.

### R2-4. 신규 취약점 점검(작업 지시 2번 — 이번 수정이 새 결함을 만들지 않았는가)

1. **레이트리밋 카운터 우회(공격자 관점)**: §R2-3 표의 "카운터 분할 우회 시도"·"XFF 스푸핑" 3종 시나리오로 직접 검증한 결과, 어떤 경로로도 IP당 10회 예산을 초과해 자격증명을 시험할 수 있는 방법을 찾지 못했다.
2. **`XForwardedForMiddleware`와의 상호작용(WU-01)**: `config/middleware.py`(11~32행)를 재열람 — rightmost 값만 `REMOTE_ADDR`로 채택하는 기존 설계(03 §5.5.4)가 신규 `RateLimitedAdminLoginView`에도 동일하게 적용됨을 §R2-3 "XFF leftmost 스푸핑(유효 CSRF)" 케이스로 직접 확인했다(기존 `core/tests.py`는 이 조합을 Wagtail 경로에만 뒀었다 — 커버리지 공백을 이번 재검증이 메움, §R2-6 참고). rightmost 자체가 공격자 통제 하에 있다면(엣지가 없는 경우) 당연히 스푸핑이 가능하지만, 이는 `render.yaml`/03 §5.5.4가 이미 전제하는 "Render 단일 신뢰 홉" 인프라 계층의 문제이며 이번 애플리케이션 코드 변경과 무관하다(기존 WU-01/WU-07 레이트리밋도 동일 전제를 공유).
3. **영구 잠금(DoS화) 가능성**: §R2-3 "고정창 만료 여부"로 직접 반증 — `cache.incr()`가 TTL을 연장하지 않으므로 공격자가 아무리 요청을 반복해도 최초 요청 시점 기준 15분 뒤 반드시 자동 해제된다. 새로운 DoS 벡터 없음.
4. **인젝션/시크릿/에러노출**: `admin_auth.py`/`urls.py` 두 파일 모두 사용자 입력을 그대로 SQL/커맨드에 넘기는 지점이 없고(ORM/Django 내장 `admin.site.login()`에 전적으로 위임), 429 응답 본문("로그인 시도가 너무 많습니다...")은 하드코딩된 고정 문자열로 사용자 입력을 반영하지 않아 XSS 표면이 없다. 두 파일 어디에도 시크릿/자격증명 하드코딩 없음(재확인).
5. **CSRF**: 전역 `CsrfViewMiddleware`(순서 불변, `config/settings/base.py` 55~71행 MIDDLEWARE 미변경 확인)가 여전히 두 로그인 경로 모두를 보호하며, `RateLimitedAdminLoginView`가 위임하는 `admin.site.login()`도 Django 표준 `LoginView`의 `csrf_protect` 데코레이터를 그대로 상속받아 이중으로 보호된다(§R2-3 "XFF leftmost 스푸핑(CSRF 무효 트래픽)" 케이스로 실측).
6. **의존성**: `git diff`로 `webapp/requirements.txt` 변경 여부를 확인한 결과 **변경 없음**(diff 0줄) — 이번 재작업이 신규 외부 패키지를 도입하지 않았음을 직접 확인(`admin_auth.py` 20~23행 docstring의 "새 패키지를 도입하지 않는다"는 주장과 일치). 따라서 의존성 CVE/의존성 환각(slopsquatting) 재스캔 대상 추가 없음 — 원본 §4-3의 9개 패키지 전수 확인 결과가 그대로 유효하다.

### R2-5. 기존 결함 재확인(작업 지시 3번)

| 결함 | 원본 등급 | 이번 라운드 관련성 | 재확인 결과 |
|---|---|---|---|
| DEF-09-02(pre-commit 훅 미설치, `.venv_wu09_it` 사고 잔존리스크) | Low | 무관 | `.git/hooks/pre-commit` 파일 없음(원본과 동일 상태). 등급/상태 변화 없음, 그대로 유지 |
| DEF-09-03(`wsgi.py`/`asgi.py`/`manage.py`의 fail-open dev 폴백) | Low | 무관 | 3곳 모두 `os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")` 그대로. 등급/상태 변화 없음 |
| DEF-09-04(GH Actions 공백 시크릿 오탐) | Low | 무관 | 이번 라운드가 `.github/workflows/`를 건드리지 않음(diff 없음). 기존 결정(DEC-034) 유지 |

세 건 모두 이번 재작업 범위(`core/admin_auth.py`, `config/urls.py`)와 상호작용이 없고, 재현 결과도 원본과 동일해 등급 상향/하향 없이 그대로 승계한다.

### R2-6. 회귀 점검(작업 지시 4번 — CSRF/XSS/SQLi/민감정보/의존성)

- **CSRF/XSS/SQLi**: §R2-4-4/5에서 직접 재확인, 회귀 없음.
- **민감정보 노출**: 429 응답 본문·로그 어디에도 시도된 사용자명/비밀번호를 반영하지 않음(코드 재확인, `HttpResponse`는 고정 문자열만 반환). WU-08 `RequestMetricsMiddleware`가 집계하는 사용량 카운터도 요청 수치만 집계하며 자격증명 페이로드를 저장하지 않음(기존 §4-2 SEC-1x대 판정 유지, 이번 라운드가 그 미들웨어 자체를 건드리지 않음).
- **의존성**: §R2-4-6에서 확인한 대로 변경 없음.
- **테스트 커버리지 공백 발견(정보성, 결함 아님)**: 기존 `core/tests.py::AdminLoginRateLimitTests.test_x_forwarded_for_rightmost_value_used_as_client_ip`는 Wagtail 경로(`RateLimitedLoginView`)만 XFF 시나리오를 검증하고, `DjangoAdminLoginRateLimitTests`/`SharedAdminRateLimitCounterTests`에는 대응하는 XFF 테스트가 없다. 실제 동작은 §R2-3에서 직접 재현해 문제 없음을 확인했으므로 결함으로 등록하지는 않으나, **11단계(운영 문서화) 또는 후속 백로그에 "신규 라우트에 대한 XFF 회귀 테스트 추가" 권고로 승계**한다(테스트 스위트 자체의 완결성 개선 사항, 시스템 결함 아님).

### R2-7. 규제/개인정보 컴플라이언스 교차 확인(원본 SEC-29 재확인, §5.6)

원본 §4-4 SEC-29가 이미 "탈퇴 요청 시 운영자 하드 삭제" 절차의 유일한 실행 경로(`NewsletterSubscriberAdmin`)가 이번에 레이트리밋을 새로 적용한 `/django-admin/` 뒤에 있다고 교차 참조했다. 7단계 라운드 2(IT-R2-E2E-1~4)가 로그인→목록조회→실제 삭제 실행(`NewsletterSubscriber.objects.filter(id=...).exists() == False`로 DB 소멸까지 실측)을 E2E로 이미 검증했음을 문서 대조로 확인했다(9단계가 이 삭제 E2E 자체를 중복 재실행하지는 않음 — 규칙B, 이미 실측된 것을 반복하지 않음). 이 경로가 여전히 새 레이트리밋 뷰(§R2-3에서 정상 로그인 확인됨) 뒤에서 정상 도달 가능함을 코드(§R2-2, `dispatch()`가 통과 시 `admin.site.login()`에 위임)로 재확인했다 — §5.6 파기절차와 실제 구현의 일치는 이번 라운드로 훼손되지 않았다.

### R2-8. Teardown(규칙K)

- `webapp/.harness-tmp/venv_09_sec_round2/`, `webapp/.harness-tmp/independent_repro_round2.py` — 검증 직후 삭제 완료.
- `automation/harness-janitor.sh --check` 재실행: `[janitor] .harness-tmp/ 는 비어있거나 없습니다 — 이상 없음.` / `[janitor] 잔여 임시 아티팩트 없음 — 다음 단계 진행 가능.`(정상 종료)
- `git status --porcelain`으로 이번 라운드가 문서(`docs/harness/*.md`) 외에 `webapp/` 소스를 수정하지 않았음을 확인(순수 검증/문서 작업만 수행, 코드는 읽기 전용으로만 다뤘다).

### R2-9. 결론 및 최종 판정

- [x] **PASS** — 10단계(배포테스트) handoff 가능
- [ ] CONDITIONAL PASS
- [ ] FAIL

**판정 근거**:
1. 원본 9단계가 실측 재현했던 정확한 공격 시나리오(`/django-admin/login/` 동일 IP 11회 연속 POST)를 이번 라운드가 처음부터 새로 만든 독립 venv/스크립트로 재실행한 결과 `[200×10, 429]`로 **명확히 차단됨을 확인**했다(§R2-3) — 원본의 `[200×11]`과 대조된다. **DEF-09-01(High) Fixed 확정.**
2. 두 로그인 경로에 시도를 분산해 예산을 2배로 늘리는 우회, X-Forwarded-For 조작을 통한 카운터 우회, 반복 요청을 통한 영구 잠금(DoS) 유발을 각각 직접 시도했으나 전부 실패함을 확인했다 — **이번 수정 자체가 새로운 Critical/High/Medium 취약점을 만들지 않았다**(§R2-4).
3. DEF-09-02/03/04(Low)는 이번 재작업과 무관한 영역이며 상태 변화 없이 그대로 유지된다(§R2-5).
4. 이번 변경 파일(`admin_auth.py`/`urls.py`)의 CSRF/XSS/SQLi/민감정보/의존성 관점 회귀를 재확인했고, 이상 없음을 확인했다(§R2-6). 의존성은 이번 라운드가 `requirements.txt`를 전혀 건드리지 않아 신규 CVE·의존성 환각 스캔 대상이 없다.
5. §5.6 개인정보 파기절차(구독자 하드삭제)의 유일한 실행 경로가 새 레이트리밋 뷰 뒤에서도 정상 도달 가능함을 문서·코드 교차로 재확인했다(§R2-7, 실제 E2E 실행은 7단계 라운드 2가 이미 실측).
6. 신규 Critical/High 결함 0건. 테스트 커버리지 공백 1건(정보성, §R2-6)을 후속 권고로 남겼을 뿐 결함으로 등록하지 않았다.
7. Teardown 완료(§R2-8, 규칙K).

**DEC-039가 정한 재검증 체인(3→5→6→7→9)이 이번 절로 완료된다. 10단계(배포테스트)로 handoff 가능한 상태로 확정한다.**

### R2-10. 내부 검증(최소 2회)

- **1차 검증(작성자 관점 자가 재검토)**: 작업 지시가 요구한 4가지 항목(① 원 공격 시나리오 재현 ② 신규 취약점 미도입 확인(카운터 우회/XFF 상호작용/DoS화) ③ 기존 Low 결함 재확인 ④ CSRF/XSS/SQLi/민감정보/의존성 회귀 확인)이 §R2-3~§R2-6에 전부 대응됐는지 재대조 — 누락 없음. 5·6·7단계의 PASS 주장을 문서로만 인용하지 않고 §R2-3 표의 모든 행을 이번 세션이 새로 만든 독립 스크립트로 직접 실행해 수치를 얻었는지 재확인 — 전부 직접 실행됨(문서 인용은 §R2-1/§R2-5/§R2-7의 교차 확인 목적에 한정). 결함 0건.
- **2차 검증("내가 이 사이트를 노리는 공격자라면 어디를 먼저 찌를까" 역할전환 관점)**: 1차가 놓쳤을 수 있는 공격 표면을 재검토했다.
  1. **"레이트리밋 자체를 악용해 정당한 관리자를 의도적으로 봉쇄할 수 있는가(reverse DoS)?"** → 가능하다(§R2-3 self-DoS 행). 다만 이는 이번 라운드가 새로 만든 리스크가 아니라 DEC-029가 Wagtail 경로에 대해 이미 승인한 기존 트레이드오프(계정 잠금보다 자기서비스거부 쪽이 안전하다는 1인 운영 전제)를 Django 기본 관리자 경로로 동일하게 확장한 것뿐이며, `admin_auth.py` 모듈 docstring과 `03 §5.1` v1.3에 이미 명시적으로 문서화돼 있다 — 신규 결함으로 등록하지 않았다.
  2. **"429 응답 자체가 공격자에게 유용한 정보(예: 계정 존재 여부)를 흘리는가?"** → 429는 사용자명 존재 여부와 무관하게 IP 기준으로만 발생하므로(§R2-3 "정상 관리자 self-DoS" 케이스가 존재하지 않는 계정으로도 카운트가 증가함을 보여줌) 계정 열거(enumeration) 공격에 악용할 정보를 제공하지 않는다.
  3. **"이 URL 오버라이드가 Django 관리자의 다른 내부 리다이렉트(로그아웃, 권한 없음 페이지 등)를 깨뜨려 인가 우회를 만드는가?"** → `config/urls.py` 주석과 코드(§R2-2)로 재확인한 결과, `reverse("admin:login")`이 계산하는 문자열이 우리 오버라이드 경로와 동일해 내부 리다이렉트 로직 자체는 전혀 변경되지 않는다 — URL 매칭 우선순위만 바뀔 뿐 이름 기반 reverse/redirect 체인은 원본과 동일하다. 새로운 인가 우회 경로 없음.
  4. **"제3의 로그인 진입점이 이번 라운드로 새로 생기지 않았는가?"** → `webapp/` 전체에서 로그인/인증 관련 뷰를 재검색해 `RateLimitedLoginView`/`RateLimitedAdminLoginView` 외 추가 진입점이 없음을 재확인(DRF/GraphQL 미도입 상태 유지).
  5. **"문서만 보고 10단계 에이전트가 추가 질문 없이 착수할 수 있는가?"** → §R2-9에 최종 판정과 handoff 가능 상태를 명시했고, 문서 최상단 배너로 원본 FAIL과 최신 PASS를 명확히 구분했다.
  - 결과: 1차·2차 모두 신규 Critical/High/Medium 결함 없음. self-DoS 트레이드오프 1건은 기존에 이미 승인된 설계의 연장으로 재확인, 테스트 커버리지 공백 1건은 정보성 권고로 유지.
- 검증 로그 파일 경로: `docs/harness/verify-log_09-security-audit.md`("재작업 라운드 2" 절, append)

**이번 라운드 실행 결과는 원본 §10 다이어그램의 `D -->|Yes| E` → 재작업 → 재검증 루프를 완주해 `F -->|PASS| G`(09-security-audit.md 확정, 10단계로 handoff)에 도달한 것에 해당한다.**
