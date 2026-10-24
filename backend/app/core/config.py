"""Configuración central cargada desde variables de entorno (Pydantic Settings)."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_REPO_ROOT / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ENVIRONMENT: str = "development"
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Chicago Road Safety Risk API"

    # Dual-Engine: asyncpg para la API, psycopg3 para Alembic / ETL
    DATABASE_URL: str = "postgresql+asyncpg://chicago_admin:chicago_secure_pass_2026@localhost:5432/chicago_safety"
    SYNC_DATABASE_URL: str = "postgresql+psycopg://chicago_admin:chicago_secure_pass_2026@localhost:5432/chicago_safety"

    SOCRATA_DOMAIN: str = "data.cityofchicago.org"
    SOCRATA_APP_TOKEN: str = ""

    DATA_DIR: str = str(_REPO_ROOT / "data")
    MODEL_PATH: str = str(_REPO_ROOT / "backend" / "app" / "ml" / "models" / "chicago_risk_xgboost.joblib")
    DUCKDB_PATH: str = str(_REPO_ROOT / "data" / "duckdb" / "chicago_olap.duckdb")

    CORS_ORIGINS: str = "http://localhost,http://localhost:80,http://localhost:3000,http://localhost:5173"

    DB_POOL_MIN: int = Field(default=2, ge=1)
    DB_POOL_MAX: int = Field(default=10, ge=1)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def asyncpg_dsn(self) -> str:
        """DSN plano para asyncpg (sin el prefijo de dialecto de SQLAlchemy)."""
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    @property
    def psycopg_dsn(self) -> str:
        return self.SYNC_DATABASE_URL.replace("postgresql+psycopg://", "postgresql://")

    @property
    def raw_dir(self) -> Path:
        return Path(self.DATA_DIR) / "raw"

    @property
    def processed_dir(self) -> Path:
        return Path(self.DATA_DIR) / "processed"


# Envolvente estricta de saneamiento municipal de Chicago (Fase 2)
CHICAGO_BBOX = {
    "min_lat": 41.644,
    "max_lat": 42.023,
    "min_lon": -87.940,
    "max_lon": -87.524,
}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
