from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Геокодер (OpenStreetMap Nominatim). Бесплатный, требует осмысленный User-Agent.
    geocoder_url: str = "https://nominatim.openstreetmap.org/search"
    geocoder_user_agent: str = "flatinfo/0.1 (rent-vs-buy advisor)"
    geocoder_timeout: float = 8.0

    # Кэш геокодера: сколько результатов держать в памяти.
    geocode_cache_size: int = 512

    # CORS: фронт на Next.js в дев-режиме.
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Логирование.
    log_level: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
