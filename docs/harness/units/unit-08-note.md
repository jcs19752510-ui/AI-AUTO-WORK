# WU-08 — 무료 티어 대응(콜드스타트 UX, 사용량 모니터링) 구현 노트

- 작성 에이전트: `05-unit-developer` (WU-08, 02-planning.md §9)
- 입력: `docs/harness/03-system-design.md`(v1.2, PASS, 특히 §1.2/§4/§6.2/§6.3/§7.2/§7.4), `docs/harness/04-ux-design.md`(v1.2, PASS, 콜드스타트 UX 설계), `docs/harness/decisions.md`(DEC-001~025), `docs/harness/units/unit-01-note.md`, `docs/harness/units/unit-04-note.md`, `docs/harness/feature-WU-07-integration-test.md`(IT-20, gunicorn 단일 워커 확인)
- 작성일: 2026-09-17
- 대상 REQ-ID: REQ-011(콜드스타트 UX), REQ-012(사용량 모니터링/유료전환 기준)

---

## 1. 구현 범위

### 1.1 콜드스타트 UX(REQ-011) — 신규 구현 없음, 회귀 확인만

`webapp/config/templates/partials/footer.html`에 04-ux-design.md §2 "콜드스타트 UX 설계"가 지시한 고정 안내 카피("⚡ 무료 인프라로 운영 중이라...")가 WU-04에서 **이미 완전히 구현**되어 있음을 확인했다(unit-04-note.md §1.7과 일치). 별도 라우트/DB 필드 없이 정적 템플릿 카피 + `<details>/<summary>`로 구현되어 있어 04번 설계가 명시한 "실시간 콜드스타트 화면은 아키텍처적으로 불가능하다"는 결론과 정확히 일치한다. 이번 WU에서는 코드를 건드리지 않고 `GET /`를 실제로 렌더링해 카피가 응답 본문에 포함되는지 회귀 확인만 했다(§3).

추가로, 03 §4가 `core` 앱 책임으로 지정한 `GET /healthz`(얕은 헬스체크, REQ-011/012 공용— 콜드스타트/장애 구분 목적)를 신규 구현했다(§1.2).

### 1.2 사용량 모니터링(REQ-012) — 신규 구현

```
webapp/
  core/
    middleware.py          (신규) RequestMetricsMiddleware — 요청 1건당 응답시간을 재서 monitoring.record_request()에 위임
    monitoring.py           (신규) 일자별(KST) 요청수/응답시간 집계(LocMemCache), 03 §6.3 유료전환 4대 기준 상수(UPGRADE_CRITERIA), get_usage_snapshot()
    views.py                 (수정) healthz(신규), usage_dashboard(신규, superuser_required), robots_txt(기존, 변경 없음)
    urls.py                  (수정) /healthz 라우트 추가
    wagtail_hooks.py        (신규) Wagtail 어드민에 /cms-admin/usage/ 라우트 + 사이드바 메뉴 항목("사용량 모니터링") 등록
    templates/core/usage_dashboard.html  (신규) 대시보드 화면
    apps.py                  (수정) 앱 docstring — WU-08 책임 범위 명시, "콜드스타트 안내 뷰"/"SiteSettings"가 왜 이 WU에서도 코드가 없는지 근거 보강
  config/
    settings/base.py         (수정) MIDDLEWARE 맨 앞에 core.middleware.RequestMetricsMiddleware 추가
    settings/production.py   (수정) ADMINS/MANAGERS/EMAIL_*(SMTP)/SERVER_EMAIL 추가(03 §7.2, Django 기본 LOGGING의 AdminEmailHandler 재사용)
  render.yaml                 (수정) gunicorn --workers 1 명시 고정(DEC-026), healthCheckPath: /healthz 추가, DJANGO_ADMIN_EMAIL/EMAIL_* env 자리 추가
docs/harness/decisions.md      DEC-026(워커 수 명시 고정), DEC-027(모니터링 장치가 03 §6.3의 "배치잡 없음" 결정과 상충하지 않는 이유) 추가
docs/harness/traceability.md   REQ-011/REQ-012 행 갱신
```

