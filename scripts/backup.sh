#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"

if [ -f ".env" ]; then
  set -a
  source .env
  set +a
fi

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUT_FILE="${BACKUP_DIR}/pychallenge_${TIMESTAMP}.sql.gz"

docker compose exec -T postgres pg_dump -U "${POSTGRES_USER}" "${POSTGRES_DB}" | gzip > "$OUT_FILE"
echo "Backup saqlandi: $OUT_FILE"

# Oxirgi 14 ta nusxani qoldirish, qolganlarini o'chirish
ls -1t "${BACKUP_DIR}"/pychallenge_*.sql.gz 2>/dev/null | tail -n +15 | xargs -r rm -f
