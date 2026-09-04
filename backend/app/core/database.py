import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

def init_engine():
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    connect_args = {}
    engine_kwargs = {"pool_pre_ping": True}

    if db_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        return create_engine(db_url, connect_args=connect_args, **engine_kwargs)
    elif db_url.startswith("postgresql"):
        # Detect Supabase direct IPv6 connection that fails on Render IPv4
        if "supabase.co" in db_url and "pooler" not in db_url:
            logger.warning("⚠️ Supabase direct IPv6 URL detected. Switching to local SQLite engine to avoid timeout.")
            return create_engine("sqlite:///./chiriqui_operativo.db", connect_args={"check_same_thread": False})

        if "sslmode" not in db_url:
            db_url += "?sslmode=require"
        engine_kwargs["pool_size"] = 5
        engine_kwargs["max_overflow"] = 10
        engine_kwargs["pool_recycle"] = 300
        connect_args["connect_timeout"] = 3
        
        try:
            temp_engine = create_engine(db_url, connect_args=connect_args, **engine_kwargs)
            with temp_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ Conexión exitosa a PostgreSQL")
            return temp_engine
        except Exception as e:
            logger.warning(f"⚠️ Error conectando a PostgreSQL ({e}). Usando fallback a SQLite.")
            return create_engine("sqlite:///./chiriqui_operativo.db", connect_args={"check_same_thread": False})

engine = init_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

