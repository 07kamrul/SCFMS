# Remove device_id Concept

## Problem
SCFMS's auth flow carries a `device_id` field end-to-end (Flutter login request → `LoginRequest` schema → `AuthService` → `refresh_tokens.device_id` column) that does nothing: it is written on login/refresh but never read back, enforces no single-device login, and binds no session or token to a device. Backend engineers maintaining `auth_service.py` and the `refresh_tokens` model must reason about a field that looks security-relevant but isn't, which increases cognitive load and the risk that future code (or a reviewer) assumes it already provides protection it does not. Left in place, it also becomes a false foundation for planned device-security work (e.g., single-device-login enforcement), which is better built on a clean slate than retrofitted onto a placeholder.

## Evidence
- Code trace of the full call path confirms `device_id` is write-only: accepted by `LoginRequest`, passed through `AuthService.login()`/`refresh()`, stored on `refresh_tokens.device_id` (nullable `VARCHAR(255)`, no index, no FK) — never queried, joined, or validated against anywhere in the backend.
- The Flutter mobile client's actual `/auth/login` call never sends `device_id` at all — the column is unpopulated by the real app today. The client instead generates a separate UUID (`readOrCreateDeviceId()` in `secure_token_storage.dart`) that it misuses as a placeholder push-notification token via `_registerDeviceToken()`, which is a distinct and equally dead-end mechanism.
- `companies.allow_multiple_devices` (boolean, unwired, referenced only in the model and schema, never read in any backend logic) is a related dead concept discovered during this trace and is in scope for removal alongside `device_id`.
- No backend or mobile tests reference `device_id`, so there is no test-suite signal currently depending on it.

## Users
- **Primary**: Backend engineers maintaining SCFMS's auth code (`auth_service.py`, `refresh_token.py`, `schemas/auth.py`) and anyone about to design real device-security features on top of this code.
- **Not for**: End users of the SCFMS mobile app — this change has no user-visible behavior change (device_id already has no observable effect today).

## Hypothesis
We believe **fully removing the dead `device_id` field/column, the unwired `allow_multiple_devices` flag, and the Flutter client's misuse of its device UUID as a fake push token** will **eliminate a false sense of device-level security and clean up the codebase ahead of real device-security work**, for **the engineers who own and will extend this auth code**.
We'll know we're right when a repository-wide search for `device_id`/`deviceId` (excluding migration history and changelogs) returns zero hits in backend, database, and mobile source, and the existing auth test suite still passes.

## Success Metrics
| Metric | Target | How measured |
|---|---|---|
| Remaining `device_id`/`deviceId` references in live source | 0 | Repo-wide grep across `backend/`, `mobile/lib/`, and current (non-historical) DB schema, excluding past migration files and changelogs |
| Auth test suite health | 100% passing | Run existing backend auth tests after removal; no new failures introduced |
| Migration correctness | Applies cleanly | New Alembic migration drops `refresh_tokens.device_id` and `companies.allow_multiple_devices` without error against a representative dataset |

## Scope
**MVP**
- Database: new Alembic migration dropping `refresh_tokens.device_id` and `companies.allow_multiple_devices`; corresponding SQLAlchemy model updates (`RefreshToken`, `Company`).
- Backend: remove `device_id` from `LoginRequest`/related schemas, `AuthService.login()`/`refresh()`/`_issue_token_pair()`, and the `/auth/login`/`/auth/refresh` route handlers; remove `allow_multiple_devices` from `Company` schemas.
- Flutter: remove `readOrCreateDeviceId()` and its stored `scfms_device_id` secure-storage value, and stop `_registerDeviceToken()` from sending that UUID as a push token to `/notifications/device-tokens`.
- All three layers land together (no interim deprecation period) since nothing currently depends on the field being present.

**Out of scope**
- Building real device-security features (single-device-login enforcement, session/token binding to a device, device-management UI) — this is pure removal, future work is separate.
- Reworking push-notification token generation into a real APNs/FCM registration flow — this PRD only stops the fake-UUID misuse; a proper push-token mechanism is a separate future effort.
- The unrelated `device_tokens` table (real push-notification tokens with platform/token columns) — explicitly out of scope, must not be conflated with `device_id`.

## Delivery Milestones
<!-- Business outcomes, not engineering tasks. /plan turns each into a plan. -->
<!-- Status: pending | in-progress | complete -->

| # | Milestone | Outcome | Status | Plan |
|---|---|---|---|---|
| 1 | Database & model cleanup | `refresh_tokens.device_id` and `company_settings.allow_multiple_devices` are dropped via migration; ORM models no longer reference them | complete | `.claude/plans/remove-device-id.plan.md` |
| 2 | Backend API/service cleanup | `LoginRequest`, `AuthService`, and auth route handlers no longer accept, store, or propagate `device_id`; `CompanySettings` schemas drop `allow_multiple_devices` | complete | — |
| 3 | Flutter client cleanup | App no longer generates/stores a device UUID or sends it as a push token; `_registerDeviceToken()` removed; `company_settings_page.dart`'s "Allow multiple devices" toggle and repository field also removed | complete | — |

## Open Questions
- [ ] Does any existing production data in `refresh_tokens.device_id` need to be considered before dropping the column (e.g., audit/export before drop), or is a straight drop acceptable given it's never read?
- [ ] Should `_registerDeviceToken()`/the `/notifications/device-tokens` call be removed entirely in this pass, or left calling with no token until real push-token support exists? (Currently scoped as "stop sending the fake UUID," but the call site's fate needs a decision in `/plan`.)
- [ ] Are there other services or clients (e.g., an admin web app, if one exists) that also reference `device_id` and weren't covered by this trace?

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Older/cached mobile app builds still POST a `device_id` field to `/auth/login` after backend removes it | Low | Low | FastAPI/Pydantic ignores unknown extra fields by default; verify schema config doesn't reject extras before merging |
| Migration drop fails or is slow on a large `refresh_tokens`/`companies` table in production | Low | Medium | Test migration against a representative data copy before applying to production |
| Removing `_registerDeviceToken()` inadvertently breaks a currently-working (if fake) push registration flow relied on elsewhere | Low | Low | Confirm no other code path consumes the registered "token" before removing the call site |

---
*Status: IMPLEMENTED — all three milestones landed together (working tree, uncommitted). Verified: repo-wide grep for `device_id`/`deviceId`/`allow_multiple_devices` in live source returns zero hits; `alembic upgrade head`/`downgrade -1` both succeed against a scratch DB; full backend test suite (109 tests) passes; `ruff check` clean.*
