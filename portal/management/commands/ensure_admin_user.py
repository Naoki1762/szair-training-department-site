import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "创建或更新本地/部署环境的 Django 后台管理员"

    def handle(self, *args, **options):
        username = os.environ.get("ADMIN_USERNAME", "admin")
        password = os.environ.get("ADMIN_PASSWORD", "shfx6688")
        email = os.environ.get("ADMIN_EMAIL", "admin@example.com")

        User = get_user_model()
        user, created = User.objects.get_or_create(username=username, defaults={"email": email})
        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        action = "创建" if created else "更新"
        self.stdout.write(self.style.SUCCESS(f"已{action}后台管理员：{username}"))
