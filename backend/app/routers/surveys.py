"""HTTP endpoints for Module 2 (sky viewer configuration)."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.surveys import DEFAULT_GRID, OVERLAYS, SURVEYS, Overlay, Survey

router = APIRouter(prefix="/api", tags=["surveys"])


class SurveyCatalog(BaseModel):
    surveys: list[Survey]
    overlays: list[Overlay]
    default_grid: list[str]


@router.get("/surveys", response_model=SurveyCatalog)
async def list_surveys() -> SurveyCatalog:
    return SurveyCatalog(surveys=SURVEYS, overlays=OVERLAYS, default_grid=DEFAULT_GRID)
