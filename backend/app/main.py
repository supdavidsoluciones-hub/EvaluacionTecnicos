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


    logger.info("✅ Sistema de Control Operativo Chiriquí - ONLINE")

# Montar archivos estáticos de forma global
if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
else:
    os.makedirs("static/uploads", exist_ok=True)
    app.mount("/static", StaticFiles(directory="static"), name="static")

if os.path.isdir("web_frontend"):
    app.mount("/app", StaticFiles(directory="web_frontend", html=True), name="web_app")



from fastapi.responses import RedirectResponse

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/app/login.html")

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "chiriqui-control-operativo", "version": "1.0.0"}
