import json
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from portal.models import ConductRule


class Command(BaseCommand):
    help = "从 assets/conduct-rules.js 导入作风量化规则"

    def handle(self, *args, **options):
        source_path = Path(settings.BASE_DIR) / "assets" / "conduct-rules.js"
        if not source_path.exists():
            raise CommandError(f"规则文件不存在：{source_path}")

        text = source_path.read_text(encoding="utf-8")
        match = re.search(r"window\.CONDUCT_SCORE_RULES\s*=\s*(\[.*?\])\.map", text, re.S)
        if not match:
            raise CommandError("未找到 window.CONDUCT_SCORE_RULES 数组")

        rows = json.loads(match.group(1))
        created = 0
        updated = 0
        for index, row in enumerate(rows, start=1):
            rule_id = f"rule-{index:03d}"
            _, was_created = ConductRule.objects.update_or_create(
                rule_id=rule_id,
                defaults={
                    "dimension": row[0],
                    "module": row[1],
                    "item": row[2],
                    "title": row[3],
                    "values": row[4],
                    "source": row[5],
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"导入完成：新增 {created} 条，更新 {updated} 条。"))