#### 설계 판단 근거 (DEC-027 요지)

03 §6.3은 "별도의 자체 사용량 추적 배치 잡은 두지 않는다"고 명시했다. 이번 WU 작업 지시는 "관리자 대시보드로 최근 요청 수/응답시간 등 기본 지표를 노출"을 요구했는데, 문언만 보면 상충하는 것처럼 보일 수 있어 다음과 같이 해석하고 규칙F(설계서 재작업)를 트리거하지 않았다: **03 §6.3이 거부한 것은 "배치 잡"(주기적으로 스스로 깨어나 Render/Neon 외부 API를 폴링하는 별도 스케줄 작업)이고, 이번에 만든 것은 이미 발생하는 요청 처리 경로에 얹은 인메모리 카운터(미들웨어)다** — 새 프로세스/새 서비스/새 스케줄이 전혀 없다. 자세한 근거는 DEC-027과 `core/monitoring.py` docstring에 기록했다.

**측정 가능한 것과 불가능한 것을 정직하게 구분했다** (과장 금지):
- 이 미들웨어가 실제로 셀 수 있는 것: 이 프로세스가 처리한 요청 수/평균 응답시간 — 03 §6.3 기준 ①(월 500 UV 초과 추세)의 "참고 지표"만 될 수 있다(정확한 UV 집계 아님).
- 절대 셀 수 없는 것: 기준 ②(Render 인스턴스시간)·③(Neon 컴퓨트/저장용량)은 앱 프로세스가 깨어 있는 동안의 요청과 무관한 플랫폼 자체 과금 지표라 앱 코드 내부에서 관측 불가능하다(스핀다운 중엔 이 코드 자체가 실행되지 않는다). 대시보드는 이 사실을 숨기지 않고 Render/Neon 콘솔을 안내한다(03 §7.2/§7.4가 이미 설계한 "Render 자동 이메일 + 운영자 주 1회 수동 확인" 체계를 대체하지 않고 보완).

#### 장애 알림(REQ-012, 03 §7.2)

`ADMINS`(env `DJANGO_ADMIN_EMAIL`)를 채우면 **커스텀 LOGGING dict를 새로 만들지 않고도** Django의 기본 LOGGING 설정(`django.utils.log.DEFAULT_LOGGING`, 이 프로젝트가 `LOGGING`을 오버라이드한 적이 없으므로 그대로 적용됨)이 이미 `django.request` 로거에 `AdminEmailHandler`(`mail_admins`, `DEBUG=False`에서만 동작)를 연결해 둔 상태라는 것을 §3-3에서 실측 확인했다. 그래서 이번 구현은 `ADMINS`/`EMAIL_*`/`SERVER_EMAIL` 설정값만 추가했다(과설계 방지 — 이미 프레임워크가 제공하는 기능을 재발명하지 않음).

#### gunicorn 워커 수(DEC-026)

`feature-WU-07-integration-test.md` IT-20이 "현재 `render.yaml`에 워커 수 지정이 없어 gunicorn 기본값(1개)으로 동작 중"이라고 확인했었다. 이번 WU 작업 지시가 "가역적 결정이므로 자체판단 가능"이라고 명시적으로 위임했으므로, `--workers 1`을 **암묵적 기본값에서 명시적 설정으로** 전환했다. 이 값은 DEC-024(뉴스레터 레이트리밋)뿐 아니라 이번에 추가한 사용량 카운터도 동일하게 "단일 프로세스" 전제 위에서만 정확하므로, 우연한 기본값이 아니라 의도된 설정으로 못박는 것이 맞다고 판단했다.

---

## 2. 설계서 대비 편차 (사유 포함)

