from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router
from app.config import settings
from app.logging_setup import setup_logging

setup_logging()

app = FastAPI(
    title="flatinfo",
    description="Подсказывает по адресу: выгоднее снимать жильё или покупать",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "flatinfo", "docs": "/docs"}
