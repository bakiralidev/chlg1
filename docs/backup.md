# PostgreSQL Zaxira (Backup) va Tiklash (Restore)

## Zaxira olish

```bash
chmod +x scripts/backup.sh
./scripts/backup.sh
```

Skript `./backups/pychallenge_YYYYMMDD_HHMMSS.sql.gz` faylini yaratadi va faqat oxirgi 14 ta nusxani saqlaydi.

Kunlik cron (02:00):

```bash
0 2 * * * cd /path/to/challenge && ./scripts/backup.sh >> /var/log/pychallenge_backup.log 2>&1
```

## Tiklash (Restore)

```bash
gunzip -c backups/pychallenge_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```
