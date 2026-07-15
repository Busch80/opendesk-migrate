# Test fixtures for offline development
A test directory containing recorded Microsoft Graph / openDesk responses so
that integration tests can run without real cloud services.

In production, these are generated via `vcr.py` cassettes. For the MVP
seed cassettes are committed for the happy paths.

# How to record new cassettes

```bash
# Need a real M365 sandbox tenant for this:
python -m tests.integration.m365.record_cassette "tests/integration/m365/fixtures/users_get.yaml"
```
