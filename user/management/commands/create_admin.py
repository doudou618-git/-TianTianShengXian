from django.core.management.base import BaseCommand
from user.models import UserInfo


class Command(BaseCommand):
    help = '创建管理员用户'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='admin', help='管理员用户名')
        parser.add_argument('--password', type=str, default='admin123', help='管理员密码')
        parser.add_argument('--email', type=str, default='admin@tiantian.com', help='管理员邮箱')

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        email = options['email']

        if UserInfo.objects.filter(username=username).exists():
            user = UserInfo.objects.get(username=username)
            user.is_admin = True
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'管理员用户 "{username}" 已更新'))
        else:
            user = UserInfo.objects.create_user(
                username=username,
                password=password,
                email=email,
                is_admin=True
            )
            self.stdout.write(self.style.SUCCESS(f'管理员用户 "{username}" 创建成功'))

        self.stdout.write(self.style.SUCCESS(f'用户名: {username}'))
        self.stdout.write(self.style.SUCCESS(f'密码: {password}'))
        self.stdout.write(self.style.SUCCESS(f'管理后台: http://127.0.0.1:8000/manage/'))
