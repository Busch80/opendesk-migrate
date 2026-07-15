# Operator Runbook

This document is for the KPX DevOps team running opendesk-migrate in production.

## 1. First-time setup

```bash
# 1. Clone repo
git clone [email protected]:kpx/opendesk-migrate.git
cd opendesk-migrate

# 2. Generate secrets
python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())' > /tmp/fernet
python3 -c 'import secrets; print(secrets.token_urlsafe(48))' > /tmp/secret
openssl rand -hex 32 > /tmp/pgpass

# 3. Fill .env
cp .env.example .env
cat >> .env <<EOF
FERNET_KEY=$(cat /tmp/fernet)
SECRET_KEY=$(cat /tmp/secret)
POSTGRES_PASSWORD=$(cat /tmp/pgpass)
APP_URL=https://mig.kpx.ch
APP_ENV=production
EOF

# 4. Deploy
docker compose up -d

# 5. Verify health
curl -sS https://mig.kpx.ch/health
```

## 2. Daily operations

### Tail logs
```bash
docker compose logs -f --tail=100 api
docker compose logs -f --tail=200 worker-mail
docker compose logs -f --tail=50 beat
```

### Restart a worker
```bash
docker compose restart worker-mail
docker compose restart worker-onedrive
```

### List running jobs
```bash
docker compose exec postgres psql -U odmig odmig \
    -c "SELECT id, job_type, phase, processed, errors FROM migration_jobs WHERE phase IN ('discovery','full','delta','verify') ORDER BY created_at DESC LIMIT 20;"
```

### Cancel a stuck job
```bash
docker compose exec postgres psql -U odmig odmig \
    -c "UPDATE migration_jobs SET phase='cancelled' WHERE id='<job-uuid>';"

# Kill the Celery task too (replace active with task name shown in /metrics/celery_active)
docker compose exec redis redis-cli cancel "app.tasks.mail.migrate_full" "<job-uuid>" || true
```

## 3. Backup

### Postgres logical backup
```bash
docker compose exec postgres pg_dump -U odmig odmig -Fc -f /tmp/odmig.dump
docker compose cp postgres:/tmp/odmig.dump ./backups/$(date +%Y%m%d).dump
# Upload to KPX backup bucket (off-host)
aws s3 cp ./backups/$(date +%Y%m%d).dump s3://kpx-backups/opendesk-migrate/
```

### Restore from backup
```bash
docker compose exec postgres pg_restore -U odmig -d odmig_restore /tmp/odmig.dump
```

### Staging backup (rare)
```bash
docker run --rm -v opendesk-migrate_staging:/staging:ro \
    alpine tar -czf - /staging | aws s3 cp - s3://kpx-backups/opendesk-migrate/staging-$(date +%Y%m%d).tgz
```

## 4. Migration tenant lifecycle

### Add a new tenant
```bash
curl -X POST https://mig.kpx.ch/api/v1/tenants \
    -H "Content-Type: application/json" \
    -d '{
        "code": "acme",
        "display_name": "ACME AG",
        "opendesk_base_url": "https://ox.acme.internal",
        "m365_tenant_id": "...",
        "m365_client_id": "...",
        "m365_client_secret": "..."
    }'
```

### Bulk-import users
```bash
cat users.csv | while IFS=, read -r upn name; do
    curl -X POST "https://mig.kpx.ch/api/v1/tenants/$TENANT_ID/users" \
        -H "Content-Type: application/json" \
        -d "{\"m365_upn\": \"$upn\", \"display_name\": \"$name\"}"
done
```

### Trigger mail full migration
```bash
curl -X POST https://mig.kpx.ch/api/v1/jobs \
    -H "Content-Type: application/json" \
    -d "{\"user_id\": \"$USER_ID\", \"job_type\": \"mail\", \"phase\": \"full\"}"
```

## 5. Monitoring

- Grafana: KPX Prometheus + Loki
- Prometheus metrics: https://mig.kpx.ch/metrics
- Recommended alerts:
  - `migration_jobs_errors_total > 5%` for 5 minutes
  - Container `worker-mail` uptime < 99% per day
  - `staging_volume_bytes` > 80% of STAGING_MAX_GB
  - Token expiry < 7 days for any active user

## 6. Security incidents

See `SECURITY.md` and `RUNBOOK.md`.
