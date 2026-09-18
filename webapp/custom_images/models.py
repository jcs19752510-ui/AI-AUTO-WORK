"""Wagtail 커스텀 이미지 모델 (WU-03, REQ-006, 03-system-design.md §3.2 CustomImage/
CustomRendition, DEC-008).

지금 당장 stock ``wagtail.images.models.Image`` 대비 추가 필드는 없다. 그럼에도
지금 시점에 커스텀 모델로 교체하는 이유는, WU-02의 07단계 통합테스트(IT-I5,
DEF-002)가 실측으로 증명한 대로 "이미지 데이터가 이미 존재하는 상태에서 나중에
``WAGTAILIMAGES_IMAGE_MODEL``을 교체하면 기존 이미지의 마이그레이션 비용이 커진다"는
것 때문이다. 현재 업로드된 이미지가 0건인 지금(WU-02는 이미지 FK를 실제로 채운 적
없음, unit-02-note.md §3 "로컬에서 확인하지 못한 것")이 교체 비용이 가장 저렴한
시점이며, 이후 필요한 커스텀 필드(예: AI 대체텍스트, 저작권 출처 등)를 언제든
무리 없이 추가할 수 있는 구조를 먼저 확보하는 것이 목적이다.
"""

from django.db import models

from wagtail.images.models import AbstractImage, AbstractRendition, Image


class CustomImage(AbstractImage):
    admin_form_fields = Image.admin_form_fields

    class Meta(AbstractImage.Meta):
        verbose_name = "이미지"
        verbose_name_plural = "이미지"
        # Wagtail의 그룹별 "Choose" 권한 패널은 Django 표준 헬퍼
        # get_permission_codename("choose", opts)로 codename을 파생시키므로
        # (opts.model_name="customimage"), stock Image.Meta의 리터럴
        # "choose_image"를 그대로 복사하면 안 되고 모델명에 맞춰야 한다.
        permissions = [
            ("choose_customimage", "Can choose custom image"),
        ]


class CustomRendition(AbstractRendition):
    image = models.ForeignKey(
        CustomImage, on_delete=models.CASCADE, related_name="renditions"
    )

    class Meta:
        unique_together = (("image", "filter_spec", "focal_point_key"),)
