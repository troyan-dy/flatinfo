"""HTTP-маршруты API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.schemas import AnalyzeRequest, AnalyzeResponse, Suggestion
from app.services import cache
from app.services.advisor import run_analysis
from app.services.geocode import GeocodeError, suggest

router = APIRouter(prefix="/api", tags=["analyze"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/suggest", response_model=list[Suggestion])
async def suggest_endpoint(q: str = Query(min_length=0, max_length=300)) -> list[Suggestion]:
    locations = await suggest(q)
    return [
        Suggestion(display_name=loc.display_name, lat=loc.lat, lon=loc.lon, city=loc.city)
        for loc in locations
    ]


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_endpoint(req: AnalyzeRequest) -> AnalyzeResponse:
    # Ключ от нормализованного запроса: адрес без регистра/пробелов + правки.
    key = cache.make_key(
        "analyze:v1",
        {"address": req.address.strip().lower(), "overrides": req.overrides.model_dump()},
    )
    cached = await cache.get_json(key)
    if cached is not None:
        return AnalyzeResponse.model_validate(cached)

    try:
        resp = await run_analysis(req)
    except GeocodeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    await cache.set_json(key, resp.model_dump(), settings.cache_ttl)
    return resp
