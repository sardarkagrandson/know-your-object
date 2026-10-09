"""HTTP endpoints for Module 1 (target resolver)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool

from app.schemas.target import ResolvedTarget
from app.services.resolver import TargetResolver, get_resolver

router = APIRouter(prefix="/api", tags=["resolver"])


@router.get("/resolve", response_model=ResolvedTarget)
async def resolve_target(
    q: str = Query(
        ...,
        min_length=1,
        max_length=200,
        description="Target name (e.g. 'NGC 1365') or J2000 coordinates",
    ),
    refresh: bool = Query(False, description="Bypass the server-side cache"),
) -> ResolvedTarget:
    resolver: TargetResolver = get_resolver()
    try:
        return await run_in_threadpool(resolver.resolve, q, not refresh)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