1. **`core/apps.py`가 언급했던 "SiteSettings"(REQ-011/012 관련 필드)를 만들지 않음** — 03 §1.2 모듈 경계 표는 `core` 앱에 "사이트 전역 설정(SiteSettings)"을 배정했지만, 04-ux-design.md §2가 이미 "운영자가 콜드스타트 문구를 어드민에서 직접 수정하고 싶다면 `SiteSettings`에 필드를 추가하는 것은 향후 규칙F 재작업 대상으로 남긴다(현재는 템플릿 하드코딩으로 충분)"고 명시적으로 v1 범위 밖으로 정해뒀다(PASS 상태 설계서의 기존 결정). 이번 WU가 이를 새로 만드는 것은 04번 설계서 범위를 벗어나는 것이라 판단해 만들지 않았다 — DEC-016/DEC-019가 이미 세운 "이번엔 필요한 것만 만든다" 선례와 동일 원칙.
2. **사용량 모니터링을 "배치 잡"이 아니라 "요청 경로에 얹은 인메모리 카운터"로 구현** — §1.2/DEC-027에 근거와 함께 기록. 03 §6.3 문언을 새로 열지 않고, 명시적으로 거부된 대상(배치 잡)과 이번 구현(미들웨어)이 기술적으로 다른 범주임을 근거로 규칙F를 트리거하지 않았다.
3. **Wagtail 어드민 커스텀 뷰 권한 제어를 `login_required`(내 코드) + `require_admin_access`(Wagtail이 `register_admin_urls` 훅 URL 전체에 자동으로 씌우는 데코레이터, 소스 직접 확인)의 이중 계층으로 구현** — Wagtail 공식 문서 일부는 "훅으로 등록한 URL에는 권한 검사가 자동으로 붙지 않는다"고 설명하지만, 실제로 설치된 `wagtail==7.4.3`의 `wagtail/admin/urls/__init__.py` 소스를 직접 읽고 `django.test.Client`로 실측한 결과 `decorate_urlpatterns(urlpatterns, require_admin_access)`가 훅으로 추가된 URL에도 이미 적용되고 있음을 확인했다(§3-2). 문서와 실제 설치 버전의 동작이 다를 수 있다는 판단 하에 실측을 우선했고, 내 코드의 `superuser_required`는 제거하지 않고 그대로 두어(방어 계층 중복, 해가 되지 않음) Wagtail의 내부 구현이 향후 바뀌어도 이 뷰 자체는 독립적으로 안전하도록 유지했다.
4. **비-superuser(스태프)가 접근 시도할 때 응답이 "403 페이지"가 아니라 "어드민 홈으로 302 리다이렉트 + 에러 플래시 메시지"** — 내 코드는 `PermissionDenied`를 raise하지만, Wagtail의 `require_admin_access`가 이를 잡아 `permission_denied()`(Wagtail 표준 헬퍼, `wagtail/admin/auth.py`)로 변환한다. 이는 Wagtail 어드민 전역에서 쓰이는 표준 UX 패턴(예: 페이지 편집 권한이 없을 때도 동일하게 동작)과 일치하므로 그대로 두었다(§3-2에서 실측 확인, "403 코드"를 기대하고 있었다면 이 노트가 실제 동작을 정정한다).

---

## 3. 로컬 동작 확인 (실제 실행 결과)

임시 venv(`webapp/.venv_wu08`, `webapp/.venv_wu08b` — 각각 검증 후 삭제) + 임시 production 유사 설정 모듈(`config/settings/it_test_prodlike_wu08.py`, 검증 후 삭제)로 아래를 직접 실행했다.

### 3-1. 기본 동작(dev, SQLite)

1. `pip install -r requirements.txt` — 오류 없음(신규 패키지 없음, WU-01~07과 동일 버전).
2. `manage.py migrate`(빈 DB) → 오류 없음.
3. `manage.py check` → "System check identified no issues (0 silenced)".
4. `manage.py makemigrations --check --dry-run` → "No changes detected"(이번 WU는 모델을 추가하지 않았으므로 정상).
5. `GET /healthz` → 200, `Content-Type: text/plain`, 본문 정확히 `ok`(03 §4 계약 그대로).
6. `GET /`(콜드스타트 카피 회귀) → 200, 응답 본문에 "무료 인프라로 운영 중" 문자열 포함 확인(WU-04 구현 회귀 없음).
7. `manage.py test`(전체) → "Ran 12 tests ... OK"(subscribers 12개, 회귀 없음).

