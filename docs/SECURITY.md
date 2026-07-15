# Security Architecture

## 1. Threat model

| Threat | Mitigation |
|---|---|
| DB dump leaked | All secrets Fernet-encrypted; no plaintext credentials |
| Network MITM | TLS 1.3 enforced (Coolify Traefik + LE) |
| FERNET_KEY extracted | Treat as SEV1 — rotate, re-encrypt, audit |
| OAuth token leak | Tokens Fernet-encrypted at rest; refresh valid 90 days max |
| Internal service impersonation | Docker `internal` network not exposed |
| Audit log tampering | DB triggers reject UPDATE/DELETE |
| Cross-tenant leak | Application-level tenant guards (per-route); planned RLS |
| M365 token replay | Tokens not transferable across users/tenants |

## 2. Encryption

### 2.1 At rest
- `*_enc` columns = Fernet (AES-128-CBC + HMAC)
- `m365_upn`, `display_name` stored plain (required for Graph queries)

### 2.2 In transit
- TLS 1.3 to/from Coolify (Traefik + Let's Encrypt)
- Internal docker network: plain HTTP (acceptable as it's host-scoped)

### 2.3 Key management
- `FERNET_KEY`: 44 chars, random, env-only, never logged
- Rotation: rotate key → re-encrypt-script → atomic swap

## 3. Authentication

### 3.1 Operator UI
- (Planned) Keycloak OIDC + 2FA enforced
- Session: short-lived, refresh on activity
- Roles: `viewer`, `operator`, `admin`

### 3.2 M365 users (delegated)
- App + Delegated Permissions (separate per-customer app registration)
- Each user does Device Code flow once
- Refresh handled automatically (Celery beat every 30 min)

## 4. Logging hygiene

- Never log email **content**
- Only log message **IDs** + SHA-256 hashes
- Audit table append-only (DB triggers)
- Logs scrubbed via structlog before persistence

## 5. Vulnerability reporting

[security@opendesk-migrate.example](mailto:security@opendesk-migrate.example) — please do not open public issues for security bugs.

Response SLA:
- SEV1: 4 hours
- SEV2: 24 hours
- SEV3: 5 working days

## 6. Compliance posture

- CH-DSG: data stays in CH, AVV with each customer
- FINMA: audit log retained for 7 years (WORM archive)
- EU-GDPR: data subject export (`GET /api/v1/audit`) + deletion (`DELETE /tenants/{id}/users/{user_id}`)
- AGPL-3.0: source disclosure required when providing as network service
