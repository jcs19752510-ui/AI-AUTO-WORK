# WU-06 데이터 마이그레이션 — 개인정보처리방침/이용약관(콘텐츠 정책 포함)/
# 쿠키 사용 고지 3개 페이지를 실제로 생성한다. home/migrations/0002_create_
# homepage.py와 동일한 패턴(historical 모델 + 수동 path/depth/numchild/
# url_path 계산)을 따른다 — Wagtail Page(treebeard MP_Node)의 add_child()
# 트리 로직은 migration의 historical 모델에서 재구성되지 않으므로 직접 계산이
# 필요하다(같은 선례, 이미 실제로 검증된 방식).
#
# 02-planning.md §5 KPI 6("배포 전 100% 게시")을 충족하기 위해 세 페이지를
# live=True로 생성한다. 본문 문구는 03-system-design.md §5.6이 명시한 항목
# (수집최소화/보관기간/파기절차/제3자 위탁 및 국외이전)과 REQ-015 콘텐츠
# 정책 문구를 반영했으나, 실제 법률 검토를 대신하지 않는다는 점을 01/02/03
# 단계가 이미 일관되게 밝힌 대로 이 마이그레이션도 동일하게 전제한다
# (unit-06-note.md 참고).

from django.conf import settings
from django.db import migrations
from django.utils import timezone

from wagtail.coreutils import get_supported_content_language_variant


PRIVACY_POLICY_BODY = """
<h2>수집하는 개인정보 항목</h2>
<p>본 사이트가 현재 실제로 수집하는 개인정보는 다음과 같습니다.</p>
<ul>
<li>이메일 뉴스레터 구독 시: 이메일 주소, 구독 동의 시각, 동의 시점의 본 방침 버전, 스팸 판별용으로 마지막 옥텟을 마스킹한 접속 IP</li>
<li>모든 방문자: 웹 서버가 자동으로 생성하는 접속 로그(IP, 접속 일시, 요청 페이지 등)</li>
</ul>
<p>회원가입, 댓글 등 그 외의 개인정보는 수집하지 않습니다.</p>

<h2>개인정보의 수집 및 이용 목적</h2>
<p>수집한 개인정보는 이메일 뉴스레터 발송, 스팸/부정 이용 방지, 서비스 운영 및 오류 대응 목적으로만 이용합니다.</p>

<h2>개인정보의 보유 및 이용 기간</h2>
<p>뉴스레터 구독 정보는 이용자가 구독 취소(탈퇴)를 요청하기 전까지 보유합니다. 본 사이트는 현재 자동 구독취소 기능을 제공하지 않으므로, 탈퇴를 원하시면 아래 "문의처"로 연락해 주시기 바랍니다.</p>

<h2>개인정보의 파기절차 및 방법</h2>
<p>탈퇴 요청이 접수되면 운영자가 해당 구독자 레코드를 지체 없이 삭제(하드 삭제)합니다. 자동으로 생성되는 백업 파일에는 삭제 시점 이후의 백업부터 반영되며, 기존 백업은 보관 정책에 따라 최대 14일 후 자동 파기됩니다.</p>

<h2>개인정보 처리 위탁 및 국외 이전</h2>
<p>본 사이트는 아래 인프라 사업자에게 개인정보 처리 업무의 일부를 위탁하고 있으며, 이들은 모두 미국에 소재하여 개인정보가 국외로 이전됩니다.</p>
<ul>
<li>Render(웹 호스팅, 미국)</li>
<li>Neon(데이터베이스 호스팅, 미국)</li>
<li>Cloudflare(이미지/백업 파일 저장, 미국)</li>
<li>GitHub(백업 자동 실행, 미국)</li>
</ul>

<h2>이용자의 권리와 행사 방법</h2>
<p>이용자는 언제든지 자신의 개인정보 열람, 정정, 삭제(뉴스레터 구독 취소)를 요청할 수 있습니다. 아래 "문의처"로 연락해 주시면 지체 없이 처리합니다.</p>

<h2>쿠키(Cookie)의 사용</h2>
<p>본 사이트가 사용하는 쿠키에 대한 자세한 내용은 별도의 <a href="/cookies/">쿠키 사용 고지</a> 페이지를 참고해 주시기 바랍니다.</p>

<h2>문의처</h2>
<p>본 방침에 대해 문의하실 사항이 있으면 사이트 운영자에게 연락해 주시기 바랍니다.</p>
<p><em>※ 이 문서는 서비스 운영 원칙을 안내하기 위한 초안이며, 실제 공개 서비스 운영 전 관련 법률 전문가의 자문을 받아 최종 검토할 것을 권고합니다.</em></p>
""".strip()