### 3-2. 사용량 대시보드 권한/데이터 흐름(dev, `django.test.Client`)

8. 익명 사용자로 `GET /cms-admin/usage/` → 302, `Location: /cms-admin/login/?next=/cms-admin/usage/`.
9. `is_staff=True`이지만 `wagtailadmin.access_admin` 권한이 없는 사용자 → 302, `/cms-admin/login/`으로 리다이렉트(Wagtail의 `require_admin_access`가 어드민 접근 자체를 막음 — 우리 뷰에 도달하기 전).
10. `wagtailadmin.access_admin` 권한은 있지만 `is_superuser=False`인 사용자(예: Editor 그룹 상당) → 302, `/cms-admin/`(어드민 홈)으로 리다이렉트 + "권한이 없습니다" 플래시 메시지(§2-4 편차 참고, Wagtail 표준 패턴).
11. `is_superuser=True` 사용자 → 200, 응답 본문에 사용량 테이블/유료전환 4대 기준 텍스트 포함 확인.
12. `RequestMetricsMiddleware`가 실제로 카운트하는지: `cache.clear()` 후 `/healthz`를 5회 호출 → `core.monitoring.get_usage_snapshot()`의 오늘 버킷 `request_count == 5`, `avg_response_ms`가 숫자로 채워짐을 확인. 같은 값이 superuser 대시보드 응답 HTML의 표에도 반영됨을 확인.
13. Wagtail 어드민 사이드바(`GET /cms-admin/`, superuser)에 메뉴 항목이 실제로 등록됐는지: 사이드바는 서버가 JSON prop으로 내려주는 구조(`{% sidebar_props %}`)라 평문 HTML 검색으로는 라벨이 직접 보이지 않는다는 것을 처음에 오인했다 — JSON 블록 안에서 유니코드 이스케이프(`사용량 모니터링` = "사용량 모니터링")와 `"url": "/cms-admin/usage/"`가 정확히 포함됨을 재확인했다(§4번 아이콘 `time.svg`가 실제 Wagtail 패키지에 존재함도 파일시스템으로 직접 확인).

### 3-3. production 유사 설정(HTTPS 강제, `it_test_prodlike_wu08.py` = `production.py` 상속 + `DATABASES`만 SQLite로 재정의, WU-01~07과 동일 방법론)

