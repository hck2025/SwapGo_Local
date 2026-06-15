from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    JWT_SECRET: str = "dev-secret"
    JWT_ALG: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24

    DATABASE_URL: str = "sqlite:///./swapgo.db"

    FEE_BPS: int = 30
    SLIPPAGE_WARN_BPS: int = 50
    SLIPPAGE_DANGER_BPS: int = 300

    MERKLE_SNAPSHOT_INTERVAL_SEC: int = 300
    MERKLE_SNAPSHOT_BATCH: int = 100

    ADMIN_BOOTSTRAP_TOKEN: str = "admin-bootstrap-change-me"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
