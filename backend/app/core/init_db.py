from sqlalchemy.orm import Session
from backend.app.models.models import (
    Role, User, Mobile, InspectionCategory, InspectionChecklistTemplate, VehicleInventory
)
from backend.app.core.security import get_password_hash

def init_db(db: Session):
    # 1. Crear Roles si no existen
    admin_role = db.query(Role).filter(Role.name == "Admin").first()
    if not admin_role:
        admin_role = Role(name="Admin")
        db.add(admin_role)
    
    super_role = db.query(Role).filter(Role.name == "Supervisor").first()
    if not super_role:
        super_role = Role(name="Supervisor")
        db.add(super_role)
    
    db.commit()

    # 2. Crear usuario Admin inicial
    admin_user = db.query(User).filter(User.username == "admin").first()
    if not admin_user:
        admin_user = User(
            username="admin",
            email="admin@chiriqui.com",
            password_hash=get_password_hash("admin123"),
            full_name="Administrador del Sistema",
            role_id=admin_role.id,
            is_active=True
        )
        db.add(admin_user)
        db.commit()

    # 3. Crear Móviles M200 a M206 (Chiriquí) y M207 a M209 (Santiago)
    default_mobiles = [
        ("M200", "Chiriquí"), ("M201", "Chiriquí"), ("M202", "Chiriquí"),
        ("M203", "Chiriquí"), ("M204", "Chiriquí"), ("M205", "Chiriquí"), ("M206", "Chiriquí"),
        ("M207", "Santiago"), ("M208", "Santiago"), ("M209", "Santiago")
    ]
    for code, location in default_mobiles:
        m = db.query(Mobile).filter(Mobile.code == code).first()
        if not m:
            m = Mobile(
                code=code,
                vehicle_model="Chevrolet P900",
                zone=location,
                status="activa",
                notes=f"Móvil {code} asignada a {location}"
            )
            db.add(m)
            db.commit()
            db.refresh(m)
            _seed_inventory(m.id, db)
    db.commit()

    # Migrar inventario existente a la lista oficial v2
    _migrate_inventory_to_v2(db)

    # 4. Crear Categorías y Preguntas por Defecto de Inspección
    checklist_structure = [
        {
            "category": ("SEGURIDAD", "SEG"),
            "questions": [
                "¿Utiliza conos de seguridad?",
                "¿Existe señalización adecuada?",
                "¿El técnico trabaja de forma segura?",
                "¿Utiliza correctamente los equipos de protección (EPP)?"
            ]
        },
        {
            "category": ("ACOMETIDA", "ACO"),
            "questions": [
                "¿La acometida está correctamente instalada?",
                "¿Está correctamente fijada?",
                "¿La instalación presenta buena terminación?",
                "¿Se respetan las normas de instalación?"
            ]
        },
        {
            "category": ("CONECTORES FTTH", "FTTH"),
            "questions": [
                "¿Conector correctamente elaborado?",
                "¿Terminación limpia?",
                "¿Sin daños visibles?",
                "¿Correcta instalación en ONU/NAP?"
            ]
        },
        {
            "category": ("ONU Y EQUIPOS", "ONU"),
            "questions": [
                "ONU correctamente instalada",
                "Cableado correctamente organizado",
                "Equipos correctamente ubicados",
                "Configuración correcta",
                "Aprovisionamiento correcto"
            ]
        },
        {
            "category": ("EERO / WIFI", "WIFI"),
            "questions": [
                "Configuración correcta",
                "Aprovisionamiento correcto",
                "Equipos correctamente instalados",
                "Uso de cable de red cuando corresponde",
                "Cliente orientado sobre administración de la red"
            ]
        },
        {
            "category": ("TELEVISIÓN", "TV"),
            "questions": [
                "Configuración correcta",
                "Equipos correctamente instalados",
                "Cableado correcto",
                "Cliente orientado sobre funcionamiento"
            ]
        },
        {
            "category": ("TELEFONÍA", "TEL"),
            "questions": [
                "Servicio funcionando",
                "Configuración correcta",
                "Cliente orientado"
            ]
        },
        {
            "category": ("ATENCIÓN AL CLIENTE", "CLI"),
            "questions": [
                "Técnico explicó correctamente los servicios",
                "Explicó funcionamiento de Internet",
                "Explicó funcionamiento de TV",
                "Explicó funcionamiento de telefonía",
                "Explicó funcionamiento de eero/WiFi",
                "Respondió las dudas del cliente"
            ]
        }
    ]

    sort_ord = 1
    for item in checklist_structure:
        cat_name, cat_code = item["category"]
        cat_obj = db.query(InspectionCategory).filter(InspectionCategory.code == cat_code).first()
        if not cat_obj:
            cat_obj = InspectionCategory(name=cat_name, code=cat_code, sort_order=sort_ord)
            db.add(cat_obj)
            db.commit()
        
        q_ord = 1
        for q_text in item["questions"]:
            q_obj = db.query(InspectionChecklistTemplate).filter(
                InspectionChecklistTemplate.category_id == cat_obj.id,
                InspectionChecklistTemplate.question_text == q_text
            ).first()
            if not q_obj:
                db.add(InspectionChecklistTemplate(
                    category_id=cat_obj.id,
                    question_text=q_text,
                    sort_order=q_ord,
                    is_active=True
                ))
            q_ord += 1
        sort_ord += 1
    
    db.commit()