14. 더미 환경변수(`SECRET_KEY`/`DJANGO_ALLOWED_HOSTS`/`RENDER_EXTERNAL_HOSTNAME`/`R2_*`/`DATABASE_URL`/`DJANGO_ADMIN_EMAIL`) 전체 채운 뒤 `manage.py check`/`migrate`/`collectstatic --noinput` 전부 오류 없음. `collectstatic`: "218 static files copied ... 638 post-processed" — `feature-WU-07-integration-test.md` IT-04(218/638)와 **정확히 동일한 수치**로, 이번 WU가 새 정적자산을 추가하지 않았음(템플릿/파이썬 코드만 추가)을 수치로 확인.
15. `settings.MIDDLEWARE` 순서 실측: `['config.middleware.XForwardedForMiddleware', 'core.middleware.RequestMetricsMiddleware', 'django.middleware.security.SecurityMiddleware', ...]` — production.py가 XFF를 맨 앞에 prepend하고 그 다음이 RequestMetrics임을 확인(§1.2 설계 의도와 일치).
16. `settings.ADMINS == [('ops@example.com', 'ops@example.com')]`, `EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend'`, `SERVER_EMAIL == 'errors@blog-web.onrender.com'`(RENDER_EXTERNAL_HOSTNAME 기반 자동 생성) 확인.
17. **AdminEmailHandler 실동작 확인**: `EMAIL_BACKEND`를 `locmem`으로 바꾼 뒤(SMTP 서버가 없는 로컬 환경이므로 실제 네트워크 발송 대신 인메모리 백엔드로 대체) `DEBUG=False` 상태에서 `logging.getLogger("django.request").error(...)`를 호출 → `django.core.mail.outbox`에 메일 1건이 실제로 쌓이고 수신자가 `ops@example.com`, 제목이 `[Django] ERROR: ...`임을 확인 — **커스텀 LOGGING dict 없이 `ADMINS`만 채워도 Django 기본 설정이 실제로 동작함**을 실측으로 증명했다(§1.2 "과설계 방지" 판단의 근거).
18. DEF-001(무한 리다이렉트) 회귀 확인: `GET /healthz`(`X-Forwarded-Proto` 헤더 없음) → 301, `Location: https://blog-web.onrender.com/healthz`. 같은 요청에 `X-Forwarded-Proto: https` 추가 → 200, 본문 `ok`. `GET /robots.txt`(HTTPS 헤더 포함) → 200. 신규 라우트(`/healthz`)에서도 WU-01의 보안 설정이 정상 작동함을 확인.

### 3-4. 정리

검증에 사용한 `.venv_wu08`, `.venv_wu08b`, `db.sqlite3`, `db_wu08_prodlike.sqlite3`, `staticfiles/`, `media/`, `config/settings/it_test_prodlike_wu08.py`, `__pycache__`는 전부 삭제했다. `git status --porcelain`으로 diff에 소스 코드(신규 4파일 + 수정 6파일)만 남았음을 최종 확인했다(§0 참고 — `docs/harness/feature-WU-07-integration-test.md` 등 WU-07 산출물이 이미 커밋 전 상태로 남아있던 것은 이번 WU와 무관한 기존 상태이며 건드리지 않았다).

**로컬에서 확인하지 못한 것**: 실제 SMTP 서버를 통한 이메일 발송(네트워크 필요, 운영자가 실제 SMTP 공급자를 선택해야 함), Render 실제 배포 환경에서의 `healthCheckPath` 동작(Windows 로컬 제약, WU-01~07과 동일 사유), Render/Neon 대시보드 링크의 실제 접근성(단순 정적 링크라 코드 결함 리스크는 낮음).

---

## 4. 게이트 1 — 정적 분석/린트

`AI-AUTO-WORK` 저장소 전체에 Python용 lint/type-check/formatter 설정(`pyproject.toml`, `.flake8`, `ruff.toml`, `.pre-commit-config.yaml` 등)이 여전히 **존재하지 않음을 재확인**했다(WU-01~07과 동일 결론 — 있는데 건너뛴 것이 아니라 설정 자체가 없다). 대체 수단으로 신규/수정 Python 파일 전체(`core/middleware.py`, `core/monitoring.py`, `core/views.py`, `core/urls.py`, `core/wagtail_hooks.py`, `core/apps.py`, `config/settings/base.py`, `config/settings/production.py`)에 `python -m py_compile`을 실행했고 전부 구문 오류 없이 통과했다(§3-1 앞부분). HTML 템플릿(`usage_dashboard.html`)은 별도 린터가 없어 실제 렌더링(§3-2 11번)으로 구문/참조 오류 없음을 확인했다. `render.yaml`은 YAML 린터가 없어 육안 검토 + Render Blueprint 스키마 문서(기존 필드 패턴, 03 §2.4)와의 형식 일치로 확인했다.

## 5. 게이트 2 — 자체 코드 리뷰 체크리스트

