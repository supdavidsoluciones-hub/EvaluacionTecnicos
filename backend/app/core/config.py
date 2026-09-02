import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Sistema de Control Operativo de Móviles - Chiriquí"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "chiriqui_secret_key_super_segura_2026_change_in_production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 días
    ALGORITHM: str = "HS256"

    # Base de Datos: PostgreSQL por defecto, fallback a SQLite para dev local si no hay DATABASE_URL
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./chiriqui_operativo.db"
    )

    # Cloud Storage (Cloudflare R2 / AWS S3 / local fallback)
    STORAGE_BUCKET_NAME: Optional[str] = os.getenv("STORAGE_BUCKET_NAME", "chiriqui-photos")
    STORAGE_ACCESS_KEY: Optional[str] = os.getenv("STORAGE_ACCESS_KEY", "")
    STORAGE_SECRET_KEY: Optional[str] = os.getenv("STORAGE_SECRET_KEY", "")
    STORAGE_ENDPOINT_URL: Optional[str] = os.getenv("STORAGE_ENDPOINT_URL", "")

    class Config:
        case_sensitive = True

settings = Settings()
