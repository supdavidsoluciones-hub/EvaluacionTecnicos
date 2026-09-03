from sqlalchemy.orm import Session
from backend.app.models.models import (
    Role, User, Mobile, InspectionCategory, InspectionChecklistTemplate
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
            db.add(Mobile(code=code, status="activa", notes=f"Móvil {code} asignada a {location}"))
    db.commit()

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
