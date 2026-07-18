"""Aggregate v1 router. New feature routers get mounted here."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, companies, health, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(companies.router)
api_router.include_router(users.router)