TERMS_BODY = """
<h2>제1조 (목적)</h2>
<p>이 약관은 본 사이트가 제공하는 콘텐츠 서비스 이용과 관련하여 운영자와 이용자의 권리, 의무 및 책임사항을 규정함을 목적으로 합니다.</p>

<h2>제2조 (게시물의 저작권)</h2>
<p>본 사이트에 게시된 모든 콘텐츠(글, 이미지 등)의 저작권은 별도 표시가 없는 한 운영자에게 있습니다. 사전 동의 없이 콘텐츠를 무단으로 복제, 배포, 전송하는 것을 금지합니다. 제3자의 저작물을 인용하는 경우 출처를 명시합니다.</p>

<h2>제3조 (이용자가 제공한 정보의 처리)</h2>
<p>이메일 뉴스레터 구독 등 이용자가 자발적으로 제공한 정보는 <a href="/privacy-policy/">개인정보처리방침</a>에 따라 처리합니다.</p>

<h2>콘텐츠 정책</h2>
<p><strong>본 사이트는 금융/투자, 의료/건강, 법률, 보험 등 전문적인 자격이나 인허가가 필요한 분야에 대해 전문가의 조언이나 추천을 제공하지 않습니다.</strong></p>
<p>본 사이트에 게시되는 모든 콘텐츠는 일반적인 정보 제공을 목적으로 하며, 이를 금융/투자, 의료, 법률, 보험 등에 대한 전문적인 자문이나 권유로 해석해서는 안 됩니다. 관련된 의사결정을 내리기 전에는 반드시 해당 분야의 자격을 갖춘 전문가와 상담하시기 바랍니다.</p>
<p>본 사이트의 카테고리(분류 체계)는 운영자만 생성/관리하며, 위 정책에 반하는 조언성 콘텐츠는 게시하지 않는 것을 운영 원칙으로 합니다.</p>

<h2>약관의 변경</h2>
<p>운영자는 필요한 경우 이 약관을 변경할 수 있으며, 변경된 약관은 본 페이지에 게시함으로써 효력이 발생합니다.</p>
""".strip()

COOKIES_BODY = """
<h2>쿠키란</h2>
<p>쿠키(Cookie)는 웹사이트를 방문할 때 이용자의 브라우저에 저장되는 작은 데이터 파일로, 사이트가 이용자의 브라우저를 인식하는 데 사용됩니다.</p>

<h2>이 사이트가 사용하는 쿠키</h2>
<ul>
<li><strong>세션 쿠키(sessionid)</strong> — 목적: 관리자 로그인 세션 유지 / 보관기간: 브라우저 종료 시 또는 세션 만료 시까지</li>
<li><strong>CSRF 쿠키(csrftoken)</strong> — 목적: 위조 요청(CSRF) 방지를 위한 보안 토큰 / 보관기간: 약 1년 또는 브라우저 삭제 시까지</li>
</ul>
<p>위 두 쿠키는 관리자(운영자) 로그인 및 폼 제출 보안을 위해 반드시 필요한 쿠키이며, 일반 방문자의 열람 행위 자체에는 별도의 추적 쿠키를 사용하지 않습니다. 향후 방문자 통계(애널리틱스) 도구가 도입되면 그 시점에 이 고지를 갱신합니다.</p>
<p>본 사이트는 쿠키와 별개로 브라우저의 로컬 저장소(localStorage)에 "쿠키 안내 확인 여부"만 저장하여, 한 번 확인한 방문자에게 동일한 안내 배너를 반복해서 보여주지 않습니다. 이 값은 서버로 전송되지 않습니다.</p>

<h2>쿠키 설정 변경 방법</h2>
<p>대부분의 웹 브라우저는 설정 메뉴에서 쿠키 저장을 거부하거나 삭제할 수 있는 옵션을 제공합니다. 다만 세션/CSRF 쿠키를 차단할 경우 관리자 로그인 등 일부 기능이 정상적으로 동작하지 않을 수 있습니다.</p>
""".strip()

