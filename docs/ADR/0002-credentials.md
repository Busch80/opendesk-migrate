# ADR-0002: Multi-Tenant credentials stored in DB

## Status
Accepted (v0.1.0)

## Context
We have three classes of credentials:
1. **Tenant-level secrets** (3-5 per customer): OX admin, NC admin, M365 app registration
2. **Per-user OAuth tokens** (1 per end-user × thousands): refresh + access tokens
3. **Per-user passwords** (transient, never persisted)

Where to store them:
- A. Coolify env vars per customer instance (requires N instances for N customers)
- B. Postgres tenant_secrets table, encrypted via Fernet
- C. HashiCorp Vault (overkill for KPX)

## Decision
**Postgres `tenant_secrets` + `user_oauth_tokens` tables, all sensitive columns Fernet-encrypted at the application layer.**

## Rationale
- Per-user tokens cannot live in env vars (thousands, rotating)
- Tenant secrets can technically live in env vars but require redeploy per rotation
- Fernet (AES-128-CBC + HMAC) is well-understood, simple, no infra
- DB row-level security (or app-level guard) isolates tenants

## Consequences
- One Fernet key (`FERNET_KEY`) is the single root secret
- `FERNET_KEY` rotation requires a re-encrypt script (planned `make rotate-fernet`)
- Compromised DB + `FERNET_KEY` = full credential leak — DB is treated as sensitive storage

## Follow-ups
- Implement `make rotate-fernet` for zero-downtime key rotation
- Add DB-level encryption (TDE) if compliance requires
- Plan quarterly access review of `FERNET_KEY` exposure
