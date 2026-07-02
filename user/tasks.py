import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task
def send_email_code_task(email, code):
    """
    异步发送邮箱验证码

    Args:
        email: 目标邮箱地址
        code: 6位验证码
    """
    try:
        send_mail(
            subject='【天天生鲜】邮箱验证码',
            message=f'【天天生鲜】您的邮箱验证码是：{code}，5分钟内有效。请勿将验证码泄露给他人。',
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', '3384225904@qq.com'),
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info(f'[邮箱验证码] 发送成功 - 邮箱: {email}, 验证码: {code}')
        print(f'[邮箱验证码] 发送成功 - 邮箱: {email}, 验证码: {code}')
        return {'status': 'success', 'email': email}
    except Exception as e:
        logger.error(f'[邮箱验证码] 发送失败 - 邮箱: {email}, 错误: {e}')
        print(f'[邮箱验证码] 发送失败 - 邮箱: {email}, 错误: {e}')
        return {'status': 'failed', 'email': email, 'error': str(e)}
