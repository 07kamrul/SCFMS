"""Liveness and readiness probes."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import Envelope, ok

router = APIRouter(tags=["health"])


@router.get("/health", response_model=Envelope[dict])
def health() -> Envelope[dict]:
    return ok({"status": "ok"})


@router.get("/health/ready", response_model=Envelope[dict])
def readiness(db: Session = Depends(get_db)) -> Envelope[dict]:
    db.execute(text("SELECT 1"))
    postgis = db.execute(text("SELECT PostGIS_Version()")).scalar_one()
    return ok({"status": "ready", "postgis": str(postgis)})
