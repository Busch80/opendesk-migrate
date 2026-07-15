# Contributing to opendesk-migrate

Thanks for contributing! This is a multi-tenant migration tool that handles
sensitive customer data, so we have a few extra guards in place:

## Code of Conduct

All interactions are governed by our Code of Conduct. Be respectful, be
precise, and bring receipts when disagreeing on technical choices.

## Development workflow

1. Branch from `main`: `git switch -c feat/<short-name>`
2. Make changes, commit with conventional commits (`feat:`, `fix:`, `refactor:` …)
3. Run `make lint test` before pushing
4. Open a PR — at least one approval required
5. CI must pass (lint, type-check, unit + integration tests)
6. Squash-merge to `main`

## Security disclosures

If you find a vulnerability, **do not open a public issue**. Email
[security@opendesk-migrate.example](mailto:security@opendesk-migrate.example).
See `docs/SECURITY.md` for our incident process.

## Coding standards

- Python: ruff (format + lint), mypy strict, type hints required
- TypeScript: eslint + Prettier + tsc strict
- DB changes: always via Alembic — never edit schema by hand
- Sensitive data:
  - All tokens/secrets encrypted via `Fernet` (`app.services.encryption`)
  - Never log mail content (only `item_id` + SHA-256 hash)
  - PII fields in DB are explicit (`m365_upn`, `display_name`)

## Testing

| Mark | Layer | Speed |
|---|---|---|
| `@pytest.mark.unit` | Pure unit | <100ms |
| `@pytest.mark.integration` | Mock/fake external services | <1s |
| `@pytest.mark.e2e` | Real services | gated, manual |

Coverage targets: 70% minimum, 85%+ on critical paths (auth, encryption, mail import).

## License

By submitting a contribution, you agree to license your work under
AGPL-3.0-or-later.
