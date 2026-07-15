# opendesk-migrate — Architecture

## 1. Components

### 1.1 FastAPI API (`api/`)
- Listens on `:8000`
- Pydantic-validated request/response models
- Async SQLAlchemy 2.0 + Alembic migrations
- 4 workers (configurable)
- Prometheus `/metrics` endpoint
- `/health`, `/healthz`, `/readyz` for K8s probes

### 1.2 React Web (`web/`)
- Vite 6 + React 19 + Tailwind
- shadcn-style UI components (`src/components/ui/`)
- i18next with de/fr/it/en locales
- React Query for API caching
- React Router v7 for routing
- Nginx serves static assets + SPA fallback

### 1.3 Celery Workers

| Queue | Concurrency | Memory limit | Purpose |
|---|---|---|---|
| `mail` | 4 | 2 GB | IMAP APPEND imports (M365 → Dovecot) |
| `calendar`,`contacts` | 2 | 1 GB | iCal / vCard writes to OX |
| `onedrive` | 4 | 4 GB | WebDAV uploads (chunked + resumable) |
| `maintenance` | 1 | 256 MB | Token refresh, staging cleanup, audit archive |
| `default` (incl. dispatch/discovery) | n/a | n/a | Job dispatcher, discovery-mode |

### 1.4 PostgreSQL 16
- Tables: tenants, tenant_secrets, users_m365, user_oauth_tokens, migration_jobs, errors, audit_log
- `pgcrypto` extension for `gen_random_uuid()`
- `audit_log` has database triggers rejecting UPDATE/DELETE (append-only)
- Connection pooling: 10 main + 20 overflow per process

### 1.5 Redis 7
- Broker + Result backend for Celery
- Token-bucket rate limiter state (per-tenant)
- 512 MB max memory, `allkeys-lru`

### 1.6 Staging — local Docker Volume
- Default: `odmig_staging` named volume, mounted on api + all workers
- Layout: `{base}/tenants/{tenant_id}/jobs/{job_id}/{...}`
- Auto-cleanup (Celery beat) every 6 hours: files older than 14 days
- Quota: 500 GB default (configurable via `STAGING_MAX_GB`)
- S3 backend: drop-in replacement, currently unimplemented

## 2. Data flow per migration type

### 2.1 Mail (M365 → Dovecot)

```
Graph /users/{upn}/mailFolders                          (folder list)
  → folder map (Sent, Trash, …) → 1:1 with Dovecot folders
For each folder:
  Graph /users/{upn}/mailFolders/{id}/messages?$delta
  For each message:
    if message.hasAttachments:
      → staging/{tenant}/{job}/{messageId}/<attachment>
    build RFC822 EML with X-M365-ItemId header (idempotency)
    → IMAP APPEND +FLAGS (\Seen|…) to Dovecot
    → migration_jobs.resumable_state.delta_link updated
```

Idempotency:
- EML header `X-M365-ItemId: <graph-item-id>` carried through
- IMAP APPEND uses UIDPLUS extension → assigns UID
- Skip when header present (stored in `user_oauth_tokens.mail_delta_link` via Graph)

### 2.2 Calendar (M365 → OX)

```
Graph /users/{upn}/events?$delta
For each event:
  build iCalendar with RRULE/EXDATE/RECURRENCE-ID
  → OX JSON API POST /calendar/actions
  recurring events preserved
  attendees (email, status) carried
  reminders (VALARM) preserved
```

### 2.3 Contacts (M365 → OX)

```
Graph /users/{upn}/contacts?$delta
For each contact:
  build vCard 3.0 + contact photo (base64)
  → OX JSON API POST /contacts
  address-book folders preserved (MyContacts, GalContacts, …)
```

### 2.4 OneDrive (Graph → Nextcloud)

```
Graph /users/{upn}/drive/root/children (tree walk)
For each file/folder:
  if size < 2 GB and network stable:
    Graph /items/{id}/contentStream → pipe → Nextcloud WebDAV PUT
  else:
    Graph /items/{id}/contentStream → /staging/{tenant}/{job}/{path} → WebDAV PUT
  permissions:
    Graph /items/{id}/permissions → read ACL
    → Nextcloud OCS POST /apps/files_sharing/api/v1/shares
  versions:
    Graph /items/{id}/versions → Nextcloud WebDAV VERSION
  sharing-link warnings flagged in job report
```

Cleanup: Celery beat `cleanup-staging` deletes staging files older than 14 days
(configurable via `STAGING_RETENTION_DAYS`).

## 3. Security architecture

### 3.1 Encryption at rest
- Fernet key from `FERNET_KEY` env (44 ASCII chars, base64-url)
- All `*_enc` columns in DB = Fernet-encrypted bytes
- Key rotation: re-encrypt rows with new key; tenant-secret `rotated_at` updated

### 3.2 Encryption in transit
- All external traffic via TLS 1.3 (Coolify Traefik + Let's Encrypt)
- Internal cluster traffic plain on `internal` Docker network

### 3.3 Secrets lifecycle
- `FERNET_KEY` (44 chars) — rotation by re-encrypt-script
- `SECRET_KEY` (64 chars) — for app-level signing
- `POSTGRES_PASSWORD` — rotated via DB migration outside scope

### 3.4 Audit log
- Immutable via DB triggers (RAISE EXCEPTION on UPDATE/DELETE)
- Periodic archive to WORM S3 (Ceph Object Lock in production)

## 4. Failure recovery

| Failure | Behaviour |
|---|---|
| Worker crash mid-message | Celery `task_acks_late=True`; message re-queued; idempotency keys prevent double-import |
| Out of disk in staging | `StorageQuotaExceeded` raised; old files cleaned by beat |
| Graph 429 | Token-bucket rate limit, exponential backoff |
| Dovecot connection loss | Celery retry; message stays in graph delta queue |
| Postgres down | API returns 503; workers wait on broker |

## 5. Observability

- Prometheus metrics on `/metrics`
- Structured JSON logs via structlog
- Audit log table for all state changes
- Health endpoints: `/health`, `/healthz` (liveness), `/readyz` (DB-ping)
