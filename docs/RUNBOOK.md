# Incident Runbook

## Severity levels

- **SEV1**: Service down OR credentials compromised OR massive data leak
- **SEV2**: Degraded service for several tenants OR scheduled downtime missed
- **SEV3**: Single-tenant failure OR non-critical error spike

## SEV1: Credentials compromised

If `FERNET_KEY` or `POSTGRES_PASSWORD` is exposed:

1. **Rotate immediately**
   ```bash
   # Generate new keys
   python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())' > /tmp/fernet.new
   openssl rand -hex 32 > /tmp/pgpass.new
   ```
2. **Re-encrypt all tenant_secrets** with new Fernet key (script: `scripts/reencrypt.py`)
3. **Rotate Postgres password**
   ```bash
   docker compose exec postgres psql -c "ALTER USER odmig PASSWORD '$(cat /tmp/pgpass.new)';"
   ```
4. **Audit log review**: was the read? when? from where?
5. **NOTIFY customers** per AVV (within 24h for personal data, immediately for credentials)

## SEV1: API down

1. `docker compose ps` — which services are unhealthy?
2. `docker compose logs --tail=200 <service>` — what's the error?
3. Most common: Postgres down → restart `postgres`
4. If `api` unhealthy: `docker compose restart api`
5. If everything fails: bring traffic via backup (KPX-side load balancer)

## SEV2: Migrations error-spike

1. Check audit log for bulk error patterns
2. Inspect specific failing job: GET /api/v1/jobs/{id}
3. Check rate-limit metrics (Graph 429s)
4. Cancel problematic jobs if needed
5. Rerun with corrected params

## SEV3: Single-tenant failure

1. Identify tenant from audit log
2. Check token expiry for their users
3. Trigger token refresh (beat job does this every 30 min; can force re-auth)
4. Rerun affected jobs

## Database corruption / disaster

1. Stop all workers: `docker compose stop worker-mail worker-cal-contacts worker-onedrive worker-maintenance beat`
2. Restore from latest backup
3. Verify with reconciliation report
4. Restart workers

## Contact

- **Security**: [email protected]
- **KPX DevOps**: see internal directory
