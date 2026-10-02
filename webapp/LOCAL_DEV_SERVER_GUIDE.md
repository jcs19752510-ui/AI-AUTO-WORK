# 로컬 개발 서버 실행 가이드

이 문서는 이 프로젝트를 처음 로컬에서 띄우는 사람도 추가 질문 없이 그대로
따라할 수 있도록 작성했다. 실제로 이 저장소에서 여러 차례 서버를 켜고
끄면서 겪은 문제(포트 충돌, 메모리 부족으로 인한 자동 종료 등)를 그대로
반영했다 — 추측이 아니라 실측 기준이다.

- 이 문서가 다루는 것: **로컬 개발 서버 실행/종료/문제 해결**만.
- 이 문서가 다루지 않는 것: 관리자 계정/권한(`ADMIN_ACCESS_GUIDE.md`), 글쓰기
  가이드(`CONTENT_GUIDE.md`), 백업/복구(`BACKUP_RESTORE_GUIDE.md`), 애드센스
  연동(`ADMIN_ACCESS_GUIDE.md` §7). 실제 운영 배포 절차도 이 문서 범위 밖이다
  (이 문서는 `127.0.0.1`에서만 도는 로컬 전용 실행법).

---

## 1. 사전 준비 (한 번만 확인하면 됨)

이 저장소에는 이미 가상환경(`webapp/.venv/`)과 필요한 패키지가 전부
설치되어 있다. 아래 명령으로 존재 여부만 확인한다.

```
webapp/.venv/Scripts/python.exe --version
```

버전 정보가 출력되면(예: `Python 3.13.15`) 준비 완료다. 만약 `.venv` 폴더
자체가 없다면(저장소를 새로 클론한 경우) 아래로 새로 만든다.

```powershell
cd webapp
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## 2. 서버 실행

**PowerShell 기준** (Windows 기본 터미널):

```powershell
cd C:\big21\vibe-coding\AI-AUTO-WORK\webapp
.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8010
```

**Git Bash 기준**:

```bash
cd /c/big21/vibe-coding/AI-AUTO-WORK/webapp
.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8010
```

실행하면 아래와 비슷한 로그가 뜬다. `Quit the server with CTRL-BREAK`까지
나오면 정상이다.

```
Watching for file changes with StatReloader
Performing system checks...
System check identified no issues (0 silenced).
Django version 5.2.17, using settings 'config.settings.dev'
Starting development server at http://127.0.0.1:8010/
```

### 왜 기본 포트(8000)가 아니라 8010을 쓰는가

이 컴퓨터에서는 `8000`번 포트로 실행하면 `Error: You don't have permission
to access that port.`가 나는 것이 실제로 확인됐다(다른 프로그램이 이미
점유했거나 OS 예약 포트 범위와 겹치는 경우 흔히 발생). 원인을 붙잡고
씨름하는 대신 **비어 있는 포트(8010)로 바로 옮기는 것**이 가장 빠른
해결책이다. 8010도 막혀 있다면 8020, 8030처럼 다른 4자리 포트로 바꿔서
시도한다.

## 3. 접속 주소

서버가 켜진 상태에서 브라우저로 아래 주소에 접속한다.

| 화면 | 주소 | 비고 |
|---|---|---|
| 사이트 홈(방문자 화면) | http://127.0.0.1:8010/ | 로그인 불필요 |
| 콘텐츠 관리자(Wagtail) | http://127.0.0.1:8010/cms-admin/login/ | 글 작성/발행/댓글 승인 |
| 구독자 관리(Django 기본 관리자) | http://127.0.0.1:8010/django-admin/login/ | 뉴스레터 구독자 조회/삭제 전용 |

관리자 계정 아이디/비밀번호는 보안상 이 문서에 적지 않는다.
`ADMIN_ACCESS_GUIDE.md` §2~3(계정 생성/비밀번호 정책)을 참고하거나, 로컬
DB에 이미 계정이 있다면 아래로 비밀번호를 새로 지정할 수 있다.

```
.venv/Scripts/python.exe manage.py changepassword admin
```

## 4. 서버 종료

터미널 창에서 `Ctrl + C`(PowerShell) 또는 `Ctrl + Break`를 누른다. 백그라운드로
띄운 경우(예: Claude Code가 `run_in_background`로 실행한 경우) 해당 작업을
중지시키면 된다.

## 5. 자주 발생하는 문제

| 증상 | 원인 | 해결 |
|---|---|---|
| `Error: You don't have permission to access that port.` | 해당 포트가 이미 사용 중이거나 OS 예약 범위와 충돌 | 2절 설명대로 다른 포트(8010, 8020...)로 재시도 |
| 잘 켜져 있던 서버가 아무 조작 없이 갑자기 꺼짐 | 이 컴퓨터의 메모리가 부족해질 때 백그라운드 프로세스가 자동으로 정리되는 경우가 실제로 여러 차례 있었다(Claude Code 세션 한정 동작) | 서버를 다시 실행하면 그만이다. 데이터는 SQLite 파일(`db.sqlite3`)에 저장되어 있어 서버가 꺼졌다 켜져도 사라지지 않는다 |
| `No directory at: .../staticfiles/` 경고 | 배포용 정적 파일 수집(`collectstatic`)을 아직 하지 않음 | 로컬 개발 중에는 무시해도 된다(개발 서버는 정적 파일을 자동으로 직접 서빙한다). 실제 배포 전에만 `manage.py collectstatic` 필요 |
| 접속은 되는데 글/카테고리가 하나도 안 보임 | 정상 — 처음 클론한 DB이거나 데이터를 초기화한 상태 | 관리자로 로그인해 글을 작성하거나(`CONTENT_GUIDE.md` 참고), 마이그레이션이 최신인지 `manage.py showmigrations`로 확인 |
| 코드(모델/뷰/설정)를 고쳤는데 반영이 안 됨 | `--noreload` 옵션을 주고 실행했다면 자동 재시작이 꺼져 있다 | `--noreload` 없이 실행하면 코드 변경 시 자동 재시작된다. 이미 `--noreload`로 띄웠다면 서버를 껐다가 다시 켠다 |

## 6. 전체 자동 테스트 실행 (선택)

서버가 실제로 잘 도는지와 별개로, 코드 자체가 정상인지 확인하고 싶으면
아래 명령으로 전체 테스트를 돌린다(2026-09-26 기준 94개 테스트, 이 환경에서
완료까지 약 2~3분 소요 — 최초 1회는 이미지 렌더링·마이그레이션 재생 때문에
더 걸릴 수 있다).

```
.venv/Scripts/python.exe manage.py test
```

마지막 줄에 `OK`가 뜨면 전부 통과한 것이다. 특정 기능만 빠르게 확인하고
싶으면 앱 이름을 붙인다(예: `manage.py test blog`, `manage.py test comments`).

---

## 다음에 볼 문서

- 글쓰기/발행 방법: `CONTENT_GUIDE.md`
- 관리자 계정/권한/보안: `ADMIN_ACCESS_GUIDE.md`
- 백업/복구: `BACKUP_RESTORE_GUIDE.md`
