# Distributed Trade Surveillance & Market Abuse Detector

Initial scaffold for a batch-oriented trade ingestion pipeline, window-based wash-trade detection, and privacy-preserving FastAPI compliance endpoints.

## Privacy model

- Feed identifiers must be pseudonymized into stable `*_ref` values before they enter the analytics store.
- The compliance API returns references, aggregates, risk bands, and redacted evidence references—not names, account numbers, contact data, or raw order payloads.
- Identity resolution should live in a separate restricted vault with independent authorization and audit logging.
- In production, protect endpoints with SSO/OIDC, RBAC, tenant scoping, rate limits, and immutable audit events.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
pytest
uvicorn app.main:app --reload
```

The database DDL and a window-function wash-trade candidate query are in `db/schema.sql`. The batch consumer currently yields validated bounded batches; persistence and checkpoint commits should be added behind a repository interface.

## Compliance API

- `GET /v1/alerts`: filtered, bounded alert summaries
- `GET /v1/alerts/{alert_id}`: redacted alert drill-down
- `GET /v1/risk/daily`: daily risk aggregates by pseudonymous trader reference
- `GET /v1/audit`: access and change events without raw payloads