- [x] **설계서/디자인서 명세와 실제 구현이 일치하는가** — 일치. §2의 편차 4건은 전부 사유와 함께 명시했고, 모두 "PASS 상태 설계서가 이미 내린 결정을 존중"(1번) 또는 "설계서 문언과 실제 구현 종류의 차이를 근거로 상충 아님이라 판단"(2번) 또는 "실측으로 문서-실제 동작 괴리를 확인하고 실제 동작 기준으로 구현"(3·4번)이며, 임의 추측이 아니다.
- [x] **에러 처리가 누락된 경로가 없는가** — `monitoring.record_request()`는 캐시 접근 실패 등 어떤 예외도 상위(실제 요청 처리)로 전파하지 않도록 `try/except`로 감쌌다(모니터링은 최선노력이어야 하며, 모니터링 코드의 실패가 실제 서비스를 막으면 안 된다는 원칙). `usage_dashboard` 뷰는 익명/비superuser 접근을 각각 로그인 리다이렉트/`PermissionDenied`로 명시적으로 처리한다(조용히 통과시키지 않음). `production.py`의 이메일 설정은 값이 없어도 기동을 막지 않되(§1.2에서 의도적으로 `_require_env`를 쓰지 않은 이유 명시), 이는 이 기능이 앱 구동의 필수 전제가 아니기 때문이라는 근거를 주석에 남겼다.
- [x] **입력값 검증이 시스템 경계(사용자 입력, 외부 API 응답)에서 이루어지는가** — 이 WU에는 사용자로부터 받는 폼/쿼리 입력이 없다(대시보드는 읽기 전용, 헬스체크는 파라미터 없음). 유일한 "경계"는 환경변수(`DJANGO_ADMIN_EMAIL`, `EMAIL_*`)이며, 형식이 틀려도(예: 빈 문자열) 파싱이 안전하게 빈 리스트로 귀결되도록 처리했다(예외 발생 없음, §3-3 16번에서 정상값 기준 확인).
- [x] **하드코딩된 시크릿/자격증명이 없는가** — 없음. `DJANGO_ADMIN_EMAIL`/`EMAIL_HOST_PASSWORD` 등은 전부 환경변수(`render.yaml`에서도 `sync: false`)로만 주입되고, 기본값은 빈 문자열(자격증명 없이도 안전하게 "미발송" 상태로 귀결)이다.
- [x] **범위를 벗어난 변경(곁다리 리팩터링 등)이 섞여 있지 않은가** — `blog/`, `legal/`, `subscribers/`, `custom_images/`, `home/` 등 다른 WU 소유 코드는 전혀 건드리지 않았다. `core/views.py`의 기존 `robots_txt` 함수는 문자 그대로 유지했다(추가만 함). `config/middleware.py`(WU-01, XForwardedForMiddleware)도 무변경. SiteSettings 모델을 만들지 않은 것(§2-1)도 범위 확장을 스스로 자제한 결과다.

---

## 6. traceability.md 갱신

`docs/harness/traceability.md`의 REQ-011/REQ-012 행을 "Not Started"에서 "구현 완료"로 갱신하고, "작업 단위" 컬럼(WU-08은 이미 채워져 있었음)과 "구현 상태"에 이번 구현 근거 파일 경로를 명시했다. "단위테스트" 컬럼은 "대기(6단계)"로, "통합테스트"/"전체테스트(08)" 컬럼은 아직 해당 단계가 실행되지 않았으므로 비워둔 채 유지했다(사실 그대로 반영, WU-04~07 선례와 동일 패턴).

---

## 7. 수동으로 확인이 필요한 부분 (6단계 테스터 및 이후 단계 인계 사항)

