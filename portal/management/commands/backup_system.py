import json
import zipfile
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "导出数据库业务数据和媒体文件备份包"

    def add_arguments(self, parser):
        parser.add_argument("--output-dir", default="backups", help="备份输出目录")

    def handle(self, *args, **options):
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_dir = Path(options["output_dir"])
        if not output_dir.is_absolute():
            output_dir = settings.BASE_DIR / output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        data_path = output_dir / f"szair-training-data-{timestamp}.json"
        media_zip_path = output_dir / f"szair-training-media-{timestamp}.zip"
        manifest_path = output_dir / f"szair-training-backup-{timestamp}.manifest.json"

        with data_path.open("w", encoding="utf-8") as file_obj:
            call_command(
                "dumpdata",
                "auth",
                "portal",
                "--natural-foreign",
                "--natural-primary",
                indent=2,
                stdout=file_obj,
            )

        media_root = Path(settings.MEDIA_ROOT)
        media_count = 0
        with zipfile.ZipFile(media_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            if media_root.exists():
                for path in media_root.rglob("*"):
                    if path.is_file():
                        archive.write(path, path.relative_to(media_root))
                        media_count += 1

        manifest = {
            "createdAt": timestamp,
            "databaseFixture": str(data_path),
            "mediaArchive": str(media_zip_path),
            "mediaFileCount": media_count,
        }
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS(f"备份完成：{manifest_path}"))
