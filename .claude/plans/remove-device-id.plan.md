# Plan: Remove device_id Concept

**Source PRD**: .claude/prds/remove-device-id.prd.md
**Selected Milestone**: 1 — Database & model cleanup
**Complexity**: Small

## Summary
Drop the write-only `refresh_tokens.device_id` column and the unwired `allow_multiple_devices` column (which actually lives on `company_settings`, not `companies` as the PRD text states) via a new Alembic migration, and remove both fields from the corresponding SQLAlchemy models (`RefreshToken`, `CompanySettings`). This is DB/ORM-only — no schema (Pydantic), service, route, or Flutter changes in this pass; those are Milestones 2 and 3.

## Pattern Grounding Correction
The PRD's Milestone 1 outcome says "ORM models no longer reference them" on `Company`/`RefreshToken`, but `allow_multiple_devices` is defined on **`CompanySettings`** (`backend/app/models/company.py:60`, table `company_settings`), not on `Company`/`companies`. This plan targets the actual location. The PRD's Database scope line ("drop `companies.allow_multiple_devices`") is likewise imprecise — the column and migration target is `company_settings.allow_multiple_devices`.

## Patterns to Mirror
| Category | Source | Pattern |
|---|---|---|
| Migration structure | `backend/alembic/versions/0008_notifications.py:1-18` | Docstring with milestone name, `Revision ID`/`Revises`/`Create Date` header, `revision`/`down_revision` vars, `upgrade()`/`downgrade()` pair |
| Column drop/add symmetry | `backend/alembic/versions/0008_notifications.py:68-78` | `downgrade()` reverses `upgrade()` exactly, in reverse order, using `op.drop_index`/`op.drop_table`/etc. |
| Column definition to remove | `backend/alembic/versions/0001_initial_foundation.py:69,115` | Original `sa.Column(...)` definitions needed to reconstruct `downgrade()`'s `op.add_column` calls with matching type/nullable/server_default |
| ORM column removal | `backend/app/models/refresh_token.py:41`, `backend/app/models/company.py:60` | Plain `mapped_column` field to delete; no relationship/back_populates tied to either field |
| Test DB provisioning | `backend/tests/conftest.py:64-65` | Test DB schema comes from `Base.metadata.create_all()`, **not** from running Alembic migrations — the model change (not the migration) is what the test suite actually exercises |
| Test fixtures | `backend/tests/test_auth.py:1-16`, `backend/tests/factories.py` | No factory or test currently constructs a `RefreshToken` row or references `device_id`/`allow_multiple_devices` directly — confirms PRD's "no test-suite signal" claim |

## Files to Change
| File | Action | Why |
|---|---|---|
| `backend/alembic/versions/0009_remove_device_id.py` | CREATE | New migration dropping `refresh_tokens.device_id` and `company_settings.allow_multiple_devices`, with a symmetric `downgrade()` that re-adds both columns |
| `backend/app/models/refresh_token.py` | UPDATE | Remove `device_id: Mapped[str | None] = mapped_column(...)` (line 41) |
| `backend/app/models/company.py` | UPDATE | Remove `allow_multiple_devices: Mapped[bool] = mapped_column(...)` (line 60) from `CompanySettings` |

## Tasks

### Task 1: Add the drop migration
- **Action**: Create `backend/alembic/versions/0009_remove_device_id.py` with `revision = "0009_remove_device_id"`, `down_revision = "0008_notifications"`. In `upgrade()`, call `op.drop_column("refresh_tokens", "device_id")` and `op.drop_column("company_settings", "allow_multiple_devices")`. In `downgrade()`, reverse with `op.add_column("company_settings", sa.Column("allow_multiple_devices", sa.Boolean(), server_default=sa.text("true"), nullable=False))` and `op.add_column("refresh_tokens", sa.Column("device_id", sa.String(length=255), nullable=True))` — order and column definitions must match the originals in `0001_initial_foundation.py:69,115` exactly so `downgrade()` is a true inverse.
- **Mirror**: Header/docstring format and revision-chaining style of `0008_notifications.py:1-18`; symmetric upgrade/downgrade ordering of `0008_notifications.py:68-78`.
- **Validate**: `cd backend && alembic upgrade head` against a scratch Postgres instance, then `alembic downgrade -1` to confirm the reverse migration also applies cleanly; `alembic history` shows no branching.

