"""پشتیبان‌گیری امن از هر دو دیتابیس SQLite (default و accountant)."""

import sqlite3
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "کپی امن دیتابیس اصلی و دیتابیس حسابدار در پوشه backups"

    def add_arguments(self, parser):
        parser.add_argument("--output-dir", default="")

    def handle(self, *args, **options):
        target_dir = Path(options["output_dir"] or (Path(settings.BASE_DIR) / "backups"))
        target_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        count = 0
        for alias in ("default", "accountant"):
            source = Path(settings.DATABASES[alias]["NAME"])
            if not source.exists():
                self.stdout.write(self.style.WARNING(f"{alias}: فایلی وجود ندارد ({source})"))
                continue
            target = target_dir / f"{alias}-{stamp}.sqlite3"
            source_conn = sqlite3.connect(source)
            target_conn = sqlite3.connect(target)
            try:
                source_conn.backup(target_conn)
            finally:
                target_conn.close()
                source_conn.close()
            count += 1
            self.stdout.write(self.style.SUCCESS(f"{alias} → {target}"))
        if count == 0:
            self.stdout.write(self.style.ERROR("هیچ دیتابیسی برای پشتیبان‌گیری پیدا نشد."))
        else:
            self.stdout.write(self.style.SUCCESS(f"{count} فایل پشتیبان ساخته شد."))
