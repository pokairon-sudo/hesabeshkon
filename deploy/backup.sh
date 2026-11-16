#!/usr/bin/env bash
# نمونه کرون روزانه:
# 0 3 * * * /var/www/hesabeshkon/deploy/backup.sh >> /var/log/hesabeshkon-backup.log 2>&1
set -euo pipefail
cd /var/www/hesabeshkon/home
set -a
. ../.env
set +a
. .venv/bin/activate
python manage.py backup_db --output-dir /var/backups/hesabeshkon
find /var/backups/hesabeshkon -type f -name "*.sqlite3" -mtime +30 -delete
