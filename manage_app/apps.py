from django.apps import AppConfig


class ManageAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'manage_app'
    verbose_name = '管理后台'