### Task 2: Remove the columns from the ORM models
- **Action**: In `backend/app/models/refresh_token.py`, delete the `device_id` `mapped_column` line. In `backend/app/models/company.py`, delete the `allow_multiple_devices` `mapped_column` line from `CompanySettings`. Leave `TimestampMixin`/`UUIDPrimaryKeyMixin` and all other fields untouched.
- **Mirror**: Existing plain-column style in both files (no custom validators or hybrid properties on either field to carry over).
- **Validate**: `cd backend && python -c "from app.models import Base"` (or equivalent import smoke test) succeeds with no `AttributeError`; `ruff check app/models/refresh_token.py app/models/company.py`.

## Validation
```bash
cd backend
alembic upgrade head          # apply new migration against a scratch/representative DB
alembic downgrade -1          # confirm downgrade() is a true inverse
pytest tests/test_auth.py tests/test_company_isolation.py -v   # models still import/instantiate cleanly
ruff check app/models/
```

## Known Follow-on Break (informational — not fixed in this milestone)
Milestone 1 alone will break the running app if deployed in isolation: `backend/app/services/auth_service.py:45,67,102,123,153,162` and `backend/app/api/v1/auth.py:31,39` still pass `device_id` into `AuthService` methods, and `backend/app/schemas/company.py:36,48` (`CompanySettingsPublic`, `CompanySettingsUpdate`) still declare `allow_multiple_devices`. Per the PRD, "all three layers land together" — this migration/model change should not be deployed until Milestone 2's plan removes those references, or `AuthService`/routes will pass `device_id` to a model field that no longer exists (`TypeError: 'device_id' is an invalid keyword argument for RefreshToken`) and `CompanySettingsPublic.model_validate(...)` will fail (`AttributeError`) reading `company_settings.allow_multiple_devices` from an ORM instance that no longer has it.

## Risks
| Risk | Likelihood | Mitigation |
|---|---|---|
| Deploying this migration/model change before Milestone 2 lands breaks `AuthService`/company-settings routes immediately (see above) | High if landed alone | Land Milestones 1+2 in the same PR/deploy, or at minimum merge-gate Milestone 1 behind Milestone 2's completion |
| `company_settings_page.dart` and `company_settings_repository.dart` (mobile) actively read/write `allow_multiple_devices` via a real "Allow multiple devices" `SwitchListTile` toggle in the Settings UI — this is **not** in the PRD's Milestone 3 Flutter scope (which only covers `device_id`/push-token UUID misuse) | High — confirmed live UI, not dead code | Flag back to the PRD/Milestone 3 plan: the mobile settings screen must also drop this toggle and its repository field, or it will silently stop working (PATCH field ignored by FastAPI's default extra-field handling; GET response parsing via `json['allow_multiple_devices'] as bool` will throw once the field is absent, since the mobile model requires it non-nullable) |
| Migration drop fails/slow on a large production `refresh_tokens`/`company_settings` table (per PRD risk) | Low | Test `alembic upgrade head` against a representative data copy before applying to production; both are simple `DROP COLUMN` operations with no data migration, so risk is low |
| `downgrade()` re-adds columns with different defaults/constraints than production actually had (e.g. real rows have non-default values) | Low | `device_id` is nullable everywhere and never populated by the real app (per PRD evidence) — safe to re-add as `NULL`-default; `allow_multiple_devices` re-adds as `server_default=true`, matching its original definition in `0001_initial_foundation.py:69` |

## Acceptance
- [ ] `backend/alembic/versions/0009_remove_device_id.py` created; `alembic upgrade head` and `alembic downgrade -1` both succeed against a scratch DB
- [ ] `refresh_tokens.device_id` removed from `RefreshToken` model
- [ ] `company_settings.allow_multiple_devices` removed from `CompanySettings` model (not `Company` — PRD wording corrected)
- [ ] `ruff check` passes on both edited model files
- [ ] Existing auth/company-isolation tests still pass (they exercise `Base.metadata.create_all`, not the migration itself)
- [ ] PRD updated: Milestone 3's plan (when written) is made aware of the `company_settings_page.dart` UI-toggle gap surfaced above, since it is currently unscoped
