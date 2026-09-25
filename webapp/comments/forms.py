"""댓글 작성 폼 (REQ-019, 03-system-design.md §4/§3.2-1).

이메일은 받지 않는다(사용자 결정, DEC-047) — `author_name`/`body`만 필수
필드다. `page_id`는 대상 게시물을 가리키는 데이터 계약이지만, `next`가
subscribers 쪽에서 별도 Form 필드가 아니었던 것과 동일한 이유로(뷰 로직
세부사항이지 사용자 입력 검증 대상이 아님) 여기서도 `views.py`가
`request.POST`에서 직접 읽는다 — 단, `page_id`는 반드시 유효한 값이어야
제출을 진행할 수 있으므로 뷰에서 조회 실패 시 400으로 처리한다.
"""

from django import forms


class CommentForm(forms.Form):
    author_name = forms.CharField(
        label="이름",
        max_length=100,
        error_messages={"required": "이름을 입력해 주세요."},
    )
    body = forms.CharField(
        label="댓글",
        max_length=2000,
        widget=forms.Textarea,
        error_messages={"required": "댓글 내용을 입력해 주세요."},
    )
    # 허니팟(03 §3.2-1) — subscribers 앱과 동일한 패턴.
    hp_field = forms.CharField(label="", required=False)

    def clean_author_name(self):
        value = self.cleaned_data["author_name"].strip()
        if not value:
            raise forms.ValidationError("이름을 입력해 주세요.")
        return value

    def clean_body(self):
        value = self.cleaned_data["body"].strip()
        if not value:
            raise forms.ValidationError("댓글 내용을 입력해 주세요.")
        return value
