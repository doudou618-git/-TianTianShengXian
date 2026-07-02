import os
from celery import Celery

# 设置 Django 默认设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TianTianShengXian.settings')

# 创建 Celery 应用实例
app = Celery('TianTianShengXian')

# 从 Django settings 中加载配置（以 CELERY_ 开头的配置）
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现所有已安装 app 中的 tasks.py 文件
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """调试任务"""
    print(f'Request: {self.request!r}')
