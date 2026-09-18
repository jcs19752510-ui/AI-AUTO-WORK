from django.apps import AppConfig


class CustomImagesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "custom_images"
    label = "custom_images"
    verbose_name = "커스텀 이미지"
