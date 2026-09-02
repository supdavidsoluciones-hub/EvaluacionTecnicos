from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from backend.app.core.config import settings
from backend.app.core.database import engine, SessionLocal, Base

# Importar Routers
from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.mobiles import router as mobiles_router
from backend.app.api.v1.technicians import router as technicians_router
from backend.app.api.v1.orders import router as orders_router
from backend.app.api.v1.inspections import router as inspections_router
from backend.app.api.v1.guarantees import router as guarantees_router
from backend.app.api.v1.action_plans import router as action_plans_router
from backend.app.api.v1.dashboard import router as dashboard_router
from backend.app.api.v1.reports import router as reports_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="API REST del Sistema de Control Operativo de Móviles - Chiriquí"
)

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir Routers
api_prefix = settings.API_V1_STR
app.include_router(auth_router, prefix=api_prefix)
app.include_router(mobiles_router, prefix=api_prefix)
app.include_router(technicians_router, prefix=api_prefix)
app.include_router(orders_router, prefix=api_prefix)
app.include_router(inspections_router, prefix=api_prefix)
app.include_router(guarantees_router, prefix=api_prefix)
app.include_router(action_plans_router, prefix=api_prefix)
app.include_router(dashboard_router, prefix=api_prefix)
app.include_router(reports_router, prefix=api_prefix)


@app.on_event("startup")
async def startup_event():
    """Inicializa la base de datos al arrancar. Nunca crashea el servidor."""
    try:
        logger.info("Iniciando conexión a base de datos...")
        Base.metadata.create_all(bind=engine)
        logger.info("Tablas creadas/verificadas correctamente.")

        from backend.app.core.init_db import init_db
        db_session = SessionLocal()
        try:
            init_db(db_session)
            logger.info("Datos iniciales cargados correctamente.")
        finally:
            db_session.close()
    except Exception as e:
        logger.error(f"Error en startup DB (la app seguirá funcionando): {e}")

    # Crear carpetas estáticas
    os.makedirs("static/uploads", exist_ok=True)
    os.makedirs("web_frontend", exist_ok=True)

    # Montar archivos estáticos solo si existen
    try:
        if not any(r.name == "static" for r in app.routes):
            app.mount("/static", StaticFiles(directory="static"), name="static")
    except Exception:
        pass

    try:
        if os.path.isdir("web_frontend") and os.listdir("web_frontend"):
            if not any(r.name == "web_app" for r in app.routes):
                app.mount("/app", StaticFiles(directory="web_frontend", html=True), name="web_app")
    except Exception:
        pass

    logger.info("✅ Sistema de Control Operativo Chiriquí - ONLINE")


@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <html>
    <head>
        <title>Control Operativo Chiriquí</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 60px;
                   background: #1a1a2e; color: white; margin: 0; }
            h1 { color: #00d4aa; font-size: 2em; }
            h2 { color: #aaa; font-size: 1.2em; }
            .btn { display: inline-block; margin: 10px; padding: 14px 28px;
                   background: #00d4aa; color: #1a1a2e; text-decoration: none;
                   border-radius: 8px; font-weight: bold; font-size: 16px; }
            .btn:hover { background: #00b894; }
            .status { margin-top: 30px; color: #55efc4; font-size: 14px; }
        </style>
    </head>
    <body>
        <h1>🚀 Control Operativo de Móviles</h1>
        <h2>Chiriquí – Panamá</h2>
        <br>
        <a href="/docs" class="btn">📚 Documentación API</a>
        <a href="/app" class="btn">📱 Aplicación Web</a>
        <p class="status">✅ Servidor funcionando correctamente</p>
    </body>
    </html>
    """

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "chiriqui-control-operativo", "version": "1.0.0"}
