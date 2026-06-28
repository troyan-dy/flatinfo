"""HTTP-маршруты API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.advisor import run_analysis
from app.services.geocode import GeocodeError

router = APIRouter(prefix="/api", tags=["analyze"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_endpoint(req: AnalyzeRequest) -> AnalyzeResponse:
    try:
        return await run_analysis(req)
    except GeocodeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
