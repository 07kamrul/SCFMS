# SCFMS — Construction Field Management System

## Problem
Construction companies running multiple concurrent sites cannot see, from one place, who is physically on which site, how each project is actually progressing, or what field problems are blocking work. Coordination today happens over phone calls, messaging apps, and paper reports, so owners and engineers learn about absent workers, stalled stages, and site issues hours or days late — and pay for it in schedule slippage and idle labor. Existing field tools are either full ERPs (too heavy, too expensive) or generic task apps with no site-boundary awareness.

## Evidence
- Assumption — needs validation via interviews with 5–10 construction company owners/engineers (target segment TBD; see Open Questions).
- Assumption — the specific gap vs. Procore/Fieldwire (GIS polygon boundaries + geofenced workforce visibility at SMB price point) needs validation via competitive teardown and prospect conversations.

## Users
- **Primary**: Company Owner of a small-to-mid construction firm running several active sites, who currently has no live view of workforce presence or project health.
- **Daily operators**: Project Engineers and Site Engineers who assign work, submit daily progress, and report issues from the field; field Employees who receive tasks and share location while on shift.
- **Support role**: HR Admin who manages employee profiles, roles, and project assignments.
- **Not for**: enterprises wanting full ERP (payroll, attendance automation, inventory, machinery/vehicle tracking, leave, safety, document management are explicitly excluded); office-based back-office staff.

## Hypothesis
We believe **a mobile-first platform that draws each project as an OpenStreetMap polygon and shows geofenced live employee status (inside / near / outside / wrong site / offline) alongside tasks, issues, and daily progress** will **replace phone-and-chat field coordination and give owners same-day project visibility** for **SMB construction companies**.
We'll know we're right when **pilot companies check the live map/dashboard daily and ≥70% of active field staff share location and submit task/progress updates through the app within 4 weeks of rollout**.

## Success Metrics
| Metric | Target | How measured |
|---|---|---|
| Field-staff adoption (location sharing + weekly task update) | ≥70% of assigned employees per pilot company | backend analytics |
| Owner/engineer daily active use of map or dashboard | ≥5 days/week per pilot manager | backend analytics |
| Daily progress report coverage | ≥80% of running projects have a report each working day | report submissions vs. active projects |
| Geofence status correctness | ≥95% agreement with ground truth in field spot-checks | pilot field audit |
| Location fix → visible on manager map | ≤30 s while online | instrumentation |
| Targets above are provisional | TBD — confirm with first pilot | pilot agreement |

## Scope
**MVP** — the minimum to test the hypothesis with one pilot company:
1. Multi-tenant accounts with the 5 roles and strict company-level data isolation (JWT + refresh, RBAC).
2. Project management: create/edit/archive projects, draw and edit a site-boundary polygon on OpenStreetMap, status + progress %, all-projects map with status-colored polygons.
3. Employee ↔ project assignment (many-to-many, role-per-assignment, full history preserved on transfer).
4. Location tracking: foreground + background GPS from the employee app under visible consent, geofence status computed server-side (inside / near [configurable distance] / outside / wrong project / offline / unavailable), live employee map with status-colored markers and tracking-permission hierarchy.
5. Task management: create/assign/update with the defined status + priority workflow, comments, photos, overdue detection.
6. Issue reporting: categories, priorities, status history, photos, comments.
7. Daily progress reports with stage-wise progress and site-photo uploads (compressed, retryable); photo timeline per project.
8. Role-based dashboards (Owner, Project Engineer, Site Engineer, Employee) and core push/in-app notifications with cooldown/dedup.
9. Baseline offline behavior: queued location points, photo upload queue, task/report drafts that survive connectivity loss.
10. Privacy guardrails from day one: explicit consent, always-visible tracking indicator, configurable tracking hours, location access audit log, retention policy. No hidden tracking.

