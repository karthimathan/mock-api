# Copilot Instructions for mock-api

## What this repo is
A single-file FastAPI mock backend (`main.py`) implementing the API contract
described in `api.md` (Partner App Integration Platform). There is no
database, ORM, or container setup — everything is in-memory and resets on
restart.

## Tech constraints
- FastAPI + Pydantic v2 only. Do NOT add SQLAlchemy, Alembic, PostgreSQL,
  Docker, PyJWT, passlib/bcrypt/argon2, or any other external dependency
  unless the user explicitly asks for it.
- Auth is mock bearer tokens (`secrets.token_urlsafe`) stored in the
  `access_tokens`/`refresh_tokens` dicts — not real JWT signing.
- Passwords are hashed with `hashlib.sha256` via `hash_password()` — mock
  only, not production-grade.
- Storage is plain Python dicts (`*_db` module-level globals) keyed by UUID
  string ids from `new_id()`.

## Conventions used in main.py
- All responses use the envelope helper `ok(data, status_code=200)` for
  success, and errors are raised as `AppError(code, message, status_code)`
  which the global exception handler formats as
  `{"success": false, "error": {"code": ..., "message": ...}}`.
- Domain not-found/validation errors use `AppError` with UPPER_SNAKE_CASE
  `code` values (e.g. `PARTNER_NOT_FOUND`, `DUPLICATE_INTEGRATION`).
- Auth dependencies: `get_current_user` (bearer token), `require_roles(*roles)`
  (role-gated admin actions), `get_current_client` (mobile `X-Api-Key` header
  — never trust a raw client id from the request).
- Pagination via `paginate(items, page, page_size)` returning
  `{items, pagination: {page, pageSize, total, totalPages}}`.
- Every mutating endpoint calls `record_audit(...)` to log the action.
- Deployments are immutable snapshots: `build_deployment_items()` copies
  current client integrations (denormalizing partner/app fields) into
  `deployment_items_db` so history never changes after publish/rollback.
- Seed/demo users and sample data are created in `seed()`, called once at
  module import time. Add new demo accounts there following the existing
  pattern (id, email, password_hash via `hash_password()`, role, status,
  timestamps).

## Running & testing
- Run: `python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000`
  (use `python -m uvicorn`, not the `uvicorn` script directly — it may not be
  on PATH on this machine).
- Swagger UI: `http://localhost:8000/docs`.
- After changes, smoke-test with a quick login + one or two representative
  endpoints (e.g. via `Invoke-RestMethod` in PowerShell) rather than assuming
  correctness.

## Docs
- `api.md` is the source-of-truth spec. If behavior changes, keep `api.md`
  and `main.py` in sync — don't let them drift.
