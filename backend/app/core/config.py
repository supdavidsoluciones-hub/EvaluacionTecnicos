import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Sistema de Control Operativo de Móviles - Chiriquí"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "chiriqui_secret_key_super_segura_2026_change_in_production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 días
    ALGORITHM: str = "HS256"

    # Base de Datos PostgreSQL de Supabase / Render
    # En producción usar: postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./chiriqui_operativo.db"
    )

    @property
    def database_url_with_ssl(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgresql://") and "sslmode" not in url:
            url += "?sslmode=require"
        return url

    # Supabase Credentials
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://vpivzxkttjsgkpxyvpvp.supabase.co")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "sb_publishable_ewGTKWdwD3HSbNkMH6qmbw_QM0Ho4KA")

    # Cloud Storage
    STORAGE_BUCKET_NAME: Optional[str] = os.getenv("STORAGE_BUCKET_NAME", "chiriqui-photos")
    STORAGE_ACCESS_KEY: Optional[str] = os.getenv("STORAGE_ACCESS_KEY", "")
    STORAGE_SECRET_KEY: Optional[str] = os.getenv("STORAGE_SECRET_KEY", "")
    STORAGE_ENDPOINT_URL: Optional[str] = os.getenv("STORAGE_ENDPOINT_URL", "")

    class Config:
        case_sensitive = True

settings = Settings()
