from wagtail.models import Page


class HomePage(Page):
    """Wagtail 페이지 트리의 루트. 실제 블로그 콘텐츠 모델(BlogPostPage 등)은
    WU-02에서 이 트리의 하위 페이지로 추가된다(03 §3.1 ERD)."""

    pass
