# Compliance Notes

## AGPL-3.0 License

opendesk-migrate is licensed under AGPL-3.0-or-later.

This means:
- Free to use, modify, and redistribute
- If you modify and **operate** it over a network, you **must publish**
  your modifications under the same license
- Sales of hosted versions to third parties → full source disclosure required

KPX publishes its changes as part of this repository. White-label deployments
for customers must follow the same terms. See `LICENSE` for full text.

## CH-DSG (Schweizer Datenschutzgesetz)

Personal data must:
- Stay on CH infrastructure (Coolify hosted in CH)
- Be processed under a signed AVV per customer
- Be deletable on request (one-tenant export + delete tools included)
- Be documented (RoPA processed by KPX)

Migrations are designed with these in mind.

## FINMA (Financial sector)

For banks / financial services:
- Audit log retained 7 years (WORM archive to S3 with object-lock)
- Recoverable evidence of every data movement
- Encrypt at rest (Fernet) + in transit (TLS)
- Operator access logging via OIDC

## EU-GDPR

Although data lives in CH, customers may request data export/deletion
under GDPR portability. The API supports:
- Export one user's full data (`GET /users/{id}/audit`)
- Deletion (`DELETE /users/{id}`)
- Tenant-level export/import via Alembic migrations + custom scripts

## ISO 27001 / SOC2 (future)

This tool is **not yet certified**. Path to certification:
- Document the security architecture (this directory)
- Implement role-based access (admin/operator/viewer)
- Production hardening (TDE, secrets via Vault)
- External pen-test

## OWASP Top-10 mitigations

| A# | Mitigated how |
|---|---|
| A01 Broken Access Control | Tenant guards on every route; future RLS |
| A02 Cryptographic Failures | Fernet, TLS, no plaintext credentials |
| A03 Injection | SQLAlchemy ORM (no raw SQL), Pydantic validation |
| A04 Insecure Design | Least-privilege tokens, no shared admin |
| A05 Security Misconfig | Pydantic-env validation, fail-fast |
| A06 Vulnerable Components | Dependabot, ruff, safety |
| A07 Auth Failures | OIDC + 2FA (planned for operator UI) |
| A08 Data Integrity | Audit log triggers, Alembic versioning |
| A09 Logging Failures | structlog → Loki, audit table |
| A10 SSRF | URL allowlist (Microsoft endpoints only) |
