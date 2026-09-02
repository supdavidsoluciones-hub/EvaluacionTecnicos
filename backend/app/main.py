from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os

from backend.app.core.config import settings
from backend.app.core.database import engine, SessionLocal, Base
from backend.app.core.init_db import init_db

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

# Crear Tablas e Inicializar Datos por Defecto al arrancar
Base.metadata.create_all(bind=engine)
db_session = SessionLocal()
try:
    init_db(db_session)
finally:
    db_session.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="API REST del Sistema de Control Operativo de Móviles - Chiriquí"
)

# Habilitar CORS para permitir consumo desde Web App y App de Escritorio
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crear directorios necesarios si no existen (crítico en Render)
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("web_frontend", exist_ok=True)

# Montar archivos estáticos solo si las carpetas existen y tienen contenido
app.mount("/static", StaticFiles(directory="static"), name="static")

if os.path.isdir("web_frontend") and os.listdir("web_frontend"):
    app.mount("/app", StaticFiles(directory="web_frontend", html=True), name="web_app")

# Incluir Routers en API V1
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

@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <html>
    <head><title>Control Operativo Chiriquí</title></head>
    <body style="font-family:Arial;text-align:center;padding:50px;background:#1a1a2e;color:white;">
        <h1>🚀 API - Sistema de Control Operativo de Móviles</h1>
        <h2>Chiriquí - Panamá</h2>
        <p><a href="/docs" style="color:#00d4aa;font-size:18px;">📚 Ver Documentación de la API</a></p>
        <p><a href="/app" style="color:#00d4aa;font-size:18px;">📱 Abrir Aplicación Web</a></p>
        <p style="color:#888;">Sistema funcionando correctamente ✅</p>
    </body>
    </html>
    """

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "chiriqui-control-operativo"}
