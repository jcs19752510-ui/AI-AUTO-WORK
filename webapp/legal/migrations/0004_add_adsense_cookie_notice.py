# DEC-053(수익화 모델 = 광고 기반) 후속 — 쿠키 사용 고지 본문의
# "일반 방문자의 열람 행위 자체에는 별도의 추적 쿠키를 사용하지 않습니다"
# 문장이 애드센스 활성화 이후 사실과 어긋나게 되는 것을 막기 위한 선제
# 정정. legal_page.html이 adsense_client_id가 채워진 경우에만 광고 쿠키
# 안내 문단을 추가로 렌더링하므로(같은 파일, 같은 조건), 이 본문 문장은
# 그 문단과 미리 모순되지 않게만 다듬는다 — "안 쓴다"는 단정 대신 "필요한
# 쿠키"라는 사실만 남기고, 광고 쿠키 여부는 화면 하단 조건부 안내로
# 위임한다.
#
# 0003_add_comment_privacy_notice.py와 동일한 패턴: historical 모델이 아닌
# 실제 LegalPage를 import해 save_revision().publish()로 리비전 이력을
# 남기고, 원본 문구가 이미 바뀌었으면(운영자 수동 편집 등) 건드리지 않는다.

from django.db import migrations

_OLD_SENTENCE = (
    "<p>위 두 쿠키는 관리자(운영자) 로그인 및 폼 제출 보안을 위해 반드시 "
    "필요한 쿠키이며, 일반 방문자의 열람 행위 자체에는 별도의 추적 쿠키를 "
    "사용하지 않습니다. 향후 방문자 통계(애널리틱스) 도구가 도입되면 그 "
    "시점에 이 고지를 갱신합니다.</p>"
)

_NEW_SENTENCE = (
    "<p>위 두 쿠키는 관리자(운영자) 로그인 및 폼 제출 보안을 위해 반드시 "
    "필요한 쿠키입니다. 이 외에 광고 서비스(Google AdSense 등)를 통해 "
    "광고를 게재하는 경우 광고 쿠키가 추가로 사용될 수 있으며, 실제 사용 "
    "여부와 상세 내용은 이 페이지 하단 안내를 참고해 주시기 바랍니다. "
    "향후 방문자 통계(애널리틱스) 도구가 도입되면 그 시점에 이 고지를 "
    "갱신합니다.</p>"
)


def update_cookie_notice(apps, schema_editor):
    from legal.models import LegalPage

    page = LegalPage.objects.filter(slug="cookies").first()
    if page is None:
        return

    if _OLD_SENTENCE not in page.body:
        # 이미 갱신되었거나 운영자가 어드민에서 직접 수정한 경우 —
        # 덮어쓰지 않는다(0003과 동일 원칙, 운영자의 수동 편집을 존중).
        return

    page.body = page.body.replace(_OLD_SENTENCE, _NEW_SENTENCE)
    page.save_revision(user=None).publish()


def noop_reverse(apps, schema_editor):
    # 콘텐츠 정정은 되돌리지 않는다(0003과 동일 원칙).
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("legal", "0003_add_comment_privacy_notice"),
        ("core", "0003_add_adsense_client_id"),
    ]

    operations = [
        migrations.RunPython(update_cookie_notice, noop_reverse),
    ]
