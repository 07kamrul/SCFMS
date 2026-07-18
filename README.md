# SCFMS — Construction Field Management System

Mobile-first platform for construction companies: GIS project boundaries on
OpenStreetMap, geofenced live employee tracking, task/issue management, daily
progress and site photos, and role-based dashboards. **Not an ERP.**

> Requirements: see [`.claude/prds/construction-field-management.prd.md`](.claude/prds/construction-field-management.prd.md).

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2 |
| Database | PostgreSQL 16 + PostGIS 3.4 |
| Auth | JWT access tokens + rotating DB-backed refresh tokens, Argon2 hashing |
| Infra | Redis, MinIO (S3), Docker Compose |
| Mobile | Flutter (added in a later milestone) |

## Implementation status

- ✅ **Milestone 1 — Secure multi-tenant foundation** (this delivery): companies,
  users, 5-role RBAC, JWT + refresh rotation, login lockout, company isolation.
- ⏳ Milestones 2–9: projects/polygons, assignments, tracking, tasks/issues,
  progress/photos, dashboards, hardening. See the PRD milestone table.

## Quick start (Docker — recommended)

```bash
cd backend
cp .env.example .env          # then set JWT_SECRET_KEY to a real random value
cd ..
docker compose up --build     # starts db (PostGIS), redis, minio, backend
```

The backend container runs `alembic upgrade head` on start. Then seed demo data:

```bash
docker compose exec backend python seed.py
```

- API docs: http://localhost:8000/docs
- Health:   http://localhost:8000/api/v1/health
- MinIO console: http://localhost:9001

## Local development (without Docker for the app)

Requires a reachable PostgreSQL+PostGIS. You can start just the infra with
`docker compose up db redis minio`.

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# point POSTGRES_HOST=localhost in .env for local runs
alembic upgrade head
python seed.py
uvicorn app.main:app --reload
```

## Running tests

Tests need a disposable PostgreSQL database (PG-specific column types are used).

```bash
cd backend
createdb scfms_test 2>/dev/null || true
export TEST_DATABASE_URL="postgresql+psycopg://scfms:scfms_dev_password@localhost:5432/scfms_test"
pytest
```

Covered: login/refresh-rotation/lockout, multi-tenant isolation, and the RBAC
permission matrix.

## Demo credentials (after `seed.py`)

| Role | Email | Password |
|---|---|---|
| Company Owner | owner@demo.com | owner123 |
| HR Admin | hr@demo.com | hr123456 |
| Project Engineer | pe@demo.com | pe123456 |
| Site Engineer | se@demo.com | se123456 |
| Employee | emp@demo.com | emp12345 |

## Project layout

```
backend/
  app/
    core/          # config, security (JWT/Argon2), logging, exceptions
    db/            # engine, session, declarative base
    models/        # SQLAlchemy models (+ shared enums)
    schemas/       # Pydantic request/response models + response envelope
    repositories/  # tenant-scoped data access
    services/      # business logic (auth, company, user)
    permissions/   # static role→permission matrix
    api/           # dependencies + versioned routers
    main.py        # app factory
  alembic/         # migrations
  tests/           # pytest suite
docker-compose.yml
```

## Security notes

- Passwords hashed with Argon2; refresh tokens stored only as SHA-256, single-use
  with rotation and reuse detection.
- Every data query is scoped by `company_id`; cross-tenant access returns 404.
- RBAC enforced via FastAPI dependencies against a single audited matrix.
- Set a strong `JWT_SECRET_KEY` and rotate credentials before any deployment.