1. **실제 SMTP 발송 미검증**: §3-4 참고. 이번 WU는 `EMAIL_BACKEND`를 코드 레벨(설정)까지만 구성했고, 실제 SMTP 서버 연동은 운영자가 SMTP 공급자(예: SendGrid/Mailgun/Gmail SMTP 등 — 이 프로젝트는 특정 벤더를 아직 확정하지 않았다, 확정은 배포 단계 운영자 재량)를 선택해 `EMAIL_HOST`/`EMAIL_HOST_USER`/`EMAIL_HOST_PASSWORD` 환경변수를 채워야 실제로 동작한다. 10단계(배포테스트)에서 강제로 500 에러를 유발해 실제 이메일이 도착하는지 반드시 실측해야 한다(03 §7.2가 이미 요구한 항목, 이번 WU가 새로 만든 요구는 아님).
2. **Render `healthCheckPath` 실제 배포 동작 미검증**: Windows 로컬 제약으로 실제 gunicorn 프로세스 기동/Render 플랫폼의 헬스체크 판정을 확인하지 못했다(WU-01~07과 동일 사유). 10단계에서 실제 배포 후 Render 대시보드의 "Health check" 상태가 정상(healthy)으로 표시되는지 확인 필요.
3. **`--workers 1` 고정이 실제 메모리/처리량에 미치는 영향 미실측**: 로컬에서는 gunicorn 자체를 기동하지 못하므로(Windows), 워커 1개로 실제 동시 요청 처리량이 KPI(02 §5)를 충족하는지는 배포 후 실측이 필요하다. 트래픽이 늘어 워커 증설이 필요해지면 DEC-026/DEC-024가 이미 명시한 대로 공유 저장소(Redis 등) 전환이 선행돼야 한다는 점을 운영 Runbook(11단계)에 반영 권고.
4. **사용량 대시보드 수치가 "프로세스 재시작 이후"로 자주 초기화됨**: 무료 티어 15분 유휴 스핀다운 특성상, 실제 운영에서는 이 대시보드가 보여주는 "최근 7일" 표가 실제로는 몇 시간~하루 분량만 채워져 있을 가능성이 높다. 화면에 "카운터 시작 시각"을 명시해 오해를 방지하도록 했으나(§1.2), 6단계 테스터가 이 특성을 결함으로 오인하지 않도록 미리 인지할 것.
5. **운영 Runbook(11단계) 반영 권고 사항**: 이번 WU는 03 §7.4가 이미 후보로 남긴 "Render Billing 페이지 주 1회 확인", "GitHub Actions 백업 성공 여부 확인"에 더해 "`/cms-admin/usage/` 대시보드로 최근 요청량 추세 확인"과 "`DJANGO_ADMIN_EMAIL`/SMTP 환경변수가 실제로 채워져 있는지 배포 후 1회 확인"을 신규 Runbook 후보 항목으로 인계한다(11단계가 실제 문서를 작성할 때 반영).
6. **git 커밋 여부**: 이번 WU 산출물은 아직 커밋하지 않았다(일반 원칙에 따라 사용자/오케스트레이터의 명시적 커밋 지시를 기다린다). 원격 push는 수행하지 않았다. WU-07의 미커밋 산출물(`docs/harness/feature-WU-07-integration-test.md` 등)도 이번 세션에서 건드리지 않고 그대로 두었다.

---

## 8. 6단계(단위테스트) 인수 조건 (Acceptance Criteria)

6단계 테스터가 그대로 재현 가능한 형태의 체크리스트다(§3에서 실제로 실행해 통과를 확인한 절차와 동일).