**Out of scope**
- Payroll, accounts, attendance automation, leave, safety, inventory, materials, machinery/vehicle tracking, visitor management, full document management — the product is a focused field-execution platform, not an ERP.
- Full chat/messaging system — announcements and contextual comments only in v1.
- Voice notes — optional future feature.
- AI features (progress summaries, delay prediction, NL assistant) — Phase 2+, never in the critical workflow.
- PDF/Excel report exports, digital site diary, engineer performance reports — Phase 2 (valuable, but not needed to test the hypothesis).
- iOS-specific polish beyond Flutter defaults — TBD; pilot device fleet unknown (see Open Questions).
- Google Maps — prohibited; OpenStreetMap only (constraint, not a decision to revisit).

**Constraint (user-mandated, fixed):** FastAPI + PostgreSQL/PostGIS backend, Flutter mobile app, OpenStreetMap. Architecture detail belongs to /plan.

## Delivery Milestones
| # | Milestone | Outcome | Status | Plan |
|---|---|---|---|---|
| 1 | Secure multi-tenant foundation | A company can sign in with role-based access; no cross-company data access is possible | complete | backend/ (auth, RBAC, isolation; 17 tests green) |
| 2 | Projects on the map | Owner creates projects, draws site polygons on OSM, and sees all projects color-coded on one map | pending | — |
| 3 | Workforce assignment | HR Admin assigns employees/engineers to multiple projects with preserved history | pending | — |
| 4 | Live geofenced tracking | Managers see permitted employees' live status (inside/near/outside/wrong-site/offline) on the map, with consent and visible tracking indicator | pending | — |
| 5 | Field execution loop | Tasks and issues flow through their full status workflows with photos and comments | pending | — |
| 6 | Daily progress & photo timeline | Site Engineers submit daily reports with staged progress and photos; owners see per-project timelines | pending | — |
| 7 | Dashboards & notifications | Each role opens to a dashboard answering "what needs my attention today", with push notifications | pending | — |
| 8 | Pilot hardening | Offline queues, sync retry, and privacy controls verified with a real pilot company on real sites | pending | — |
| 9 | Phase 2: diary, exports, comms | Digital site diary, PDF/Excel reports, announcements/mentions | pending | — |

## Open Questions
- [ ] Who is the launch customer / target market? (Company size, country — this drives location-privacy law compliance, e.g. Japan APPI vs. GDPR, and consent design.)
- [ ] Is there any concrete demand evidence (a committed pilot company, prospect interviews)? Currently zero — the whole problem framing is assumption.
- [ ] Device fleet: Android-only for MVP, or must iOS ship simultaneously? (Background location behaves very differently per platform.)
- [ ] Default geofence "near" distance and tracking-hours policy — company-configurable, but what defaults do pilots expect?
- [ ] Is progress % self-reported per stage acceptable for v1, or does the pilot require the configurable weighting model up front?
- [ ] Single company per user, or can one user belong to multiple companies (affects login/company-selection flow)?
- [ ] Business model (per-seat SaaS? per-project?) — affects multi-tenancy limits and plan gating, even if billing itself is out of scope.

## Risks
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Field workers reject location tracking (privacy backlash, uninstalls) | High | Critical — hypothesis fails | Consent-first design, visible indicator, tracking limited to configured work hours, worker-facing value (their own status, tasks) |
| Background GPS drains batteries → workers disable it | High | High | Adaptive update intervals (movement/battery/app-state), pilot battery benchmarks as a launch gate |
| GPS accuracy near structures makes geofence status wrong → managers distrust the map | Medium | High | Accuracy-aware status logic, "near" buffer, show confidence/last-seen instead of false precision |
| Location-privacy law non-compliance in launch market | Medium | Critical | Resolve launch-market question first; retention + audit log in MVP; legal review before pilot |
| Offline/sync complexity delays MVP | Medium | Medium | Baseline queues only in MVP; full conflict handling deferred to hardening milestone |
| Location spoofing (mock GPS) undermines trust in tracking | Medium | Medium | Mock-location flag captured per point; treat as signal, not enforcement, in v1 |
| No validated demand — building on assumption | High | Critical | Secure a pilot commitment before Milestone 4 (tracking) is built; Milestones 1–3 are reusable regardless |

---
*Status: DRAFT — requirements only. Implementation planning pending via /plan.*
