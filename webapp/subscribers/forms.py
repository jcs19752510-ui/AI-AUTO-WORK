"""뉴스레터 구독 폼 (WU-07, REQ-016, 03-system-design.md §4/§5.3).

03 §4가 명시한 요청 필드(email/consent/hp_field) 그대로다. `next`(돌아갈
페이지 경로)는 03이 정의한 데이터 계약이 아니라 무-JS 폴백 리다이렉트를
위한 순수 구현 세부사항이라 별도 Form 필드로 선언하지 않고 views.py에서
`request.POST`로 직접 읽는다(불필요하게 폼 에러 사전에 섞이지 않도록).
"""

from django import forms


class NewsletterSubscribeForm(forms.Form):
    email = forms.EmailField(
        label="이메일",
        max_length=254,
        error_messages={
            "required": "이메일 주소를 입력해 주세요.",
            "invalid": "올바른 이메일 형식이 아닙니다.",
        },
    )
    consent = forms.BooleanField(
        label="개인정보 수집·이용 동의",
        required=True,
        error_messages={"required": "개인정보 수집·이용에 동의해야 구독할 수 있습니다."},
    )
    # 허니팟(03 §5.3/04 §5) — 사람은 비워 두고 봇만 채운다. required=False라
    # 비어 있어도 폼 유효성 검사를 통과하며, views.py가 값의 존재 여부만 본다.
    hp_field = forms.CharField(label="", required=False)

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()