1. `webapp/`에서 새 venv를 만들고 `pip install -r requirements.txt`가 오류 없이 끝나는가(신규 패키지 없음).
2. `DJANGO_SETTINGS_MODULE=config.settings.dev`로 `manage.py migrate`가 빈 DB에서 오류 없이 끝나는가.
3. `manage.py check`가 "System check identified no issues"를 출력하는가.
4. `manage.py makemigrations --check --dry-run`이 "No changes detected"를 출력하는가(이번 WU는 모델을 추가하지 않았으므로 신규 마이그레이션이 없어야 함).
5. `GET /healthz` → 200, `Content-Type`이 `text/plain`으로 시작, 본문이 정확히 `ok`인가.
6. `GET /`(홈) 응답 본문에 "무료 인프라로 운영 중" 문자열이 포함되는가(REQ-011 콜드스타트 안내 카피 회귀).
7. `cache.clear()` 후 익명 클라이언트로 `GET /cms-admin/usage/` → 302이고 `Location`이 `/cms-admin/login/`을 포함하는가.
8. `is_staff=True`이지만 `wagtailadmin.access_admin` 권한이 없는 사용자로 로그인 후 `GET /cms-admin/usage/` → 302(어드민 자체 접근 거부, 로그인 페이지로)인가.
9. superuser로 `GET /cms-admin/usage/` → 200이고, 응답 본문에 "유료 전환"(또는 03 §6.3 기준 관련 문구)과 "요청 수" 표가 포함되는가.
10. `cache.clear()` 후 임의 경로(예: `/healthz`)를 N회(예: 5회) 호출한 다음 `core.monitoring.get_usage_snapshot()["daily"][-1]["request_count"] == N`이고 `avg_response_ms`가 `None`이 아닌 숫자인가.
11. 위 상태에서 superuser로 `GET /cms-admin/usage/`를 재요청하면 방금 기록된 요청 수가 화면 표에도 동일하게 반영되는가(대시보드가 실시간으로 `monitoring.get_usage_snapshot()`을 호출함을 확인).
12. `config/settings/production.py`를 상속하고 `DATABASES`만 SQLite로 재정의한 설정 모듈(더미 `SECRET_KEY`/`DJANGO_ALLOWED_HOSTS`/`RENDER_EXTERNAL_HOSTNAME`/`R2_*`/`DATABASE_URL`/`DJANGO_ADMIN_EMAIL` 환경변수)에서 `manage.py check`/`migrate`/`collectstatic --noinput`이 전부 오류 없이 끝나는가.
13. 위 production 유사 설정에서 `settings.MIDDLEWARE`의 첫 두 항목이 정확히 `["config.middleware.XForwardedForMiddleware", "core.middleware.RequestMetricsMiddleware", ...]` 순서인가.
14. 위 production 유사 설정에서 `settings.ADMINS == [("<DJANGO_ADMIN_EMAIL 값>", "<동일 값>")]`이고 `settings.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend"`인가.
15. `EMAIL_BACKEND`를 `django.core.mail.backends.locmem.EmailBackend`로 일시 교체(테스트 전용)하고 `DEBUG=False` 상태에서 `logging.getLogger("django.request").error(...)`를 직접 호출하면 `django.core.mail.outbox`에 메일이 1건 쌓이고 수신자가 `DJANGO_ADMIN_EMAIL` 값과 일치하는가.
16. 위 production 유사 설정에서 `X-Forwarded-Proto` 헤더 없이 `GET /healthz`(`ALLOWED_HOSTS`에 포함된 `Host`) → 301, `Location`이 `https://` 스킴으로 바뀌는가. 같은 요청에 `HTTP_X_FORWARDED_PROTO: https`를 추가하면 200, 본문 `ok`가 오는가(DEF-001 회귀 확인, 신규 라우트 대상).
17. `render.yaml`의 `startCommand`에 `--workers 1`이 포함되어 있고 `healthCheckPath: /healthz`가 설정되어 있는가(문자열 그대로 대조).
18. `manage.py test`(전체)가 기존 12개 테스트(subscribers)를 포함해 전부 OK로 통과하는가(회귀 확인).
19. 검증에 사용한 venv/DB(`db.sqlite3` 등)/staticfiles/media/임시 설정 모듈/임시 스크립트를 정리했는지, `git status --porcelain`에 소스 diff만 남는지 확인.

---

## 9. 다음 단계

이 노트 작성 완료 후 **6단계(`06-unit-tester`) 호출을 트리거한다** — 위 §8의 1~19번 인수 조건을 입력으로 `docs/harness/units/unit-08-test.md`를 작성하도록 한다. 6단계가 PASS 판정하면, 02-planning.md §9 계획에 따라 이 업무 단위(WU-08)의 7단계(통합테스트, WU-01~07과의 조립 검증 포함) 착수 여부를 오케스트레이터가 판단한다.