LEGAL_PAGES = [
    {
        "slug": "privacy-policy",
        "title": "개인정보처리방침",
        "body": PRIVACY_POLICY_BODY,
    },
    {
        "slug": "terms",
        "title": "이용약관",
        "body": TERMS_BODY,
    },
    {
        "slug": "cookies",
        "title": "쿠키 사용 고지",
        "body": COOKIES_BODY,
    },
]


def create_legal_pages(apps, schema_editor):
    ContentType = apps.get_model("contenttypes.ContentType")
    HomePage = apps.get_model("home.HomePage")
    LegalPage = apps.get_model("legal.LegalPage")
    Locale = apps.get_model("wagtailcore.Locale")

    homepage = HomePage.objects.get(slug="home")

    # wagtailcore.0054_initial_locale가 생성하는 기본 Locale을 그대로 참조한다
    # (wagtailcore.Page.locale은 NOT NULL FK — home/migrations/0002_create_
    # homepage.py는 wagtailcore.0053(Locale 모델 도입) 이전에 실행되어 이 필드가
    # 아직 없었지만, 이 마이그레이션은 그 이후 시점에 실행되므로 명시적으로
    # 채워야 한다. 로컬 검증 중 이를 생략하면 `NOT NULL constraint failed:
    # wagtailcore_page.locale_id`로 실제로 재현됨을 확인했다).
    default_locale = Locale.objects.get(
        language_code=get_supported_content_language_variant(settings.LANGUAGE_CODE)
    )

    legalpage_content_type, __ = ContentType.objects.get_or_create(
        model="legalpage", app_label="legal"
    )

    now = timezone.now()
    for index, spec in enumerate(LEGAL_PAGES, start=1):
        segment = str(index).zfill(4)
        LegalPage.objects.create(
            title=spec["title"],
            draft_title=spec["title"],
            slug=spec["slug"],
            content_type=legalpage_content_type,
            locale=default_locale,
            path=f"{homepage.path}{segment}",
            depth=homepage.depth + 1,
            numchild=0,
            url_path=f"{homepage.url_path}{spec['slug']}/",
            live=True,
            has_unpublished_changes=False,
            first_published_at=now,
            last_published_at=now,
            latest_revision_created_at=now,
            body=spec["body"],
        )

    homepage.numchild = homepage.numchild + len(LEGAL_PAGES)
    homepage.save()


def remove_legal_pages(apps, schema_editor):
    ContentType = apps.get_model("contenttypes.ContentType")
    HomePage = apps.get_model("home.HomePage")
    LegalPage = apps.get_model("legal.LegalPage")

    slugs = [spec["slug"] for spec in LEGAL_PAGES]
    removed = LegalPage.objects.filter(slug__in=slugs).count()
    LegalPage.objects.filter(slug__in=slugs).delete()

    homepage = HomePage.objects.get(slug="home")
    homepage.numchild = max(homepage.numchild - removed, 0)
    homepage.save()

    ContentType.objects.filter(model="legalpage", app_label="legal").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("legal", "0001_initial"),
        ("home", "0002_create_homepage"),
    ]

    operations = [
        migrations.RunPython(create_legal_pages, remove_legal_pages),
    ]
