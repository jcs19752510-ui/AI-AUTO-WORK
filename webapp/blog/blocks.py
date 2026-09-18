"""BlogPostPage.body(StreamField)에서 사용하는 콘텐츠 블록 정의 (REQ-001, WU-02).

03-system-design.md §3.2가 명시한 "문단/이미지/인용/FAQ블록 등 콘텐츠 타입"을
그대로 구현한다. 블록별 `template` Meta(ArticleBody 프런트엔드 마크업, 04-ux-design.md
§4)는 WU-04가 추가했다 — WU-02는 데이터 구조(특히 접근성 필수 필드 `alt_text`)만
정의하고 프런트엔드 렌더링은 명시적으로 WU-04로 미뤘다(unit-02-note.md §2-4).
`paragraph`(RichTextBlock)는 커스텀 템플릿이 필요 없다 — RichTextBlock은 별도
template 지정 없이도 Wagtail이 이미 새니타이즈된 리치텍스트 HTML을 그대로
렌더링한다(03 §5.2 auto-escape 원칙과 일관).
"""

from wagtail import blocks
from wagtail.images.blocks import ImageChooserBlock


class ImageBlock(blocks.StructBlock):
    """04-ux-design.md §5 접근성 기준: 본문 중간에 삽입되는 이미지는 대표이미지와
    달리 Wagtail이 자동으로 제공하는 대체텍스트가 없으므로, alt_text를 필수 입력
    필드로 둔다(§7 정합성 체크에서 지적된 5단계 반영 요구사항)."""

    image = ImageChooserBlock(required=True)
    alt_text = blocks.CharBlock(
        required=True,
        max_length=255,
        help_text="스크린리더 등 접근성을 위한 대체 텍스트(필수)",
    )
    caption = blocks.CharBlock(required=False, max_length=255)

    class Meta:
        icon = "image"
        label = "이미지"
        template = "blog/blocks/image_block.html"


class QuoteBlock(blocks.StructBlock):
    quote = blocks.TextBlock(required=True)
    attribution = blocks.CharBlock(required=False, max_length=255, help_text="인용 출처(선택)")

    class Meta:
        icon = "openquote"
        label = "인용"
        template = "blog/blocks/quote_block.html"


class FAQItemBlock(blocks.StructBlock):
    # help_text는 REQ-017(AI 검색 대응 질문-답변형 콘텐츠)의 "템플릿 수준
    # 지원"을 어드민 편집 화면에서 운영자에게 직접 안내하기 위한 것이다
    # (WU-05, webapp/CONTENT_GUIDE.md와 동일한 가이드의 요약).
    question = blocks.CharBlock(
        required=True,
        max_length=255,
        help_text="독자가 검색창에 입력할 법한 질문 형태로 쓰세요 (예: 'RSS가 무엇인가요?').",
    )
    answer = blocks.RichTextBlock(
        required=True,
        help_text="질문에 대한 답을 2~3문장으로 먼저 제시한 뒤 필요하면 설명을 덧붙이세요.",
    )

    class Meta:
        icon = "help"
        label = "FAQ 항목"


class FAQBlock(blocks.StructBlock):
    """REQ-017(AI 검색 대응 질문-답변형 콘텐츠)이 사용할 블록. 여기 담은
    질문/답변은 게시물 상세 페이지에서 schema.org FAQPage JSON-LD 구조화
    데이터로도 자동 변환된다(WU-05, 03-system-design.md §4,
    `BlogPostPage.get_faq_json_ld`)."""

    items = blocks.ListBlock(FAQItemBlock)

    class Meta:
        icon = "help"
        label = "FAQ"
        template = "blog/blocks/faq_block.html"


class BlogStreamBlock(blocks.StreamBlock):
    paragraph = blocks.RichTextBlock(icon="pilcrow", label="문단")
    image = ImageBlock()
    quote = QuoteBlock()
    faq = FAQBlock()
