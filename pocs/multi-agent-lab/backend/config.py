from __future__ import annotations

import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    database_url: str = "sqlite:///./db/app.db"
    app_env: str = "development"

    # Cache
    cache_ttl_hours: int = 24

    # Rate limiting (requests per minute per IP on POST /demo/run)
    rate_limit_per_minute: int = 10

    # CORS — comma-separated origins; "*" only in development
    allowed_origins: str = "http://localhost:8010,http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def openai_configured(self) -> bool:
        return bool(self.openai_api_key.strip())

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


settings = Settings()

# Configure root logger once at import time
logging.basicConfig(
    level=logging.DEBUG if settings.is_development else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
