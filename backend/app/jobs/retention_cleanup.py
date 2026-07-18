"""Purge location points past each company's configured retention window.

Standalone script, same style as seed.py — run on a schedule via cron/systemd
timer (Celery is an installed-but-unused dependency here; adding a beat
scheduler for one daily job is unnecessary infrastructure for this MVP).

Run:  python -m app.jobs.retention_cleanup
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.company import Company, CompanySettings
from app.repositories.location_point_repo import LocationPointRepository

logger = logging.getLogger("scfms.jobs.retention_cleanup")


def purge(db: Session) -> int:
    """Core logic against an already-open session — kept separate from run()
    so tests can inject the test-transaction session instead of a real one."""
    total_deleted = 0
    rows = db.execute(
        select(Company.id, CompanySettings.location_retention_days).join(
            CompanySettings, CompanySettings.company_id == Company.id
        )
    ).all()
    points = LocationPointRepository(db)
    for company_id, retention_days in rows:
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        deleted = points.delete_older_than(company_id=company_id, cutoff=cutoff)
        if deleted:
            logger.info(
                "Deleted %d location point(s) for company %s older than %d days",
                deleted, company_id, retention_days,
            )
        total_deleted += deleted
    return total_deleted


def run() -> int:
    """Returns the total number of location points deleted."""
    db = SessionLocal()
    try:
        total_deleted = purge(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return total_deleted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    deleted_count = run()
    logger.info("Retention cleanup complete: %d location point(s) deleted.", deleted_count)
