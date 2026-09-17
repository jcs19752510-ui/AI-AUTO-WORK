"""WU-08, REQ-012 — 무료 티어 사용량 모니터링(03 §6.3 유료 전환 4대 기준 지원).

03 §6.3은 "별도의 자체 사용량 추적 배치 잡은 두지 않는다(그 잡 자체가 시간을
소모하고 과설계이기 때문)"라고 명시했다. 이 모듈은 그 결정과 상충하지
않는다 — 여기서 만드는 것은 주기적으로 스스로 깨어나 외부 API를 조회하는
배치 잡이 아니라, 이미 발생하는 요청 처리 경로(`core.middleware.
RequestMetricsMiddleware`)에 얹은 인메모리 카운터 집계 함수일 뿐이다.

**측정 가능한 것과 불가능한 것을 명확히 구분한다** (과장 없이 정직하게):
- 이 모듈이 실제로 셀 수 있는 것: 이 Django 프로세스가 처리한 요청 수/평균
  응답시간. 03 §6.3 유료 전환 기준 ①(월 500 UV 초과 추세)의 "참고 지표"는
  될 수 있으나 정확한 순방문자(UV) 수는 아니다(세션/쿠키 기반 UV 집계는
  이번 WU 범위 밖 — 과설계 방지, REQ-012는 "모니터링 장치"를 요구할 뿐
  정밀한 애널리틱스를 요구하지 않는다).
- 이 모듈이 절대 셀 수 없는 것: Render 인스턴스시간(②)·Neon 컴퓨트/저장
  사용률(③)은 앱 프로세스가 깨어 있는 동안의 요청 수와 무관한 플랫폼
  자체 과금 지표라, 우리 코드 내부에서 관측할 방법이 없다(스핀다운 중에는
  애초에 이 코드 자체가 실행되지 않는다). 이 두 기준은 03 §7.2/§7.4가 이미
  설계한 대로 Render 자동 이메일 + 운영자 주 1회 수동 확인(Runbook)이
  유일한 방법이다 — 대시보드는 이 사실을 숨기지 않고 링크로 안내한다.

**LocMemCache 특유의 한계** (DEC-012 재사용, DEC-024와 동일 성격의
트레이드오프): 카운터는 프로세스 메모리에만 존재해 (a) 배포/재시작마다
초기화되고 (b) 워커가 2개 이상이면 워커별로 카운터가 분리된다. render.yaml이
gunicorn 워커 수를 1로 명시 고정하므로(DEC-026) (b)는 v1에서 발생하지
않지만, (a)는 Render 무료 티어의 15분 유휴 스핀다운 특성상 실제로는
"최근 재시작 이후" 수치에 가깝다 — 대시보드 템플릿이 이를 그대로 고지한다.
"""

from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone

CACHE_KEY_PREFIX = "core:usage:daily:"
CACHE_TTL_SECONDS = 60 * 60 * 24 * 35  # 최대 35일치 버킷을 굴릴 수 있도록 여유

DASHBOARD_WINDOW_DAYS = 7

# 프로세스가 최근 언제 시작됐는지(=카운터가 언제부터 쌓이기 시작했는지)를
# 그대로 고지하기 위한 값. 모듈이 처음 임포트되는 시점(=워커 프로세스 기동
# 시점)에 한 번만 계산된다.
PROCESS_STARTED_AT = timezone.now()

# 03 §6.3 유료 전환 4대 기준 — 원문 그대로. 코드가 설계서 문구를 복붙해
# 임의로 재해석하지 않도록, 이 리스트가 대시보드 템플릿에 직접 노출된다.
UPGRADE_CRITERIA = [
    {
        "title": "① 월 500 UV 초과 추세",
        "detail": "02-planning.md §5 KPI(월 순방문자 500명) 초과 추세가 확인될 때.",
        "measurable_here": True,
        "note": "이 대시보드의 \"최근 요청 수\"를 참고 지표로 쓸 수 있으나, 정확한 UV(순방문자) 집계는 아님에 유의.",
    },
    {
        "title": "② Render 인스턴스시간 80% 이상 소진",
        "detail": "Render 무료 인스턴스시간(월 750시간)이 매월 정기적으로 80% 이상 소진될 때.",
        "measurable_here": False,
        "note": "앱 프로세스 내부에서 관측 불가능한 플랫폼 지표. Render 대시보드 Billing 페이지에서 직접 확인.",
    },
    {
        "title": "③ Neon 무료 컴퓨트/저장용량 80% 이상",
        "detail": "Neon 무료 컴퓨트(월 100 CU-hour) 또는 저장용량(0.5GB) 사용률이 80%를 넘을 때.",
        "measurable_here": False,
        "note": "앱 프로세스 내부에서 관측 불가능한 플랫폼 지표. Neon 콘솔에서 직접 확인.",
    },
    {
        "title": "④ 사실상 상시 운영 상태로 전환",
        "detail": "Render 공식 경고(\"프로덕션 비권장\")에도 불구하고 서비스가 사실상 상시 운영 상태라고 운영자가 판단할 때.",
        "measurable_here": False,
        "note": "수치가 아니라 운영자의 정성적 판단 기준.",
    },
]


def _daily_cache_key(day):
    return f"{CACHE_KEY_PREFIX}{day.isoformat()}"


def record_request(duration_ms):
    """요청 1건을 오늘 날짜(KST) 버킷에 집계한다. 예외를 절대 상위로 전파하지
    않는다 — 모니터링 부가기능의 실패가 실제 요청 처리를 막아서는 안 된다."""
    try:
        key = _daily_cache_key(timezone.localdate())
        count, total_ms = cache.get(key, (0, 0.0))
        cache.set(key, (count + 1, total_ms + duration_ms), CACHE_TTL_SECONDS)
    except Exception:  # noqa: BLE001 — 모니터링은 최선노력(best-effort)이어야 한다
        pass


def get_usage_snapshot(days=DASHBOARD_WINDOW_DAYS):
    """최근 N일(오늘 포함, KST 기준)의 요청 수/평균 응답시간을 집계해 반환한다."""
    today = timezone.localdate()
    daily = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        count, total_ms = cache.get(_daily_cache_key(day), (0, 0.0))
        avg_ms = round(total_ms / count, 1) if count else None
        daily.append({"date": day, "request_count": count, "avg_response_ms": avg_ms})

    total_requests = sum(d["request_count"] for d in daily)
    return {
        "daily": daily,
        "total_requests": total_requests,
        "window_days": days,
        "process_started_at": PROCESS_STARTED_AT,
        "generated_at": timezone.now(),
    }