def _seed_inventory(mobile_id: int, db: Session):
    """Agrega la lista oficial de herramientas estándar a una móvil nueva."""
    default_tools = [
        # ── Herramientas Manuales ──────────────────────────────────────────────
        ("Alicate Corte Diagonal 7\"",         "Herramienta", 2),
        ("Alicate Punta 7\"",                  "Herramienta", 2),
        ("Alicate Universal 8\"",              "Herramienta", 2),
        ("Desatornillador Phillips",           "Herramienta", 2),
        ("Desatornillador Plano",              "Herramienta", 2),
        ("Llave Corofija 3/8",                 "Herramienta", 2),
        ("Llave Corofija 7/16",                "Herramienta", 2),
        ("Martillo Herramientas P/Móviles",    "Herramienta", 1),
        ("Bolso de Herramientas",              "Herramienta", 2),
        ("Caja de Herramientas",               "Herramienta", 1),
        ("Marco de Segueta",                   "Herramienta", 1),
        ("Extensión P/Pintor",                 "Herramienta", 1),
        ("Odómetro",                           "Herramienta", 1),
        ("Ratch de 3/8",                       "Herramienta", 1),
        ("Extensión para Rach de 3/8",         "Herramienta", 1),
        ("Cubo 3/8 x 5/8",                     "Herramienta", 1),
        ("Cubo para Rach 7/16",                "Herramienta", 1),
        ("Engrapadora T-59",                   "Herramienta", 1),
        ("Cureña",                             "Herramienta", 1),
        ("Sonda Pasa-Cable en Ductos 100 Mts / 6mm (60 mts)", "Herramienta", 1),
        # ── Herramientas Eléctricas ───────────────────────────────────────────
        ("Inversor de 1500 W / 1800 W",        "Eléctrico",   1),
        ("Multímetro Digital",                 "Eléctrico",   1),
        ("Extensión Eléctrica",                "Eléctrico",   1),
        ("Taladro Inalámbrico (de cable)",     "Eléctrico",   1),
        ("Cubo P/Taladro 3/8",                 "Eléctrico",   1),
        ("Broca P/Concreto 1/4",               "Eléctrico",   1),
        ("Broca P/Concreto 3/8",               "Eléctrico",   1),
        ("Broca 3/8\" Metal",                  "Eléctrico",   1),
        ("Brocas 5/16 x 12 Metal",             "Eléctrico",   1),
        # ── Fibra Óptica ──────────────────────────────────────────────────────
        ("Cleaver F.O Sumitomo (Cortadora F.O)", "Fibra Óptica", 2),
        ("Peladora Fibra 3 Calibres",          "Fibra Óptica", 2),
        ("Peladora Cable Drop",                "Fibra Óptica", 2),
        ("Regla para Cortador",                "Fibra Óptica", 2),
        ("Limpiador de Conectores One-Click (SC-2.5MM)", "Fibra Óptica", 2),
        ("Medidor de Potencia PON FTTH",       "Fibra Óptica", 1),
        ("Localizador Óptico de Falla Visual F.O [FFL-50/1]", "Fibra Óptica", 2),
        # ── EPP (Equipo de Protección Personal) ───────────────────────────────
        ("Arnés Rota Confort Faja Lumbar 3 Puntos", "EPP", 1),
        ("Casco de Seguridad",                 "EPP", 2),
        ("Línea de Vida Sencilla 90 30/49 Gancho Grande", "EPP", 1),
        ("Línea de Posicionamiento 14MM CU 31/1", "EPP", 1),
        ("Lente Protector Fuji2 [PO-FUJI2NOOR]", "EPP", 2),
        ("Lentes de Seguridad Claro",          "EPP", 2),
        ("Chaleco Seguridad Fosforescente",    "EPP", 2),
        ("Guante Protec. Palma Látex (A3) Par 10CM", "EPP", 2),
        ("Guante Protec. Palma Látex (A3) Par 8CM",  "EPP", 2),
        ("Foco de Minero",                     "EPP", 2),
        # ── Seguridad Vial ────────────────────────────────────────────────────
        ("Conos Reflectores 28\" P/Móviles",   "Seguridad", 4),
        ("Cadena Galvanizada P/Móviles",       "Seguridad", 2),
        ("Candado Segur P/Móviles 60MM",       "Seguridad", 2),
        ("Kit de Seguridad P/Móvil [12560]",   "Seguridad", 1),
        # ── Escaleras ─────────────────────────────────────────────────────────
        ("Escalera de Extensión #28 (con Ganchos)", "Escalera", 1),
        ("Escalera Recta 12 FT (Machillo)",    "Escalera", 1),
        ("Escalera de 6 Peldaños",             "Escalera", 1),
        # ── Telecom / Equipos ─────────────────────────────────────────────────
        ("Teléfono Pared P/Móvil",             "Telecom", 1),
        ("Televisor 24\" (o menor tamaño)",    "Telecom", 1),
        ("Laptop con Puerto de Red 1 GB",      "Telecom", 1),
        # ── Bolsos / Contenedores ─────────────────────────────────────────────
        ("Bolso Porta Herramientas",           "Herramienta", 2),
    ]
    for tool_name, category, qty_required in default_tools:
        exists = db.query(VehicleInventory).filter(
            VehicleInventory.mobile_id == mobile_id,
            VehicleInventory.tool_name == tool_name
        ).first()
        if not exists:
            db.add(VehicleInventory(
                mobile_id=mobile_id,
                tool_name=tool_name,
                category=category,
                quantity_required=qty_required,
                quantity_current=qty_required,
                status="ok"
            ))
    db.commit()

def _migrate_inventory_to_v2(db: Session):
    """Limpia el inventario viejo y aplica el nuevo formato a todas las móviles si no tienen la herramienta de referencia 'Alicate Corte Diagonal 7"'."""
    from backend.app.models.models import Mobile, VehicleInventory
    mobiles = db.query(Mobile).all()
    for m in mobiles:
        # Check if it already has the new tools (using one as reference)
        has_new = db.query(VehicleInventory).filter(
            VehicleInventory.mobile_id == m.id,
            VehicleInventory.tool_name == "Alicate Corte Diagonal 7\""
        ).first()
        
        if not has_new:
            # Delete old inventory for this mobile
            db.query(VehicleInventory).filter(VehicleInventory.mobile_id == m.id).delete()
            db.commit()
            
            # Seed the new inventory
            _seed_inventory(m.id, db)
