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

    if db_url.startswith("sqlite"):
        return create_engine(db_url, connect_args={"check_same_thread": False}, pool_pre_ping=True)

    # Supabase requires pooler URL for IPv4 (Render is IPv4 only)
    # Convert direct connection to pooler automatically
    if "db.vpivzxkttjsgkpxyvpvp.supabase.co" in db_url:
        db_url = db_url.replace(
            "db.vpivzxkttjsgkpxyvpvp.supabase.co:5432",
            "aws-0-us-east-1.pooler.supabase.com:6543"
        )
        db_url = db_url.replace(
            "postgresql://postgres:",
            "postgresql://postgres.vpivzxkttjsgkpxyvpvp:"
        )

    if "sslmode" not in db_url:
        db_url += "?sslmode=require"

    engine = create_engine(
        db_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=300,
        connect_args={"connect_timeout": 10}
    )

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Conexion exitosa a PostgreSQL (Supabase Pooler)")
    except Exception as e:
        logger.error(f"Error conectando a PostgreSQL: {e}")
        raise RuntimeError(f"No se puede conectar a la base de datos: {e}")

    return engine

engine = init_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
