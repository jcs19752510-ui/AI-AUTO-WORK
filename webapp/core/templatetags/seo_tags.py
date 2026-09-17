"""JSON-LD 안전 직렬화 필터 (WU-05, REQ-005/REQ-017).

03-system-design.md §4는 "이 값들은 전부 신뢰된 운영자 입력 또는 시스템
필드이므로 별도 새니타이즈 라이브러리 없이 Django 템플릿의 기본 auto-escape만
으로 충분하다"고 명시했다. 이는 XSS 방지 관점(값 자체가 악의적 스크립트를
담을 위험이 낮다는 뜻)에서는 맞지만, "Django 기본 auto-escape를 그대로
`<script type=\"application/ld+json\">` 안에 출력해도 된다"는 뜻은 아니다 —
HTML auto-escape는 `"`를 `&quot;`로 바꾸는데, 이는 JSON 문자열의 구분자 자체를
깨뜨려 문법적으로 유효하지 않은 JSON을 만든다(WU-04의 500.html
`TemplateSyntaxError` 사고와 같은 계열의 "검증 없이 두면 실제로 깨지는" 함정,
따라서 §5 검증에서 실제로 `json.loads`로 파싱해 확인한다). 그래서 여기서는
`json.dumps`로 직접 직렬화한 뒤, `</script>` 조기 종료·HTML 삽입만 막는 최소
이스케이프(Django 내장 `json_script` 필터와 동일한 전략 — `<`/`>`/`&`만
유니코드 이스케이프)를 적용하고 `mark_safe`로 표시한다.
"""

import json

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

_ESCAPES = {
    ord("<"): "\\u003C",
    ord(">"): "\\u003E",
    ord("&"): "\\u0026",
}


@register.filter(name="jsonld")
def jsonld(value):
    if not value:
        return ""
    return mark_safe(json.dumps(value, ensure_ascii=False).translate(_ESCAPES))
